from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import current_user
from app.extensions import db
from app.models import Examination, ExamAttempt, Question, Option, StudentAnswer, ExamActivityLog, ExamResult
from app.utils import student_required, evaluate_exam_attempt

examination_bp = Blueprint('examination', __name__)
examination_bp.before_request(student_required)


@examination_bp.route('/<int:exam_id>/instructions')
def instructions(exam_id):
    student = current_user.student_profile
    exam = Examination.query.get_or_404(exam_id)

    # Verification: Student's college, course, branch, and semester
    if (exam.college_id != student.college_id or
        exam.course_id != student.course_id or
        exam.branch_id != student.branch_id or
        exam.semester != student.semester):
        flash('You are not eligible to take this examination.', 'danger')
        abort(403)

    if exam.status not in ['active', 'scheduled']:
        flash('This examination is currently not active.', 'warning')
        return redirect(url_for('student.dashboard'))

    # Check attempt count
    submitted_attempts = ExamAttempt.query.filter_by(
        examination_id=exam.id,
        student_id=student.id,
        status='submitted'
    ).count()

    if submitted_attempts >= exam.max_attempts:
        flash('You have reached the maximum allowed attempts for this examination.', 'info')
        return redirect(url_for('student.dashboard'))

    # Check for active in-progress attempt
    in_progress = ExamAttempt.query.filter_by(
        examination_id=exam.id,
        student_id=student.id,
        status='in_progress'
    ).first()

    return render_template(
        'student/instructions.html',
        exam=exam,
        student=student,
        college=student.college,
        in_progress=in_progress,
        submitted_attempts=submitted_attempts
    )


@examination_bp.route('/<int:exam_id>/start', methods=['POST'])
def start_exam(exam_id):
    student = current_user.student_profile
    exam = Examination.query.get_or_404(exam_id)

    # Validate eligibility
    if (exam.college_id != student.college_id or
        exam.course_id != student.course_id or
        exam.branch_id != student.branch_id or
        exam.semester != student.semester):
        abort(403)

    # Check for existing in-progress attempt to resume
    attempt = ExamAttempt.query.filter_by(
        examination_id=exam.id,
        student_id=student.id,
        status='in_progress'
    ).first()

    if not attempt:
        submitted_attempts = ExamAttempt.query.filter_by(
            examination_id=exam.id,
            student_id=student.id,
            status='submitted'
        ).count()

        if submitted_attempts >= exam.max_attempts:
            flash('Maximum examination attempts exceeded.', 'danger')
            return redirect(url_for('student.dashboard'))

        attempt = ExamAttempt(
            examination_id=exam.id,
            student_id=student.id,
            college_id=student.college_id,
            attempt_number=submitted_attempts + 1,
            start_time=datetime.utcnow(),
            status='in_progress',
            ip_address=request.remote_addr
        )
        db.session.add(attempt)
        db.session.flush()

        # Log start event
        log = ExamActivityLog(
            attempt_id=attempt.id,
            event_type='start',
            event_data=f"Examination initiated from IP: {request.remote_addr}"
        )
        db.session.add(log)
        db.session.commit()

    return redirect(url_for('examination.take_exam', attempt_id=attempt.id))


@examination_bp.route('/<int:attempt_id>/take')
def take_exam(attempt_id):
    student = current_user.student_profile
    attempt = ExamAttempt.query.get_or_404(attempt_id)

    if attempt.student_id != student.id:
        abort(403)

    if attempt.status != 'in_progress':
        # If already evaluated/submitted, redirect directly to result
        result = ExamResult.query.filter_by(attempt_id=attempt.id).first()
        if result:
            return redirect(url_for('results.view_result', result_id=result.id))
        return redirect(url_for('student.dashboard'))

    exam = attempt.examination

    # Backend-enforced timer validation
    elapsed_seconds = (datetime.utcnow() - attempt.start_time).total_seconds()
    max_duration_seconds = exam.duration_minutes * 60
    remaining_seconds = max_duration_seconds - elapsed_seconds

    if remaining_seconds <= 0:
        # Time has expired on backend - trigger immediate evaluation
        flash('Examination time limit expired. Your responses have been automatically submitted.', 'info')
        result = evaluate_exam_attempt(attempt)
        return redirect(url_for('results.view_result', result_id=result.id))

    # Prepare existing student answers map
    saved_answers = {a.question_id: a for a in attempt.answers}

    # Format questions cleanly (ensuring is_correct is NOT exposed in template variables)
    questions_data = []
    for q in exam.questions:
        ans = saved_answers.get(q.id)
        questions_data.append({
            'id': q.id,
            'number': q.question_number,
            'text': q.question_text,
            'marks': q.marks,
            'negative_marks': q.negative_marks if q.negative_marks > 0 else (exam.negative_mark_value if exam.negative_marking else 0.0),
            'options': [{'id': opt.id, 'number': opt.option_number, 'text': opt.option_text} for opt in q.options],
            'selected_option_id': ans.selected_option_id if ans else None,
            'is_marked_for_review': ans.is_marked_for_review if ans else False
        })

    return render_template(
        'student/exam.html',
        attempt=attempt,
        exam=exam,
        student=student,
        college=student.college,
        questions=questions_data,
        remaining_seconds=int(remaining_seconds)
    )


@examination_bp.route('/<int:attempt_id>/save-answer', methods=['POST'])
def save_answer(attempt_id):
    student = current_user.student_profile
    attempt = ExamAttempt.query.get_or_404(attempt_id)

    if attempt.student_id != student.id or attempt.status != 'in_progress':
        return jsonify({'status': 'error', 'message': 'Invalid session or unauthorized attempt'}), 403

    # Check timeout
    elapsed = (datetime.utcnow() - attempt.start_time).total_seconds()
    if elapsed > (attempt.examination.duration_minutes * 60 + 30):  # 30 seconds network grace
        result = evaluate_exam_attempt(attempt)
        return jsonify({'status': 'expired', 'redirect_url': url_for('results.view_result', result_id=result.id)})

    data = request.get_json() or {}
    question_id = data.get('question_id')
    selected_option_id = data.get('selected_option_id')
    is_marked_for_review = bool(data.get('is_marked_for_review', False))

    if not question_id:
        return jsonify({'status': 'error', 'message': 'Question ID missing'}), 400

    # Ensure question belongs to this exam
    question = Question.query.filter_by(id=question_id, examination_id=attempt.examination_id).first()
    if not question:
        return jsonify({'status': 'error', 'message': 'Question not associated with examination'}), 400

    # Save or update answer
    answer = StudentAnswer.query.filter_by(attempt_id=attempt.id, question_id=question_id).first()
    if not answer:
        answer = StudentAnswer(
            attempt_id=attempt.id,
            question_id=question_id,
            selected_option_id=selected_option_id,
            is_marked_for_review=is_marked_for_review,
            answered_at=datetime.utcnow()
        )
        db.session.add(answer)
    else:
        answer.selected_option_id = selected_option_id
        answer.is_marked_for_review = is_marked_for_review
        answer.answered_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'status': 'success', 'question_id': question_id})


@examination_bp.route('/<int:attempt_id>/clear-answer', methods=['POST'])
def clear_answer(attempt_id):
    student = current_user.student_profile
    attempt = ExamAttempt.query.get_or_404(attempt_id)

    if attempt.student_id != student.id or attempt.status != 'in_progress':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    data = request.get_json() or {}
    question_id = data.get('question_id')

    answer = StudentAnswer.query.filter_by(attempt_id=attempt.id, question_id=question_id).first()
    if answer:
        answer.selected_option_id = None
        db.session.commit()

    return jsonify({'status': 'success'})


@examination_bp.route('/<int:attempt_id>/log-activity', methods=['POST'])
def log_activity(attempt_id):
    student = current_user.student_profile
    attempt = ExamAttempt.query.get_or_404(attempt_id)

    if attempt.student_id != student.id:
        return jsonify({'status': 'error'}), 403

    data = request.get_json() or {}
    event_type = data.get('event_type', 'unknown')
    event_data = data.get('event_data', '')

    if event_type == 'tab_switch':
        attempt.tab_switch_count += 1
    elif event_type == 'fullscreen_exit':
        attempt.fullscreen_exit_count += 1

    log = ExamActivityLog(
        attempt_id=attempt.id,
        event_type=event_type,
        event_data=event_data
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'status': 'logged',
        'tab_switch_count': attempt.tab_switch_count,
        'fullscreen_exit_count': attempt.fullscreen_exit_count
    })


@examination_bp.route('/<int:attempt_id>/submit', methods=['POST'])
def submit_exam(attempt_id):
    student = current_user.student_profile
    attempt = ExamAttempt.query.get_or_404(attempt_id)

    if attempt.student_id != student.id:
        abort(403)

    if attempt.status != 'in_progress':
        result = ExamResult.query.filter_by(attempt_id=attempt.id).first()
        if result:
            return redirect(url_for('results.view_result', result_id=result.id))
        return redirect(url_for('student.dashboard'))

    # Evaluate attempt
    result = evaluate_exam_attempt(attempt)

    # Log submission event
    log = ExamActivityLog(
        attempt_id=attempt.id,
        event_type='submit',
        event_data=f"Manual student submission recorded. Final Score: {result.obtained_marks}/{result.total_marks}"
    )
    db.session.add(log)
    db.session.commit()

    flash('Your examination has been submitted and automatically evaluated.', 'success')
    return redirect(url_for('results.view_result', result_id=result.id))

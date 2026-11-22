import io
import csv
from datetime import datetime, date, time, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from flask_login import current_user
from app.extensions import db
from app.models import (
    Examination, Question, Option, Course, Branch, Subject,
    ExamAttempt, ExamResult, FacultySubjectAssignment, StudentAnswer, StudentProfile
)
from app.utils import (
    faculty_required, compute_competition_ranking,
    generate_attendance_pdf, generate_marks_pdf, generate_complete_exam_report_pdf
)

faculty_bp = Blueprint('faculty', __name__)
faculty_bp.before_request(faculty_required)


def verify_faculty_exam_access(exam, faculty):
    """Verify that the faculty member is authorized to view or manage this examination."""
    if exam.college_id != current_user.college_id:
        abort(403)
    if exam.faculty_id != faculty.id:
        has_assignment = FacultySubjectAssignment.query.filter_by(
            faculty_id=faculty.id, subject_id=exam.subject_id
        ).first()
        if not has_assignment:
            abort(403)
    return True


def get_exam_attendance_and_metrics(exam):
    """
    Computes real attendance ledger and statistics for an examination based on actual attempts.
    """
    now = datetime.now()
    exam_end_datetime = datetime.combine(exam.exam_date, exam.end_time)
    is_window_closed = (now > exam_end_datetime) or (exam.status == 'completed')

    # Eligible registered students
    eligible_students = StudentProfile.query.filter_by(
        college_id=exam.college_id,
        course_id=exam.course_id,
        branch_id=exam.branch_id,
        semester=exam.semester
    ).order_by(StudentProfile.registration_number).all()

    attempts_by_student = {a.student_id: a for a in exam.attempts}
    results_by_student = {r.student_id: r for r in exam.results}

    attendance_records = []
    present_count = 0
    in_progress_count = 0
    absent_count = 0
    pending_count = 0

    for s_no, st in enumerate(eligible_students, start=1):
        att = attempts_by_student.get(st.id)
        res = results_by_student.get(st.id)

        if att:
            if att.status == 'submitted' or res is not None:
                status = 'Present'
                badge_class = 'bg-success'
                present_count += 1
            elif att.status == 'in_progress':
                if is_window_closed:
                    status = 'Present'
                    badge_class = 'bg-success'
                    present_count += 1
                else:
                    status = 'In Progress'
                    badge_class = 'bg-warning text-dark'
                    in_progress_count += 1
            else:
                status = 'Present'
                badge_class = 'bg-success'
                present_count += 1
        else:
            if is_window_closed:
                status = 'Absent'
                badge_class = 'bg-danger'
                absent_count += 1
            else:
                status = 'Pending'
                badge_class = 'bg-secondary'
                pending_count += 1

        attendance_records.append({
            's_no': s_no,
            'student': st,
            'attempt': att,
            'result': res,
            'status': status,
            'badge_class': badge_class
        })

    total_registered = len(eligible_students)
    attendance_percentage = round((present_count / total_registered * 100), 2) if total_registered > 0 else 0.0

    return {
        'records': attendance_records,
        'total_registered': total_registered,
        'present_count': present_count,
        'in_progress_count': in_progress_count,
        'absent_count': absent_count,
        'pending_count': pending_count,
        'attendance_percentage': attendance_percentage,
        'is_window_closed': is_window_closed
    }



@faculty_bp.route('/dashboard')
def dashboard():
    faculty = current_user.faculty_profile
    if not faculty:
        abort(403)

    college_id = current_user.college_id
    courses = Course.query.filter_by(college_id=college_id).all()
    subjects = Subject.query.filter_by(college_id=college_id).all()

    selected_course_id = request.args.get('course_id', type=int)
    selected_subject_id = request.args.get('subject_id', type=int)

    query = Examination.query.filter_by(faculty_id=faculty.id)
    if selected_course_id:
        query = query.filter_by(course_id=selected_course_id)
    if selected_subject_id:
        query = query.filter_by(subject_id=selected_subject_id)

    exams = query.order_by(Examination.created_at.desc()).all()
    total_exams = len(exams)
    active_exams = sum(1 for e in exams if e.status == 'active')
    scheduled_exams = sum(1 for e in exams if e.status == 'scheduled')
    completed_exams = sum(1 for e in exams if e.status == 'completed')

    # Total attempts evaluated across faculty's exams
    exam_ids = [e.id for e in exams]
    total_evaluated = ExamResult.query.filter(ExamResult.examination_id.in_(exam_ids)).count() if exam_ids else 0

    # If subject selected, gather all questions with keys and solutions
    subject_questions = []
    selected_subject = None
    if selected_subject_id:
        selected_subject = Subject.query.get(selected_subject_id)
        for e in exams:
            for q in e.questions:
                subject_questions.append({
                    'exam': e,
                    'question': q,
                    'correct_option': next((opt for opt in q.options if opt.is_correct), None)
                })

    return render_template(
        'faculty/dashboard.html',
        faculty=faculty,
        courses=courses,
        subjects=subjects,
        selected_course_id=selected_course_id,
        selected_subject_id=selected_subject_id,
        selected_subject=selected_subject,
        subject_questions=subject_questions,
        exams=exams,
        total_exams=total_exams,
        active_exams=active_exams,
        scheduled_exams=scheduled_exams,
        completed_exams=completed_exams,
        total_evaluated=total_evaluated
    )


@faculty_bp.route('/examinations/create', methods=['GET', 'POST'])
def create_exam():
    if getattr(current_user, 'registration_status', 'active') not in ('active', 'approved') or not current_user.is_active:
        flash('Your faculty account has not been approved yet. Examination authoring is restricted.', 'warning')
        return redirect(url_for('faculty.dashboard'))

    faculty = current_user.faculty_profile
    college_id = current_user.college_id

    courses = Course.query.filter_by(college_id=college_id).all()
    branches = Branch.query.filter_by(college_id=college_id).all()
    subjects = Subject.query.filter_by(college_id=college_id).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        course_id = request.form.get('course_id')
        branch_id = request.form.get('branch_id')
        semester = int(request.form.get('semester', 1))
        subject_id = request.form.get('subject_id')
        exam_date_str = request.form.get('exam_date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        duration_minutes = int(request.form.get('duration_minutes', 60))
        passing_percentage = float(request.form.get('passing_percentage', 40.0))
        max_attempts = int(request.form.get('max_attempts', 1))
        negative_marking = 'negative_marking' in request.form
        negative_mark_value = float(request.form.get('negative_mark_value', 0.25)) if negative_marking else 0.0
        instructions = request.form.get('instructions', '').strip()

        if not all([title, course_id, branch_id, subject_id, exam_date_str, start_time_str, end_time_str]):
            flash('All primary examination scheduling fields are required.', 'warning')
            return render_template('faculty/create_exam.html', courses=courses, branches=branches, subjects=subjects)

        try:
            exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format submitted.', 'danger')
            return render_template('faculty/create_exam.html', courses=courses, branches=branches, subjects=subjects)

        exam = Examination(
            college_id=college_id,
            faculty_id=faculty.id,
            course_id=course_id,
            branch_id=branch_id,
            semester=semester,
            subject_id=subject_id,
            title=title,
            instructions=instructions,
            exam_date=exam_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            passing_percentage=passing_percentage,
            max_attempts=max_attempts,
            negative_marking=negative_marking,
            negative_mark_value=negative_mark_value,
            status='draft'
        )
        db.session.add(exam)
        db.session.commit()

        flash(f'Examination "{title}" created as Draft. Now configure questions.', 'success')
        return redirect(url_for('faculty.manage_questions', exam_id=exam.id))

    return render_template('faculty/create_exam.html', courses=courses, branches=branches, subjects=subjects)


@faculty_bp.route('/examinations/<int:exam_id>/questions', methods=['GET', 'POST'])
def manage_questions(exam_id):
    faculty = current_user.faculty_profile
    exam = Examination.query.filter_by(id=exam_id, faculty_id=faculty.id).first_or_404()

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        marks = float(request.form.get('marks', 1.0))
        negative_marks = float(request.form.get('negative_marks', 0.0))
        explanation = request.form.get('explanation', '').strip()

        # 4 Options
        opt1_text = request.form.get('option_1', '').strip()
        opt2_text = request.form.get('option_2', '').strip()
        opt3_text = request.form.get('option_3', '').strip()
        opt4_text = request.form.get('option_4', '').strip()
        correct_option = int(request.form.get('correct_option', 1))

        if not question_text or not all([opt1_text, opt2_text, opt3_text, opt4_text]):
            flash('Question text and all 4 multiple choice options are required.', 'warning')
        else:
            q_num = len(exam.questions) + 1
            question = Question(
                examination_id=exam.id,
                question_number=q_num,
                question_text=question_text,
                marks=marks,
                negative_marks=negative_marks,
                explanation=explanation
            )
            db.session.add(question)
            db.session.flush()

            options = [
                Option(question_id=question.id, option_number=1, option_text=opt1_text, is_correct=(correct_option == 1)),
                Option(question_id=question.id, option_number=2, option_text=opt2_text, is_correct=(correct_option == 2)),
                Option(question_id=question.id, option_number=3, option_text=opt3_text, is_correct=(correct_option == 3)),
                Option(question_id=question.id, option_number=4, option_text=opt4_text, is_correct=(correct_option == 4)),
            ]
            db.session.add_all(options)
            exam.calculate_total_marks()
            db.session.commit()
            flash(f'Question {q_num} added successfully.', 'success')
            return redirect(url_for('faculty.manage_questions', exam_id=exam.id))

    return render_template('faculty/manage_questions.html', exam=exam)


@faculty_bp.route('/examinations/<int:exam_id>/questions/<int:question_id>/delete', methods=['POST'])
def delete_question(exam_id, question_id):
    faculty = current_user.faculty_profile
    exam = Examination.query.filter_by(id=exam_id, faculty_id=faculty.id).first_or_404()
    question = Question.query.filter_by(id=question_id, examination_id=exam.id).first_or_404()

    db.session.delete(question)
    db.session.flush()

    # Re-number remaining questions
    for idx, q in enumerate(exam.questions, start=1):
        q.question_number = idx
    exam.calculate_total_marks()
    db.session.commit()

    flash('Question removed and sequence updated.', 'info')
    return redirect(url_for('faculty.manage_questions', exam_id=exam.id))


@faculty_bp.route('/examinations/<int:exam_id>/publish', methods=['POST'])
def publish_exam(exam_id):
    faculty = current_user.faculty_profile
    exam = Examination.query.filter_by(id=exam_id, faculty_id=faculty.id).first_or_404()

    if len(exam.questions) == 0:
        flash('Cannot publish an examination without at least one question.', 'danger')
        return redirect(url_for('faculty.manage_questions', exam_id=exam.id))

    exam.calculate_total_marks()
    exam.status = 'active'
    db.session.commit()
    flash(f'Examination "{exam.title}" has been published and activated for eligible students.', 'success')
    return redirect(url_for('faculty.dashboard'))


@faculty_bp.route('/examination-reports')
def reports_index():
    """
    Displays all examinations created by or assigned to this faculty member,
    along with real attendance and completion statistics.
    """
    faculty = current_user.faculty_profile
    if not faculty:
        abort(403)

    college_id = current_user.college_id

    # Retrieve exams created by this faculty or where faculty is assigned to the subject
    assigned_subject_ids = [a.subject_id for a in faculty.assignments]
    exams = Examination.query.filter(
        Examination.college_id == college_id,
        (Examination.faculty_id == faculty.id) | (Examination.subject_id.in_(assigned_subject_ids) if assigned_subject_ids else False)
    ).order_by(Examination.exam_date.desc(), Examination.created_at.desc()).all()

    exam_cards = []
    for ex in exams:
        metrics = get_exam_attendance_and_metrics(ex)
        exam_cards.append({
            'exam': ex,
            'total_registered': metrics['total_registered'],
            'present_count': metrics['present_count'],
            'absent_count': metrics['absent_count'],
            'in_progress_count': metrics['in_progress_count'],
            'attendance_percentage': metrics['attendance_percentage'],
            'is_window_closed': metrics['is_window_closed']
        })

    return render_template('faculty/reports_index.html', exam_cards=exam_cards, faculty=faculty)


@faculty_bp.route('/examination-reports/<int:exam_id>')
def examination_report_detail(exam_id):
    """
    Comprehensive examination report view: attendance ledger, competition ranked marks,
    performance statistics, and Chart.js analytics.
    """
    faculty = current_user.faculty_profile
    exam = Examination.query.get_or_404(exam_id)
    verify_faculty_exam_access(exam, faculty)

    attendance_data = get_exam_attendance_and_metrics(exam)
    results = ExamResult.query.filter_by(examination_id=exam.id).all()
    ranked_results = compute_competition_ranking(results)

    total_evaluated = len(ranked_results)
    if total_evaluated > 0:
        highest_marks = max(r.obtained_marks for r in ranked_results)
        lowest_marks = min(r.obtained_marks for r in ranked_results)
        average_marks = round(sum(r.obtained_marks for r in ranked_results) / total_evaluated, 2)
        pass_count = sum(1 for r in ranked_results if r.is_passed)
        fail_count = total_evaluated - pass_count
        pass_percentage = round((pass_count / total_evaluated * 100), 2)
        fail_percentage = round((fail_count / total_evaluated * 100), 2)
    else:
        highest_marks = 0.0
        lowest_marks = 0.0
        average_marks = 0.0
        pass_count = 0
        fail_count = 0
        pass_percentage = 0.0
        fail_percentage = 0.0

    # Marks distribution buckets for Chart.js
    max_m = max(1.0, exam.total_marks)
    step = max_m / 5.0
    bucket_labels = [
        f"0 - {round(step, 1)}",
        f"{round(step + 0.1, 1)} - {round(step * 2, 1)}",
        f"{round(step * 2 + 0.1, 1)} - {round(step * 3, 1)}",
        f"{round(step * 3 + 0.1, 1)} - {round(step * 4, 1)}",
        f"{round(step * 4 + 0.1, 1)} - {round(max_m, 1)}"
    ]
    bucket_counts = [0, 0, 0, 0, 0]
    for r in ranked_results:
        m = r.obtained_marks
        if m <= step:
            bucket_counts[0] += 1
        elif m <= step * 2:
            bucket_counts[1] += 1
        elif m <= step * 3:
            bucket_counts[2] += 1
        elif m <= step * 4:
            bucket_counts[3] += 1
        else:
            bucket_counts[4] += 1

    summary_stats = {
        'total_registered': attendance_data['total_registered'],
        'present_count': attendance_data['present_count'],
        'absent_count': attendance_data['absent_count'],
        'in_progress_count': attendance_data['in_progress_count'],
        'pending_count': attendance_data['pending_count'],
        'attendance_percentage': attendance_data['attendance_percentage'],
        'total_evaluated': total_evaluated,
        'highest_marks': highest_marks,
        'lowest_marks': lowest_marks,
        'average_marks': average_marks,
        'pass_count': pass_count,
        'fail_count': fail_count,
        'pass_percentage': pass_percentage,
        'fail_percentage': fail_percentage
    }

    # Extract unique branches for filter dropdown
    branches = sorted(list(set(item['student'].branch.code for item in attendance_data['records'])))

    return render_template(
        'faculty/examination_report_detail.html',
        exam=exam,
        faculty=faculty,
        attendance_records=attendance_data['records'],
        ranked_results=ranked_results,
        summary_stats=summary_stats,
        branches=branches,
        bucket_labels=bucket_labels,
        bucket_counts=bucket_counts
    )


@faculty_bp.route('/examination-reports/<int:exam_id>/student/<int:student_id>')
def student_performance_detail(exam_id, student_id):
    """
    Granular examination review for a specific candidate with question-by-question responses,
    answer keys, and detailed solutions.
    """
    faculty = current_user.faculty_profile
    exam = Examination.query.get_or_404(exam_id)
    verify_faculty_exam_access(exam, faculty)

    student = StudentProfile.query.filter_by(id=student_id, college_id=exam.college_id).first_or_404()
    attempt = ExamAttempt.query.filter_by(examination_id=exam.id, student_id=student.id).order_by(ExamAttempt.id.desc()).first()
    result = ExamResult.query.filter_by(examination_id=exam.id, student_id=student.id).first()

    # Calculate student rank among evaluated candidates
    all_results = ExamResult.query.filter_by(examination_id=exam.id).all()
    ranked = compute_competition_ranking(all_results)
    student_rank = next((r.competition_rank for r in ranked if r.student_id == student.id), None)

    # Detailed question breakdown
    question_breakdown = []
    saved_answers = {a.question_id: a for a in attempt.answers} if attempt else {}

    for q in exam.questions:
        ans = saved_answers.get(q.id)
        selected_opt = db.session.get(Option, ans.selected_option_id) if ans and ans.selected_option_id else None
        correct_opt = next((opt for opt in q.options if opt.is_correct), None)

        is_correct = bool(selected_opt and correct_opt and selected_opt.id == correct_opt.id)
        is_unanswered = (selected_opt is None)

        question_breakdown.append({
            'question': q,
            'selected_option': selected_opt,
            'correct_option': correct_opt,
            'is_correct': is_correct,
            'is_unanswered': is_unanswered
        })

    return render_template(
        'faculty/student_performance_detail.html',
        exam=exam,
        faculty=faculty,
        student=student,
        attempt=attempt,
        result=result,
        student_rank=student_rank,
        question_breakdown=question_breakdown
    )


@faculty_bp.route('/examination-reports/<int:exam_id>/download-attendance')
def download_attendance(exam_id):
    """Generates and downloads the official Attendance Ledger PDF."""
    faculty = current_user.faculty_profile
    exam = Examination.query.get_or_404(exam_id)
    verify_faculty_exam_access(exam, faculty)

    attendance_data = get_exam_attendance_and_metrics(exam)
    pdf_buffer = generate_attendance_pdf(exam, attendance_data['records'], attendance_data)

    safe_title = "".join(c for c in exam.title if c.isalnum() or c in (' ', '_', '-')).rstrip()
    filename = f"Attendance_{safe_title}_{exam.exam_date.strftime('%Y%m%d')}.pdf"
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)


@faculty_bp.route('/examination-reports/<int:exam_id>/download-marks')
def download_marks(exam_id):
    """Generates and downloads the official Ranked Marks & Merit Sheet PDF."""
    faculty = current_user.faculty_profile
    exam = Examination.query.get_or_404(exam_id)
    verify_faculty_exam_access(exam, faculty)

    results = ExamResult.query.filter_by(examination_id=exam.id).all()
    ranked_results = compute_competition_ranking(results)
    total_evaluated = len(ranked_results)

    summary_stats = {
        'total_evaluated': total_evaluated,
        'highest_marks': max((r.obtained_marks for r in ranked_results), default=0.0),
        'lowest_marks': min((r.obtained_marks for r in ranked_results), default=0.0),
        'average_marks': round(sum(r.obtained_marks for r in ranked_results) / total_evaluated, 2) if total_evaluated > 0 else 0.0,
        'pass_percentage': round(sum(1 for r in ranked_results if r.is_passed) / total_evaluated * 100, 2) if total_evaluated > 0 else 0.0
    }

    pdf_buffer = generate_marks_pdf(exam, ranked_results, summary_stats)
    safe_title = "".join(c for c in exam.title if c.isalnum() or c in (' ', '_', '-')).rstrip()
    filename = f"Marks_{safe_title}_{exam.exam_date.strftime('%Y%m%d')}.pdf"
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)


@faculty_bp.route('/examination-reports/<int:exam_id>/download-complete-report')
def download_complete_report(exam_id):
    """Generates and downloads the Complete Comprehensive Examination Report PDF."""
    faculty = current_user.faculty_profile
    exam = Examination.query.get_or_404(exam_id)
    verify_faculty_exam_access(exam, faculty)

    attendance_data = get_exam_attendance_and_metrics(exam)
    results = ExamResult.query.filter_by(examination_id=exam.id).all()
    ranked_results = compute_competition_ranking(results)
    total_evaluated = len(ranked_results)

    summary_stats = {
        'total_registered': attendance_data['total_registered'],
        'present_count': attendance_data['present_count'],
        'absent_count': attendance_data['absent_count'],
        'in_progress_count': attendance_data['in_progress_count'],
        'attendance_percentage': attendance_data['attendance_percentage'],
        'total_evaluated': total_evaluated,
        'highest_marks': max((r.obtained_marks for r in ranked_results), default=0.0),
        'lowest_marks': min((r.obtained_marks for r in ranked_results), default=0.0),
        'average_marks': round(sum(r.obtained_marks for r in ranked_results) / total_evaluated, 2) if total_evaluated > 0 else 0.0,
        'pass_percentage': round(sum(1 for r in ranked_results if r.is_passed) / total_evaluated * 100, 2) if total_evaluated > 0 else 0.0
    }

    pdf_buffer = generate_complete_exam_report_pdf(exam, ranked_results, attendance_data['records'], summary_stats)
    safe_title = "".join(c for c in exam.title if c.isalnum() or c in (' ', '_', '-')).rstrip()
    filename = f"Complete_Report_{safe_title}_{exam.exam_date.strftime('%Y%m%d')}.pdf"
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)


@faculty_bp.route('/examination-reports/<int:exam_id>/export-csv')
def export_csv(exam_id):
    """Exports examination marks and attendance ledger to a structured CSV spreadsheet."""
    faculty = current_user.faculty_profile
    exam = Examination.query.get_or_404(exam_id)
    verify_faculty_exam_access(exam, faculty)

    attendance_data = get_exam_attendance_and_metrics(exam)
    results = ExamResult.query.filter_by(examination_id=exam.id).all()
    ranked_results = compute_competition_ranking(results)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Rank', 'Roll Number', 'Student Name', 'Course', 'Branch', 'Semester',
        'Marks Obtained', 'Total Marks', 'Percentage', 'Correct Answers',
        'Wrong Answers', 'Unanswered Questions', 'Result Status', 'Attendance Status'
    ])

    evaluated_student_ids = set()
    for res in ranked_results:
        st = res.student
        evaluated_student_ids.add(st.id)
        writer.writerow([
            res.competition_rank,
            st.registration_number,
            st.full_name,
            st.course.code,
            st.branch.code,
            st.semester,
            res.obtained_marks,
            res.total_marks,
            f"{res.percentage}%",
            res.correct_answers,
            res.wrong_answers,
            res.unanswered_questions,
            'PASS' if res.is_passed else 'FAIL',
            'Present'
        ])

    # Record unattempted / absent students
    for item in attendance_data['records']:
        st = item['student']
        if st.id not in evaluated_student_ids:
            writer.writerow([
                '-',
                st.registration_number,
                st.full_name,
                st.course.code,
                st.branch.code,
                st.semester,
                0.0,
                exam.total_marks,
                '0.0%',
                0,
                0,
                len(exam.questions),
                'ABSENT' if item['status'] == 'Absent' else item['status'].upper(),
                item['status']
            ])

    output.seek(0)
    safe_title = "".join(c for c in exam.title if c.isalnum() or c in (' ', '_', '-')).rstrip()
    filename = f"Results_{safe_title}_{exam.exam_date.strftime('%Y%m%d')}.csv"
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@faculty_bp.route('/examinations/<int:exam_id>/reports')
def exam_reports(exam_id):
    """Legacy redirect to the comprehensive report page."""
    return redirect(url_for('faculty.examination_report_detail', exam_id=exam_id))


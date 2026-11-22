from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, abort, request, flash, redirect, url_for
from flask_login import current_user
from app.models import Examination, ExamAttempt, ExamResult, Subject
from app.utils import student_required

student_bp = Blueprint('student', __name__)
student_bp.before_request(student_required)


@student_bp.route('/dashboard')
def dashboard():
    student = current_user.student_profile
    if not student:
        abort(403)

    college = student.college
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # 1. Retrieve all curriculum subjects for this student's course, branch, and semester
    enrolled_subjects = Subject.query.filter_by(
        college_id=student.college_id,
        course_id=student.course_id,
        branch_id=student.branch_id,
        semester=student.semester
    ).order_by(Subject.code).all()

    # 2. Check if a specific subject was selected by the student
    selected_subject_id = request.args.get('subject_id', type=int)

    # 3. Base examination query matching student's eligibility
    exam_query = Examination.query.filter(
        Examination.college_id == student.college_id,
        Examination.course_id == student.course_id,
        Examination.branch_id == student.branch_id,
        Examination.semester == student.semester,
        Examination.status.in_(['active', 'scheduled'])
    )

    if selected_subject_id:
        exam_query = exam_query.filter(Examination.subject_id == selected_subject_id)

    eligible_exams = exam_query.order_by(Examination.exam_date, Examination.start_time).all()

    # 4. Check attempt status
    attempts = ExamAttempt.query.filter_by(student_id=student.id).all()
    submitted_exam_ids = [a.examination_id for a in attempts if a.status == 'submitted']

    available_exams = []
    for exam in eligible_exams:
        if submitted_exam_ids.count(exam.id) < exam.max_attempts:
            available_exams.append(exam)

    # 5. Group into Today vs Tomorrow vs Upcoming
    exams_today = [e for e in available_exams if e.exam_date == today]
    exams_tomorrow = [e for e in available_exams if e.exam_date == tomorrow]
    exams_other = [e for e in available_exams if e.exam_date > tomorrow]

    # 6. Completed results
    results = ExamResult.query.filter_by(student_id=student.id).order_by(ExamResult.evaluated_at.desc()).all()
    total_completed = len(results)
    avg_score = round(sum(r.percentage for r in results) / total_completed, 2) if total_completed > 0 else 0.0

    return render_template(
        'student/dashboard.html',
        student=student,
        college=college,
        enrolled_subjects=enrolled_subjects,
        selected_subject_id=selected_subject_id,
        exams_today=exams_today,
        exams_tomorrow=exams_tomorrow,
        exams_other=exams_other,
        available_count=len(available_exams),
        completed_results=results,
        total_completed=total_completed,
        avg_score=avg_score,
        today=today,
        tomorrow=tomorrow
    )


@student_bp.route('/profile')
def profile():
    student = current_user.student_profile
    college = student.college
    return render_template('student/profile.html', student=student, college=college)


@student_bp.route('/subjects')
def subjects():
    student = current_user.student_profile
    college = student.college

    enrolled_subjects = Subject.query.filter_by(
        college_id=student.college_id,
        course_id=student.course_id,
        branch_id=student.branch_id,
        semester=student.semester
    ).order_by(Subject.code).all()

    return render_template(
        'student/subjects.html',
        student=student,
        college=college,
        subjects=enrolled_subjects
    )


@student_bp.route('/history')
def history():
    student = current_user.student_profile
    college = student.college
    results = ExamResult.query.filter_by(student_id=student.id).order_by(ExamResult.evaluated_at.desc()).all()
    return render_template('student/results.html', student=student, college=college, results=results)


@student_bp.route('/instructions')
def instructions():
    flash('Please select an active examination from your dashboard to view its instructions.', 'info')
    return redirect(url_for('student.dashboard'))

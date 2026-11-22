from flask import Blueprint, render_template, abort, send_file, redirect, url_for
from flask_login import current_user
from app.extensions import db
from app.models import ExamResult, StudentAnswer, Option, FacultySubjectAssignment
from app.utils import generate_result_pdf

results_bp = Blueprint('results', __name__)

@results_bp.before_request
def ensure_authenticated():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))



@results_bp.route('/<int:result_id>')
def view_result(result_id):
    result = ExamResult.query.get_or_404(result_id)

    # Authorization Check
    authorized = False
    if current_user.is_super_admin:
        authorized = True
    elif current_user.is_college_admin and current_user.college_id == result.college_id:
        authorized = True
    elif current_user.is_faculty and current_user.faculty_profile and result.college_id == current_user.college_id:
        if result.examination.faculty_id == current_user.faculty_profile.id:
            authorized = True
        elif FacultySubjectAssignment.query.filter_by(
            faculty_id=current_user.faculty_profile.id, subject_id=result.examination.subject_id
        ).first():
            authorized = True
    elif current_user.is_student and current_user.student_profile and result.student_id == current_user.student_profile.id:
        authorized = True

    if not authorized:
        abort(403)

    student = result.student
    college = result.college
    exam = result.examination
    attempt = result.attempt

    # Fetch detailed questions & responses for question review
    saved_answers = {a.question_id: a for a in attempt.answers}
    review_data = []

    for q in exam.questions:
        ans = saved_answers.get(q.id)
        selected_option = db.session.get(Option, ans.selected_option_id) if ans and ans.selected_option_id else None
        correct_option = next((opt for opt in q.options if opt.is_correct), None)

        is_user_correct = False
        if selected_option and correct_option and selected_option.id == correct_option.id:
            is_user_correct = True

        review_data.append({
            'question': q,
            'selected_option': selected_option,
            'correct_option': correct_option,
            'is_user_correct': is_user_correct,
            'is_unanswered': selected_option is None
        })

    return render_template(
        'student/result_detail.html',
        result=result,
        student=student,
        college=college,
        exam=exam,
        attempt=attempt,
        review_data=review_data
    )


@results_bp.route('/<int:result_id>/download-pdf')
def download_pdf(result_id):
    result = ExamResult.query.get_or_404(result_id)

    # Authorization Check
    authorized = False
    if current_user.is_super_admin:
        authorized = True
    elif current_user.is_college_admin and current_user.college_id == result.college_id:
        authorized = True
    elif current_user.is_faculty and current_user.faculty_profile and result.college_id == current_user.college_id:
        if result.examination.faculty_id == current_user.faculty_profile.id:
            authorized = True
        elif FacultySubjectAssignment.query.filter_by(
            faculty_id=current_user.faculty_profile.id, subject_id=result.examination.subject_id
        ).first():
            authorized = True
    elif current_user.is_student and current_user.student_profile and result.student_id == current_user.student_profile.id:
        authorized = True

    if not authorized:
        abort(403)

    pdf_stream = generate_result_pdf(result)
    filename = f"Scorecard_{result.student.registration_number}_{result.examination.id}.pdf"

    return send_file(
        pdf_stream,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

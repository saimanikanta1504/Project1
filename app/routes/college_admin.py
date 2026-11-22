from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.extensions import db
from app.models import (
    College, User, StudentProfile, FacultyProfile, Course, Branch, Subject,
    Examination, ExamResult, FacultySubjectAssignment, AccountVerification
)
from app.utils import college_admin_required, ensure_college_access

college_admin_bp = Blueprint('college_admin', __name__)
college_admin_bp.before_request(college_admin_required)


@college_admin_bp.route('/dashboard')
def dashboard():
    college_id = current_user.college_id
    college = College.query.get_or_404(college_id)

    total_students = StudentProfile.query.filter_by(college_id=college_id).count()
    total_faculty = FacultyProfile.query.filter_by(college_id=college_id).count()
    total_courses = Course.query.filter_by(college_id=college_id).count()
    total_branches = Branch.query.filter_by(college_id=college_id).count()
    total_subjects = Subject.query.filter_by(college_id=college_id).count()
    total_exams = Examination.query.filter_by(college_id=college_id).count()

    courses = Course.query.filter_by(college_id=college_id).all()
    subjects = Subject.query.filter_by(college_id=college_id).all()

    selected_course_id = request.args.get('course_id', type=int)
    selected_subject_id = request.args.get('subject_id', type=int)

    exam_query = Examination.query.filter_by(college_id=college_id)
    if selected_course_id:
        exam_query = exam_query.filter_by(course_id=selected_course_id)
    if selected_subject_id:
        exam_query = exam_query.filter_by(subject_id=selected_subject_id)

    recent_exams = exam_query.order_by(Examination.created_at.desc()).limit(10).all()
    recent_students = StudentProfile.query.filter_by(college_id=college_id).order_by(StudentProfile.id.desc()).limit(5).all()

    # Pass rate calculation for analytics
    results = ExamResult.query.filter_by(college_id=college_id).all()
    total_attempts_evaluated = len(results)
    passed_attempts = sum(1 for r in results if r.is_passed)
    overall_pass_rate = round((passed_attempts / total_attempts_evaluated * 100), 1) if total_attempts_evaluated > 0 else 0.0

    return render_template(
        'college_admin/dashboard.html',
        college=college,
        courses=courses,
        subjects=subjects,
        selected_course_id=selected_course_id,
        selected_subject_id=selected_subject_id,
        total_students=total_students,
        total_faculty=total_faculty,
        total_courses=total_courses,
        total_branches=total_branches,
        total_subjects=total_subjects,
        total_exams=total_exams,
        total_attempts_evaluated=total_attempts_evaluated,
        overall_pass_rate=overall_pass_rate,
        recent_exams=recent_exams,
        recent_students=recent_students
    )


# ----------------- Academic Management ----------------- #

@college_admin_bp.route('/courses', methods=['GET', 'POST'])
def courses():
    college_id = current_user.college_id
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        duration_years = int(request.form.get('duration_years', 4))

        if not code or not name:
            flash('Course Code and Name are mandatory.', 'warning')
        elif Course.query.filter_by(college_id=college_id, code=code).first():
            flash(f'Course code "{code}" already exists in your college catalog.', 'danger')
        else:
            course = Course(college_id=college_id, code=code, name=name, duration_years=duration_years)
            db.session.add(course)
            db.session.commit()
            flash(f'Course "{name}" ({code}) created successfully.', 'success')
            return redirect(url_for('college_admin.courses'))

    all_courses = Course.query.filter_by(college_id=college_id).all()
    return render_template('college_admin/courses.html', courses=all_courses)


@college_admin_bp.route('/branches', methods=['GET', 'POST'])
def branches():
    college_id = current_user.college_id
    courses_list = Course.query.filter_by(college_id=college_id).all()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()

        if not course_id or not code or not name:
            flash('All branch fields are required.', 'warning')
        elif Branch.query.filter_by(college_id=college_id, course_id=course_id, code=code).first():
            flash(f'Branch with code "{code}" already registered under this course.', 'danger')
        else:
            branch = Branch(college_id=college_id, course_id=course_id, code=code, name=name)
            db.session.add(branch)
            db.session.commit()
            flash(f'Branch "{name}" ({code}) registered successfully.', 'success')
            return redirect(url_for('college_admin.branches'))

    all_branches = Branch.query.filter_by(college_id=college_id).all()
    return render_template('college_admin/branches.html', branches=all_branches, courses=courses_list)


@college_admin_bp.route('/subjects', methods=['GET', 'POST'])
def subjects():
    college_id = current_user.college_id
    courses_list = Course.query.filter_by(college_id=college_id).all()
    branches_list = Branch.query.filter_by(college_id=college_id).all()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        branch_id = request.form.get('branch_id')
        semester = int(request.form.get('semester', 1))
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        academic_year = request.form.get('academic_year', '2026-2027').strip()

        if not all([course_id, branch_id, code, name]):
            flash('All subject fields are mandatory.', 'warning')
        elif Subject.query.filter_by(college_id=college_id, branch_id=branch_id, semester=semester, code=code).first():
            flash(f'Subject code "{code}" already exists for this branch and semester.', 'danger')
        else:
            subject = Subject(
                college_id=college_id,
                course_id=course_id,
                branch_id=branch_id,
                semester=semester,
                code=code,
                name=name,
                academic_year=academic_year
            )
            db.session.add(subject)
            db.session.commit()
            flash(f'Subject "{name}" ({code}) added for Semester {semester}.', 'success')
            return redirect(url_for('college_admin.subjects'))

    all_subjects = Subject.query.filter_by(college_id=college_id).order_by(Subject.semester, Subject.code).all()
    return render_template('college_admin/subjects.html', subjects=all_subjects, courses=courses_list, branches=branches_list)


# ----------------- Student Management ----------------- #

@college_admin_bp.route('/students')
def students():
    college_id = current_user.college_id
    students_list = StudentProfile.query.filter_by(college_id=college_id).order_by(StudentProfile.registration_number).all()
    return render_template('college_admin/students.html', students=students_list)


@college_admin_bp.route('/students/<int:student_id>/approve', methods=['POST'])
def approve_student(student_id):
    college_id = current_user.college_id
    student = StudentProfile.query.filter_by(id=student_id, college_id=college_id).first_or_404()
    if student.user:
        student.user.registration_status = 'approved'
        student.user.is_active = True
        ver = AccountVerification.query.filter_by(user_id=student.user.id, status='pending_approval').first()
        if ver:
            ver.status = 'approved'
            ver.reviewed_at = datetime.utcnow()
            ver.reviewed_by_id = current_user.id
    student.registration_status = 'approved'
    db.session.commit()
    flash(f'Registration for candidate {student.full_name} ({student.registration_number}) has been approved and activated.', 'success')
    return redirect(url_for('college_admin.students'))


@college_admin_bp.route('/students/<int:student_id>/reject', methods=['POST'])
def reject_student(student_id):
    college_id = current_user.college_id
    student = StudentProfile.query.filter_by(id=student_id, college_id=college_id).first_or_404()
    if student.user:
        student.user.registration_status = 'rejected'
        student.user.is_active = False
        ver = AccountVerification.query.filter_by(user_id=student.user.id, status='pending_approval').first()
        if ver:
            ver.status = 'rejected'
            ver.reviewed_at = datetime.utcnow()
            ver.reviewed_by_id = current_user.id
    student.registration_status = 'rejected'
    db.session.commit()
    flash(f'Registration for candidate {student.full_name} ({student.registration_number}) has been rejected.', 'warning')
    return redirect(url_for('college_admin.students'))


@college_admin_bp.route('/students/new', methods=['GET', 'POST'])
def new_student():
    college_id = current_user.college_id
    courses_list = Course.query.filter_by(college_id=college_id).all()
    branches_list = Branch.query.filter_by(college_id=college_id).all()

    if request.method == 'POST':
        reg_number = request.form.get('registration_number', '').strip().upper()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        course_id = request.form.get('course_id')
        branch_id = request.form.get('branch_id')
        semester = int(request.form.get('semester', 1))
        academic_year = request.form.get('academic_year', '2026-2027').strip()
        contact = request.form.get('contact_number', '').strip()

        if not all([reg_number, first_name, last_name, email, password, course_id, branch_id]):
            flash('Please complete all mandatory student registration fields.', 'warning')
            return render_template('college_admin/student_form.html', courses=courses_list, branches=branches_list, is_edit=False)

        if User.query.filter((User.identifier == reg_number) | (User.email == email)).first():
            flash('A user with this Registration Number or Email already exists.', 'danger')
            return render_template('college_admin/student_form.html', courses=courses_list, branches=branches_list, is_edit=False)

        # Create user
        user = User(
            identifier=reg_number,
            email=email,
            role='student',
            college_id=college_id,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        profile = StudentProfile(
            user_id=user.id,
            registration_number=reg_number,
            first_name=first_name,
            last_name=last_name,
            college_id=college_id,
            course_id=course_id,
            branch_id=branch_id,
            semester=semester,
            academic_year=academic_year,
            contact_number=contact
        )
        db.session.add(profile)
        db.session.commit()

        flash(f'Student "{profile.full_name}" ({reg_number}) registered successfully.', 'success')
        return redirect(url_for('college_admin.students'))

    return render_template('college_admin/student_form.html', courses=courses_list, branches=branches_list, is_edit=False)


# ----------------- Faculty Management ----------------- #

@college_admin_bp.route('/faculty')
def faculty():
    college_id = current_user.college_id
    faculty_list = FacultyProfile.query.filter_by(college_id=college_id).order_by(FacultyProfile.faculty_id_code).all()
    return render_template('college_admin/faculty.html', faculty=faculty_list)


@college_admin_bp.route('/faculty/<int:faculty_id>/approve', methods=['POST'])
def approve_faculty(faculty_id):
    college_id = current_user.college_id
    fac = FacultyProfile.query.filter_by(id=faculty_id, college_id=college_id).first_or_404()
    if fac.user:
        fac.user.registration_status = 'approved'
        fac.user.is_active = True
        ver = AccountVerification.query.filter_by(user_id=fac.user.id, status='pending_approval').first()
        if ver:
            ver.status = 'approved'
            ver.reviewed_at = datetime.utcnow()
            ver.reviewed_by_id = current_user.id
    fac.registration_status = 'approved'
    db.session.commit()
    flash(f'Registration for faculty member {fac.full_name} ({fac.faculty_id_code}) has been approved and activated.', 'success')
    return redirect(url_for('college_admin.faculty'))


@college_admin_bp.route('/faculty/<int:faculty_id>/reject', methods=['POST'])
def reject_faculty(faculty_id):
    college_id = current_user.college_id
    fac = FacultyProfile.query.filter_by(id=faculty_id, college_id=college_id).first_or_404()
    if fac.user:
        fac.user.registration_status = 'rejected'
        fac.user.is_active = False
        ver = AccountVerification.query.filter_by(user_id=fac.user.id, status='pending_approval').first()
        if ver:
            ver.status = 'rejected'
            ver.reviewed_at = datetime.utcnow()
            ver.reviewed_by_id = current_user.id
    fac.registration_status = 'rejected'
    db.session.commit()
    flash(f'Registration for faculty member {fac.full_name} ({fac.faculty_id_code}) has been rejected.', 'warning')
    return redirect(url_for('college_admin.faculty'))


@college_admin_bp.route('/faculty/new', methods=['GET', 'POST'])
def new_faculty():
    college_id = current_user.college_id

    if request.method == 'POST':
        fac_code = request.form.get('faculty_id_code', '').strip().upper()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        dept = request.form.get('department_name', '').strip()
        designation = request.form.get('designation', 'Assistant Professor').strip()
        phone = request.form.get('contact_number', '').strip()

        if not all([fac_code, first_name, last_name, email, password, dept]):
            flash('Please complete all required faculty information fields.', 'warning')
            return render_template('college_admin/faculty_form.html', is_edit=False)

        if User.query.filter((User.identifier == fac_code) | (User.email == email)).first():
            flash('A faculty user with this Faculty ID or Email already exists.', 'danger')
            return render_template('college_admin/faculty_form.html', is_edit=False)

        user = User(
            identifier=fac_code,
            email=email,
            role='faculty',
            college_id=college_id,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        profile = FacultyProfile(
            user_id=user.id,
            faculty_id_code=fac_code,
            first_name=first_name,
            last_name=last_name,
            college_id=college_id,
            designation=designation,
            department_name=dept,
            contact_number=phone
        )
        db.session.add(profile)
        db.session.commit()

        flash(f'Faculty member "{profile.full_name}" registered successfully.', 'success')
        return redirect(url_for('college_admin.faculty'))

    return render_template('college_admin/faculty_form.html', is_edit=False)


# ----------------- Examination & Results Oversight ----------------- #

@college_admin_bp.route('/examinations')
def examinations():
    college_id = current_user.college_id
    exams = Examination.query.filter_by(college_id=college_id).order_by(Examination.exam_date.desc()).all()
    return render_template('college_admin/examinations.html', examinations=exams)


@college_admin_bp.route('/results')
def results():
    college_id = current_user.college_id
    results_list = ExamResult.query.filter_by(college_id=college_id).order_by(ExamResult.evaluated_at.desc()).all()
    return render_template('college_admin/results.html', results=results_list)

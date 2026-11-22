import pytest
from datetime import datetime, date, time
from app import create_app
from app.extensions import db
from app.models import (
    College, User, StudentProfile, FacultyProfile, CollegeAdminProfile,
    Course, Branch, Subject, Examination, Question, Option, ExamAttempt,
    StudentAnswer, ExamResult
)
from app.utils import evaluate_exam_attempt, generate_result_pdf


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # Seed test college 1
        col1 = College(
            name='ABC Engineering College',
            code='ABCENG',
            address='Tech City, Hyderabad',
            email='info@abccollege.edu',
            contact_number='+91 40 1234 5678',
            logo_filename='default_college_logo.png',
            status='active'
        )
        # Seed test college 2 (for multi-tenant isolation verification)
        col2 = College(
            name='XYZ Institute of Technology',
            code='XYZTECH',
            address='Knowledge Park, Bengaluru',
            email='info@xyztech.edu',
            contact_number='+91 80 8765 4321',
            logo_filename='default_college_logo.png',
            status='active'
        )
        db.session.add_all([col1, col2])
        db.session.flush()

        # Seed Course, Branch, Subject for College 1
        course1 = Course(college_id=col1.id, code='BTECH', name='Bachelor of Technology')
        db.session.add(course1)
        db.session.flush()

        branch1 = Branch(college_id=col1.id, course_id=course1.id, code='CSE', name='Computer Science')
        db.session.add(branch1)
        db.session.flush()

        subject1 = Subject(
            college_id=col1.id, course_id=course1.id, branch_id=branch1.id,
            semester=3, code='CS301', name='Data Structures', academic_year='2026-2027'
        )
        db.session.add(subject1)
        db.session.flush()

        # Super Admin
        super_admin = User(identifier='SUPERADMIN', email='super@uni.edu', role='super_admin')
        super_admin.set_password('Secret123')

        # College 1 Admin
        c1_admin = User(identifier='ADM-ABC', email='admin@abc.edu', role='college_admin', college_id=col1.id)
        c1_admin.set_password('Secret123')
        c1_admin_prof = CollegeAdminProfile(user=c1_admin, admin_id_code='ADM-ABC', full_name='Admin ABC', college_id=col1.id)

        # College 1 Faculty
        c1_fac = User(identifier='FAC-ABC', email='faculty@abc.edu', role='faculty', college_id=col1.id)
        c1_fac.set_password('Secret123')
        c1_fac_prof = FacultyProfile(
            user=c1_fac, faculty_id_code='FAC-ABC', first_name='Ramesh', last_name='Varma',
            college_id=col1.id, department_name='CSE'
        )

        # College 1 Student A
        st_a = User(identifier='2025DAMBT11765', email='sai@abc.edu', role='student', college_id=col1.id)
        st_a.set_password('Secret123')
        st_a_prof = StudentProfile(
            user=st_a, registration_number='2025DAMBT11765', first_name='Sai', last_name='Kumar',
            college_id=col1.id, course_id=course1.id, branch_id=branch1.id, semester=3, academic_year='2026-2027'
        )

        # College 2 Student B
        st_b = User(identifier='2025DAMBT11766', email='student@xyz.edu', role='student', college_id=col2.id)
        st_b.set_password('Secret123')
        # Setup course & branch for College 2
        course2 = Course(college_id=col2.id, code='BTECH', name='Bachelor of Technology')
        db.session.add(course2)
        db.session.flush()
        branch2 = Branch(college_id=col2.id, course_id=course2.id, code='CSE', name='Computer Science')
        db.session.add(branch2)
        db.session.flush()
        st_b_prof = StudentProfile(
            user=st_b, registration_number='2025DAMBT11766', first_name='Alex', last_name='Peter',
            college_id=col2.id, course_id=course2.id, branch_id=branch2.id, semester=3, academic_year='2026-2027'
        )

        db.session.add_all([super_admin, c1_admin, c1_admin_prof, c1_fac, c1_fac_prof, st_a, st_a_prof, st_b, st_b_prof])
        db.session.commit()

        # Create Exam under College 1
        exam = Examination(
            college_id=col1.id,
            faculty_id=c1_fac_prof.id,
            course_id=course1.id,
            branch_id=branch1.id,
            semester=3,
            subject_id=subject1.id,
            title='Data Structures Quiz',
            exam_date=date.today(),
            start_time=time(9, 0),
            end_time=time(18, 0),
            duration_minutes=30,
            passing_percentage=40.0,
            max_attempts=1,
            negative_marking=True,
            negative_mark_value=0.25,
            status='active'
        )
        db.session.add(exam)
        db.session.flush()

        # Add 2 questions with 4 options each
        q1 = Question(examination_id=exam.id, question_number=1, question_text='What is LIFO?', marks=1.0, negative_marks=0.25)
        q2 = Question(examination_id=exam.id, question_number=2, question_text='What is FIFO?', marks=1.0, negative_marks=0.25)
        db.session.add_all([q1, q2])
        db.session.flush()

        opt1_1 = Option(question_id=q1.id, option_number=1, option_text='Stack', is_correct=True)
        opt1_2 = Option(question_id=q1.id, option_number=2, option_text='Queue', is_correct=False)
        opt1_3 = Option(question_id=q1.id, option_number=3, option_text='Tree', is_correct=False)
        opt1_4 = Option(question_id=q1.id, option_number=4, option_text='Array', is_correct=False)

        opt2_1 = Option(question_id=q2.id, option_number=1, option_text='Stack', is_correct=False)
        opt2_2 = Option(question_id=q2.id, option_number=2, option_text='Queue', is_correct=True)
        opt2_3 = Option(question_id=q2.id, option_number=3, option_text='Tree', is_correct=False)
        opt2_4 = Option(question_id=q2.id, option_number=4, option_text='Graph', is_correct=False)

        db.session.add_all([opt1_1, opt1_2, opt1_3, opt1_4, opt2_1, opt2_2, opt2_3, opt2_4])
        exam.calculate_total_marks()
        db.session.commit()

        yield app

        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# Test 1 & 2: Student Login & Credential Verification
def test_authentication(client):
    # Reject invalid password
    res_fail = client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'WrongPassword', 'role': 'student'})
    assert b'Invalid credentials' in res_fail.data

    # Accept valid credentials
    res_ok = client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Secret123', 'role': 'student'}, follow_redirects=True)
    assert res_ok.status_code == 200
    assert b'ABC Engineering College' in res_ok.data


# Test 3 & 4: Automatic College Identification
def test_automatic_college_identification(client):
    # Student A logs in (No manual college selection)
    client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Secret123', 'role': 'student'})
    dash_res = client.get('/student/dashboard')
    assert b'ABC Engineering College' in dash_res.data
    assert b'ABCENG' in dash_res.data
    assert b'default_college_logo.png' in dash_res.data
    assert b'Sai Kumar' in dash_res.data

    # Student B logs in (Different college)
    client.get('/auth/logout')
    client.post('/auth/login', data={'identifier': '2025DAMBT11766', 'password': 'Secret123', 'role': 'student'})
    dash_b = client.get('/student/dashboard')
    assert b'XYZ Institute of Technology' in dash_b.data
    assert b'XYZTECH' in dash_b.data
    assert b'Alex Peter' in dash_b.data


# Test 5: Cross-College Data Isolation
def test_cross_college_isolation(client):
    # Student B belongs to College 2. College 1's exam has ID 1.
    client.post('/auth/login', data={'identifier': '2025DAMBT11766', 'password': 'Secret123', 'role': 'student'})
    # Attempting to access instructions for College 1's exam
    res = client.get('/exam/1/instructions')
    assert res.status_code == 403


# Test 6 & 7: Branches and Subjects Loaded From DB
def test_branches_and_subjects_loaded(client):
    client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Secret123', 'role': 'student'})
    res = client.get('/student/subjects')
    assert res.status_code == 200
    assert b'Data Structures' in res.data
    assert b'CS301' in res.data


# Test 8 & 9: Faculty Exam Creation & Questions
def test_faculty_exam_creation(client):
    client.post('/auth/login', data={'identifier': 'FAC-ABC', 'password': 'Secret123', 'role': 'faculty'})
    # Create new exam
    res = client.post('/faculty/examinations/create', data={
        'title': 'Operating Systems Midterm',
        'course_id': 1,
        'branch_id': 1,
        'semester': 3,
        'subject_id': 1,
        'exam_date': '2026-11-25',
        'start_time': '10:00',
        'end_time': '11:00',
        'duration_minutes': 60,
        'passing_percentage': 40.0,
        'max_attempts': 1,
        'instructions': 'Test Instructions'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Operating Systems Midterm' in res.data


# Test 10, 11, 14, 15: Exam Attendance, Saving Answers & Auto-Evaluation
def test_exam_flow_and_evaluation(client):
    # Login Student A
    client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Secret123', 'role': 'student'})

    # Start Exam 1
    start_res = client.post('/exam/1/start', follow_redirects=True)
    assert start_res.status_code == 200
    assert b'Data Structures Quiz' in start_res.data

    attempt = ExamAttempt.query.filter_by(student_id=1, examination_id=1).first()
    assert attempt is not None

    # Answer Q1 correctly (Option 1 = Stack)
    save_res1 = client.post(f'/exam/{attempt.id}/save-answer', json={
        'question_id': 1,
        'selected_option_id': 1,
        'is_marked_for_review': False
    })
    assert save_res1.status_code == 200

    # Answer Q2 incorrectly (Option 1 = Stack, correct is Option 2 Queue)
    save_res2 = client.post(f'/exam/{attempt.id}/save-answer', json={
        'question_id': 2,
        'selected_option_id': 5,
        'is_marked_for_review': True
    })
    assert save_res2.status_code == 200

    # Submit Exam
    sub_res = client.post(f'/exam/{attempt.id}/submit', follow_redirects=True)
    assert sub_res.status_code == 200
    assert b'EXAMINATION RESULT' in sub_res.data

    # Check Evaluation: Total 2, 1 Correct (1.0), 1 Wrong (0.25 penalty) => 0.75 / 2.0 = 37.5% (< 40% Fail)
    result = ExamResult.query.filter_by(attempt_id=attempt.id).first()
    assert result is not None
    assert result.correct_answers == 1
    assert result.wrong_answers == 1
    assert result.obtained_marks == 0.75
    assert result.percentage == 37.5
    assert result.is_passed is False


# Test 16: ReportLab PDF Generation
def test_pdf_scorecard_generation(client):
    client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Secret123', 'role': 'student'})
    attempt = ExamAttempt.query.filter_by(student_id=1, examination_id=1).first()
    if not attempt:
        attempt = ExamAttempt(examination_id=1, student_id=1, college_id=1, status='in_progress')
        db.session.add(attempt)
        db.session.commit()
    result = ExamResult.query.filter_by(attempt_id=attempt.id).first()
    if not result:
        result = evaluate_exam_attempt(attempt)

    pdf_res = client.get(f'/results/{result.id}/download-pdf')
    assert pdf_res.status_code == 200
    assert pdf_res.mimetype == 'application/pdf'
    assert len(pdf_res.data) > 1000  # Verify non-empty valid PDF bytes


# Test 17: Unauthorized Role Access Blocked
def test_unauthorized_role_access(client):
    # Student attempts to access Super Admin dashboard
    client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Secret123'})
    admin_access = client.get('/super-admin/dashboard')
    assert admin_access.status_code == 403


# Test 18: Unified Login & Strict Role Isolation Across All 4 Roles
def test_unified_login_and_strict_role_isolation(client):
    # 1. Student Login -> Redirects directly to Student Dashboard
    res_st = client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Secret123'}, follow_redirects=False)
    assert res_st.status_code == 302
    assert '/student/dashboard' in res_st.headers['Location']

    st_dash = client.get('/student/dashboard')
    assert st_dash.status_code == 200
    assert b'ABC Engineering College' in st_dash.data
    assert b'Sai Kumar' in st_dash.data

    # Student cannot access faculty, college admin, or super admin dashboards
    assert client.get('/faculty/dashboard').status_code == 403
    assert client.get('/college-admin/dashboard').status_code == 403
    assert client.get('/super-admin/dashboard').status_code == 403

    # 2. Faculty Login -> Redirects directly to Faculty Dashboard
    client.get('/auth/logout')
    res_fac = client.post('/auth/login', data={'identifier': 'FAC-ABC', 'password': 'Secret123'}, follow_redirects=False)
    assert res_fac.status_code == 302
    assert '/faculty/dashboard' in res_fac.headers['Location']

    fac_dash = client.get('/faculty/dashboard')
    assert fac_dash.status_code == 200
    assert b'Ramesh' in fac_dash.data

    # Faculty cannot access student, college admin, or super admin dashboards
    assert client.get('/student/dashboard').status_code == 403
    assert client.get('/college-admin/dashboard').status_code == 403
    assert client.get('/super-admin/dashboard').status_code == 403

    # 3. College Admin Login -> Redirects directly to College Admin Dashboard
    client.get('/auth/logout')
    res_adm = client.post('/auth/login', data={'identifier': 'ADM-ABC', 'password': 'Secret123'}, follow_redirects=False)
    assert res_adm.status_code == 302
    assert '/college-admin/dashboard' in res_adm.headers['Location']

    adm_dash = client.get('/college-admin/dashboard')
    assert adm_dash.status_code == 200
    assert b'ABC Engineering College' in adm_dash.data

    # College admin cannot access student or super admin dashboards
    assert client.get('/student/dashboard').status_code == 403
    assert client.get('/super-admin/dashboard').status_code == 403

    # 4. Super Admin Login -> Redirects directly to Super Admin Dashboard
    client.get('/auth/logout')
    res_sup = client.post('/auth/login', data={'identifier': 'SUPERADMIN', 'password': 'Secret123'}, follow_redirects=False)
    assert res_sup.status_code == 302
    assert '/super-admin/dashboard' in res_sup.headers['Location']

    sup_dash = client.get('/super-admin/dashboard')
    assert sup_dash.status_code == 200

    # Super admin cannot access student or faculty dashboards
    assert client.get('/student/dashboard').status_code == 403
    assert client.get('/faculty/dashboard').status_code == 403


def test_student_instructions_route_safe_redirect(client):
    """Verify /student/instructions gracefully redirects to dashboard without 500 error."""
    client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Secret123'})
    resp = client.get('/student/instructions', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Please select an active examination' in resp.data



import pytest
from datetime import datetime, date, time, timedelta
from app import create_app
from app.extensions import db
from app.models import (
    College, User, StudentProfile, FacultyProfile, CollegeAdminProfile,
    AdminProfile, Course, Branch, Subject, Examination, Question, Option,
    ExamAttempt, StudentAnswer, ExamResult
)
from app.demo_service import (
    get_or_create_demo_college, reset_demo_examination_data, purge_demo_accounts
)


@pytest.fixture
def demo_app():
    app = create_app('testing')
    app.config['DEMO_MODE_ENABLED'] = True
    with app.app_context():
        db.create_all()

        # Seed Real Production College 1
        real_college = College(
            name='ABC Engineering College',
            code='ABCENG',
            address='Tech City, Hyderabad',
            email='info@abccollege.edu',
            contact_number='+91 40 1234 5678',
            email_domain='abccollege.edu',
            status='active',
            is_demo=False
        )
        db.session.add(real_college)
        db.session.flush()

        rcourse = Course(college_id=real_college.id, code='BTECH', name='Bachelor of Technology')
        rbranch = Branch(college_id=real_college.id, course=rcourse, code='CSE', name='Computer Science')
        db.session.add_all([rcourse, rbranch])
        db.session.flush()

        rsub = Subject(college_id=real_college.id, course_id=rcourse.id, branch_id=rbranch.id, semester=3, code='CS301', name='Data Structures')
        db.session.add(rsub)
        db.session.flush()

        # Real Super Admin
        real_sup = User(
            identifier='SUPERADMIN',
            email='superadmin@portal.edu',
            role='super_admin',
            is_active=True,
            registration_status='approved',
            is_demo=False
        )
        real_sup.set_password('Password@123')

        # Real College Admin
        real_adm = User(
            identifier='ADM-ABC-01',
            email='admin@abccollege.edu',
            role='college_admin',
            college_id=real_college.id,
            is_active=True,
            registration_status='approved',
            is_demo=False
        )
        real_adm.set_password('Password@123')
        real_adm_p = CollegeAdminProfile(user=real_adm, admin_id_code='ADM-ABC-01', full_name='Dr. Real Admin', college_id=real_college.id)

        # Real Faculty
        real_fac = User(
            identifier='FAC-ABC-01',
            email='anita.sharma@abccollege.edu',
            role='faculty',
            college_id=real_college.id,
            is_active=True,
            registration_status='approved',
            is_demo=False
        )
        real_fac.set_password('Password@123')
        real_fac_p = FacultyProfile(user=real_fac, faculty_id_code='FAC-ABC-01', first_name='Anita', last_name='Sharma', college_id=real_college.id, department_name='CSE', registration_status='approved')

        # Real Student
        real_st = User(
            identifier='2025DAMBT11765',
            email='sai.kumar@abccollege.edu',
            role='student',
            college_id=real_college.id,
            is_active=True,
            registration_status='approved',
            is_demo=False
        )
        real_st.set_password('Password@123')
        real_st_p = StudentProfile(
            user=real_st,
            registration_number='2025DAMBT11765',
            first_name='Sai',
            last_name='Kumar',
            college_id=real_college.id,
            course_id=rcourse.id,
            branch_id=rbranch.id,
            semester=3
        )

        db.session.add_all([real_sup, real_adm, real_adm_p, real_fac, real_fac_p, real_st, real_st_p])
        db.session.commit()

        yield app
        db.session.remove()
        db.drop_all()


# 1. Demo student can log in with new demonstration information
def test_1_demo_student_can_login_with_new_info(demo_app):
    client = demo_app.test_client()
    res = client.post('/auth/demo-login', data={
        'role': 'student',
        'name': 'Demo Candidate Alex',
        'email': 'alex.test@example.com',
        'roll_number': 'DEMO-ALEX-01',
        'branch': 'CSE',
        'password': 'DemoPassword@123'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'Student Dashboard' in res.data or b'Student Portal' in res.data
    assert b'Demonstration Session Active' in res.data


# 2. Demo faculty can log in with new demonstration information
def test_2_demo_faculty_can_login_with_new_info(demo_app):
    client = demo_app.test_client()
    res = client.post('/auth/demo-login', data={
        'role': 'faculty',
        'name': 'Dr. Alan Turing',
        'email': 'alan.turing@demotech.edu',
        'faculty_id': 'FAC-DEMO-TURING',
        'department': 'Computer Science & Engineering',
        'password': 'DemoFaculty@123'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'Faculty Dashboard' in res.data or b'Faculty' in res.data
    assert b'FAC-DEMO-TURING' in res.data or b'Alan Turing' in res.data


# 3. Demo College Admin can log in with new demonstration information
def test_3_demo_college_admin_can_login_with_new_info(demo_app):
    client = demo_app.test_client()
    res = client.post('/auth/demo-login', data={
        'role': 'college_admin',
        'name': 'Administrator Radhakrishnan',
        'email': 'radha.admin@demotech.edu',
        'admin_id': 'ADM-DEMO-RADHA',
        'password': 'DemoAdmin@123'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'College Administrator' in res.data or b'College Admin' in res.data
    assert b'ADM-DEMO-RADHA' in res.data or b'Radhakrishnan' in res.data


# 4. Demo accounts are saved in the database
def test_4_demo_accounts_saved_in_database(demo_app):
    client = demo_app.test_client()
    client.post('/auth/demo-login', data={
        'role': 'student',
        'name': 'John Doe Demo',
        'email': 'john.doe.demo@example.com',
        'roll_number': 'DEMO-JOHNDOE-99',
        'password': 'DemoPassword@123'
    })

    with demo_app.app_context():
        user = User.query.filter_by(email='john.doe.demo@example.com').first()
        assert user is not None
        assert user.is_demo is True
        assert user.account_type == 'demo'
        assert user.identifier == 'DEMO-JOHNDOE-99'
        assert user.student_profile is not None
        assert user.college.is_demo is True


# 5. Existing accounts continue working
def test_5_existing_accounts_continue_working(demo_app):
    client = demo_app.test_client()
    # Log in real student via normal login
    res = client.post('/auth/login', data={
        'identifier': '2025DAMBT11765',
        'password': 'Password@123'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'Student' in res.data

    # Log in real faculty via normal login
    client.get('/auth/logout')
    res_fac = client.post('/auth/login', data={
        'identifier': 'FAC-ABC-01',
        'password': 'Password@123'
    }, follow_redirects=True)

    assert res_fac.status_code == 200
    assert b'Faculty' in res_fac.data


# 6. Normal login still requires valid credentials
def test_6_normal_login_still_requires_valid_credentials(demo_app):
    client = demo_app.test_client()
    # Random unapproved credentials in normal login mode must fail
    res = client.post('/auth/login', data={
        'identifier': 'arbitrary_non_existent@example.com',
        'password': 'WrongPassword@123'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'Invalid credentials' in res.data


# 7. Demo accounts cannot access real college records
def test_7_demo_accounts_cannot_access_real_college_records(demo_app):
    client = demo_app.test_client()
    # Log in demo student
    client.post('/auth/demo-login', data={
        'role': 'student',
        'name': 'Demo Security Tester',
        'email': 'tester.sec@demotech.edu',
        'roll_number': 'DEMO-SEC-01',
        'password': 'DemoPassword@123'
    }, follow_redirects=True)

    with demo_app.app_context():
        demo_user = User.query.filter_by(email='tester.sec@demotech.edu').first()
        real_college = College.query.filter_by(code='ABCENG').first()
        assert demo_user.college_id != real_college.id
        assert demo_user.college.is_demo is True

    # Attempt to access real college admin route or forbidden endpoints
    res = client.get('/college-admin/dashboard')
    assert res.status_code == 403


# 8. Demo student can attempt a demonstration examination
def test_8_demo_student_can_attempt_demonstration_examination(demo_app):
    client = demo_app.test_client()
    client.post('/auth/demo-login', data={
        'role': 'student',
        'name': 'Exam Tester Student',
        'email': 'exam.tester@demotech.edu',
        'roll_number': 'DEMO-EXAM-TEST',
        'branch': 'CSE',
        'password': 'DemoPassword@123'
    }, follow_redirects=True)

    with demo_app.app_context():
        demo_exam = Examination.query.filter_by(is_demo=True).first()
        assert demo_exam is not None
        exam_id = demo_exam.id
        q1 = demo_exam.questions[0]
        correct_opt = [o for o in q1.options if o.is_correct][0]

    # Start examination
    res_start = client.post(f'/exam/{exam_id}/start', follow_redirects=True)
    assert res_start.status_code == 200

    with demo_app.app_context():
        user = User.query.filter_by(email='exam.tester@demotech.edu').first()
        attempt = ExamAttempt.query.filter_by(student_id=user.student_profile.id, status='in_progress').first()
        assert attempt is not None
        attempt_id = attempt.id

    # Submit answer to question using attempt_id and selected_option_id
    res_ans = client.post(f'/exam/{attempt_id}/save-answer', json={
        'question_id': q1.id,
        'selected_option_id': correct_opt.id
    })
    assert res_ans.status_code == 200

    # Submit examination
    res_submit = client.post(f'/exam/{attempt_id}/submit', follow_redirects=True)
    assert res_submit.status_code == 200
    assert b'Result' in res_submit.data or b'Score' in res_submit.data or b'Examination Completed' in res_submit.data or b'passed' in res_submit.data.lower()

    with demo_app.app_context():
        user = User.query.filter_by(email='exam.tester@demotech.edu').first()
        result = ExamResult.query.filter_by(student_id=user.student_profile.id).first()
        assert result is not None
        assert result.obtained_marks >= 2.0


# 9. Faculty can create a demonstration examination
def test_9_demo_faculty_can_create_demonstration_examination(demo_app):
    client = demo_app.test_client()
    client.post('/auth/demo-login', data={
        'role': 'faculty',
        'name': 'Dr. Demo Author',
        'email': 'author.faculty@demotech.edu',
        'faculty_id': 'FAC-DEMO-AUTH',
        'password': 'DemoPassword@123'
    }, follow_redirects=True)

    with demo_app.app_context():
        fac_user = User.query.filter_by(email='author.faculty@demotech.edu').first()
        course = Course.query.filter_by(college_id=fac_user.college_id).first()
        branch = Branch.query.filter_by(college_id=fac_user.college_id).first()
        subject = Subject.query.filter_by(college_id=fac_user.college_id).first()
        c_id = course.id
        b_id = branch.id
        s_id = subject.id

    # Create new exam via /faculty/examinations/create
    res = client.post('/faculty/examinations/create', data={
        'title': 'Faculty Created Demo Test',
        'course_id': c_id,
        'branch_id': b_id,
        'semester': 5,
        'subject_id': s_id,
        'exam_date': date.today().isoformat(),
        'start_time': '10:00',
        'end_time': '12:00',
        'duration_minutes': 60,
        'passing_percentage': 40.0,
        'max_attempts': 1,
        'instructions': 'Please complete all questions carefully.'
    }, follow_redirects=True)

    assert res.status_code == 200
    with demo_app.app_context():
        created_exam = Examination.query.filter_by(title='Faculty Created Demo Test').first()
        assert created_exam is not None
        author_user = User.query.filter_by(email='author.faculty@demotech.edu').first()
        assert created_exam.faculty_id == author_user.faculty_profile.id


# 10. Faculty can view demonstration attendance
def test_10_demo_faculty_can_view_demonstration_attendance(demo_app):
    client = demo_app.test_client()
    client.post('/auth/demo-login', data={
        'role': 'faculty',
        'name': 'Dr. Attendance Viewer',
        'email': 'attendance.viewer@demotech.edu',
        'faculty_id': 'FAC-DEMO-ATT',
        'password': 'DemoPassword@123'
    }, follow_redirects=True)

    with demo_app.app_context():
        demo_exam = Examination.query.filter_by(is_demo=True).first()
        exam_id = demo_exam.id

    res = client.get(f'/faculty/examination-reports/{exam_id}')
    assert res.status_code == 200
    # Baseline cohort attendance check: Attended students vs Absent
    assert b'Priya' in res.data or b'Registered' in res.data
    assert b'Attended' in res.data


# 11. Faculty can view marks and rankings
def test_11_demo_faculty_can_view_marks_and_rankings(demo_app):
    client = demo_app.test_client()
    client.post('/auth/demo-login', data={
        'role': 'faculty',
        'name': 'Dr. Marks Examiner',
        'email': 'marks.examiner@demotech.edu',
        'faculty_id': 'FAC-DEMO-MARKS',
        'password': 'DemoPassword@123'
    }, follow_redirects=True)

    with demo_app.app_context():
        demo_exam = Examination.query.filter_by(is_demo=True).first()
        exam_id = demo_exam.id

    res = client.get(f'/faculty/examination-reports/{exam_id}')
    assert res.status_code == 200
    # Checks ranking / performance table
    assert b'Marks' in res.data or b'Score' in res.data
    assert b'Rank' in res.data or b'Ranking' in res.data


# 12. College Admin can manage demo records
def test_12_demo_college_admin_can_manage_demo_records(demo_app):
    client = demo_app.test_client()
    client.post('/auth/demo-login', data={
        'role': 'college_admin',
        'name': 'Admin Demo Manager',
        'email': 'manager.admin@demotech.edu',
        'admin_id': 'ADM-DEMO-MGR',
        'password': 'DemoPassword@123'
    }, follow_redirects=True)

    res_dash = client.get('/college-admin/dashboard')
    assert res_dash.status_code == 200

    # View demo students in college admin
    res_students = client.get('/college-admin/students')
    assert res_students.status_code == 200
    assert b'Priya' in res_students.data or b'DEMO' in res_students.data


# 13. Super Admin access remains protected
def test_13_super_admin_access_remains_protected(demo_app):
    client = demo_app.test_client()
    # Attempting to dynamically create a Super Admin via Demo Login must be rejected
    res = client.post('/auth/demo-login', data={
        'role': 'super_admin',
        'name': 'Hacker Intruder',
        'email': 'intruder@hack.com',
        'password': 'BadPassword@123'
    }, follow_redirects=True)

    assert b'Super Administrator accounts cannot be created' in res.data

    # Ensure no Super Admin was created
    with demo_app.app_context():
        intruder = User.query.filter_by(email='intruder@hack.com').first()
        assert intruder is None


# 14. Demo Mode can be disabled
def test_14_demo_mode_can_be_disabled(demo_app):
    demo_app.config['DEMO_MODE_ENABLED'] = False
    client = demo_app.test_client()

    res = client.post('/auth/demo-login', data={
        'role': 'student',
        'name': 'Disabled Mode User',
        'email': 'disabled.test@demotech.edu',
        'roll_number': 'DEMO-DIS-01',
        'password': 'DemoPassword@123'
    }, follow_redirects=True)

    assert b'Demonstration Mode is disabled' in res.data
    with demo_app.app_context():
        user = User.query.filter_by(email='disabled.test@demotech.edu').first()
        assert user is None


# 15. No real user records are affected during demo operations or cleanup
def test_15_no_real_user_records_are_affected(demo_app):
    with demo_app.app_context():
        real_user_count_before = User.query.filter_by(is_demo=False).count()
        real_col_count_before = College.query.filter_by(is_demo=False).count()

    # Create dynamic demo records
    client = demo_app.test_client()
    client.post('/auth/demo-login', data={
        'role': 'student',
        'name': 'Transient Candidate',
        'email': 'transient@demotech.edu',
        'roll_number': 'DEMO-TRANS-01',
        'password': 'DemoPassword@123'
    })

    # Run cleanup functions
    with demo_app.app_context():
        reset_demo_examination_data()
        purge_demo_accounts(preserve_baseline_cohort=True)

        real_user_count_after = User.query.filter_by(is_demo=False).count()
        real_col_count_after = College.query.filter_by(is_demo=False).count()

        # Real records must be 100% unchanged
        assert real_user_count_after == real_user_count_before
        assert real_col_count_after == real_col_count_before
        assert User.query.filter_by(email='superadmin@portal.edu').first() is not None
        assert User.query.filter_by(email='sai.kumar@abccollege.edu').first() is not None

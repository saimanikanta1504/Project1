import pytest
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import (
    College, User, StudentProfile, FacultyProfile, CollegeAdminProfile,
    AdminProfile, PasswordResetToken, AccountVerification, Course, Branch, Subject
)


@pytest.fixture
def multi_role_app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # Seed College 1
        col1 = College(
            name='ABC Engineering College', code='ABCENG',
            address='Tech City, Hyderabad', email='info@abccollege.edu',
            contact_number='+91 40 1234 5678', email_domain='abccollege.edu',
            status='active'
        )
        # Seed College 2 (for multi-tenant isolation testing)
        col2 = College(
            name='Apex Institute of Technology', code='APEX',
            address='Electronic City, Bengaluru', email='info@apexinstitute.edu',
            contact_number='+91 80 9876 5432', email_domain='apexinstitute.edu',
            status='active'
        )
        db.session.add_all([col1, col2])
        db.session.flush()

        course1 = Course(college_id=col1.id, code='BTECH', name='Bachelor of Technology')
        branch1 = Branch(college_id=col1.id, course=course1, code='CSE', name='Computer Science')
        db.session.add_all([course1, branch1])
        db.session.flush()

        subject1 = Subject(college_id=col1.id, course_id=course1.id, branch_id=branch1.id, semester=3, code='CS301', name='Data Structures')
        db.session.add(subject1)
        db.session.flush()

        # 1. Super Admin
        sup = User(identifier='SUPERADMIN', email='superadmin@portal.edu', role='super_admin', is_active=True, registration_status='approved')
        sup.set_password('Password@123')

        # 2. College Admin
        adm = User(identifier='ADM-ABC-01', email='admin@abccollege.edu', role='college_admin', college_id=col1.id, is_active=True, registration_status='approved')
        adm.set_password('Password@123')
        adm_p = CollegeAdminProfile(user=adm, admin_id_code='ADM-ABC-01', full_name='Dr. Ramanathan', college_id=col1.id)
        adm_ap = AdminProfile(user=adm, admin_id_code='ADM-ABC-01', full_name='Dr. Ramanathan', college_id=col1.id, registration_status='approved')

        # 3. Faculty
        fac = User(identifier='FAC-ABC-01', email='anita.sharma@abccollege.edu', role='faculty', college_id=col1.id, is_active=True, registration_status='approved')
        fac.set_password('Password@123')
        fac_p = FacultyProfile(user=fac, faculty_id_code='FAC-ABC-01', first_name='Anita', last_name='Sharma', college_id=col1.id, department_name='CSE', registration_status='approved')

        # 4. Student
        st = User(identifier='2025DAMBT11765', email='sai.kumar@abccollege.edu', role='student', college_id=col1.id, is_active=True, registration_status='approved')
        st.set_password('Password@123')
        st_p = StudentProfile(user=st, registration_number='2025DAMBT11765', first_name='Sai', last_name='Kumar', college_id=col1.id, course_id=course1.id, branch_id=branch1.id, semester=3, registration_status='approved')

        db.session.add_all([sup, adm, adm_p, adm_ap, fac, fac_p, st, st_p])
        db.session.commit()

        yield app

        db.drop_all()


@pytest.fixture
def client(multi_role_app):
    return multi_role_app.test_client()


# Requirement 1: Student can register a new account
def test_1_student_can_register(client):
    res = client.post('/auth/signup/student', data={
        'full_name': 'Aarav Patel',
        'college_id': 1,
        'roll_number': '2025DAMBT11801',
        'phone_number': '9876543210',
        'email': 'aarav.patel@gmail.com',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'PENDING VERIFICATION' in res.data or b'Registration submitted' in res.data

    user = User.query.filter_by(identifier='2025DAMBT11801').first()
    assert user is not None
    assert user.role == 'student'
    assert user.registration_status in ('pending_verification', 'pending_approval')
    assert user.is_active is False
    assert user.student_profile is not None


# Requirement 2: Faculty can register a new account
def test_2_faculty_can_register(client):
    res = client.post('/auth/signup/faculty', data={
        'full_name': 'Dr. Suresh Kumar',
        'college_id': 1,
        'faculty_id': 'FAC-ABC-02',
        'phone_number': '9849012345',
        'email': 'suresh.k@abccollege.edu',
        'department_name': 'Computer Science',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'PENDING APPROVAL' in res.data

    fac_user = User.query.filter_by(identifier='FAC-ABC-02').first()
    assert fac_user is not None
    assert fac_user.role == 'faculty'
    assert fac_user.registration_status == 'pending_approval'
    assert fac_user.is_active is False
    assert fac_user.faculty_profile is not None


# Requirement 3: College Admin registration requires Super Admin approval
def test_3_college_admin_requires_super_admin_approval(client):
    # 1. Register College Admin
    res = client.post('/auth/signup/admin', data={
        'full_name': 'Prof. Rajesh Khanna',
        'college_id': 1,
        'admin_id': 'ADM-ABC-02',
        'phone_number': '9876500000',
        'email': 'rajesh.admin@abccollege.edu',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'PENDING APPROVAL' in res.data

    adm_user = User.query.filter_by(identifier='ADM-ABC-02').first()
    assert adm_user is not None
    assert adm_user.registration_status == 'pending_approval'
    assert adm_user.is_active is False

    # 2. Attempt login before approval -> blocked
    login_attempt = client.post('/auth/login', data={'identifier': 'ADM-ABC-02', 'password': 'Password@123'})
    assert b'pending approval by the Super Admin' in login_attempt.data

    # 3. Super Admin logs in and approves the new College Admin
    client.post('/auth/login', data={'identifier': 'SUPERADMIN', 'password': 'Password@123'})
    approve_res = client.post(f'/super-admin/admins/{adm_user.id}/approve', follow_redirects=True)
    assert approve_res.status_code == 200
    assert b'approved and activated' in approve_res.data

    # 4. College Admin can now log in
    client.get('/auth/logout')
    login_ok = client.post('/auth/login', data={'identifier': 'ADM-ABC-02', 'password': 'Password@123'}, follow_redirects=False)
    assert login_ok.status_code == 302
    assert '/college-admin/dashboard' in login_ok.headers['Location']


# Requirement 4: Super Admin cannot be created through public registration
def test_4_super_admin_cannot_be_created_publicly(client):
    # Public registration endpoints only exist for student, faculty, and admin (college admin)
    res_bad = client.post('/auth/signup/super_admin', data={'email': 'hacker@evil.com'}, follow_redirects=True)
    # Either 404 or redirected to login
    assert res_bad.status_code in (404, 200)
    assert User.query.filter_by(email='hacker@evil.com').first() is None


# Requirement 5: Duplicate email registration is rejected
def test_5_duplicate_email_rejected(client):
    res = client.post('/auth/signup/student', data={
        'full_name': 'Another Student',
        'college_id': 1,
        'roll_number': '2025DAMBT11999',
        'phone_number': '9876543210',
        'email': 'sai.kumar@abccollege.edu',  # Already belongs to existing student
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    })
    assert b'email address is already registered' in res.data


# Requirement 6: Duplicate roll number registration is rejected
def test_6_duplicate_roll_number_rejected(client):
    res = client.post('/auth/signup/student', data={
        'full_name': 'Duplicate Roll',
        'college_id': 1,
        'roll_number': '2025DAMBT11765',  # Already exists
        'phone_number': '9876543210',
        'email': 'unique.email@example.com',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    })
    assert b'already registered' in res.data


# Requirement 7: Weak passwords are rejected
def test_7_weak_password_rejected(client):
    res = client.post('/auth/signup/student', data={
        'full_name': 'Weak Password User',
        'college_id': 1,
        'roll_number': '2025DAMBT11998',
        'phone_number': '9876543210',
        'email': 'weak.pwd@example.com',
        'password': 'short',
        'confirm_password': 'short'
    })
    assert b'at least 8 characters' in res.data


# Requirement 8: Incorrect password confirmation is rejected
def test_8_password_mismatch_rejected(client):
    res = client.post('/auth/signup/student', data={
        'full_name': 'Mismatch User',
        'college_id': 1,
        'roll_number': '2025DAMBT11997',
        'phone_number': '9876543210',
        'email': 'mismatch@example.com',
        'password': 'Password@123',
        'confirm_password': 'DifferentPassword@123'
    })
    assert b'Confirm Password does not match' in res.data


# Requirement 9: Existing students can log in using email and password
def test_9_existing_student_login_with_email(client):
    res = client.post('/auth/login', data={'identifier': 'sai.kumar@abccollege.edu', 'password': 'Password@123'}, follow_redirects=False)
    assert res.status_code == 302
    assert '/student/dashboard' in res.headers['Location']


# Requirement 10: Existing faculty can log in
def test_10_existing_faculty_login(client):
    res = client.post('/auth/login', data={'identifier': 'anita.sharma@abccollege.edu', 'password': 'Password@123'}, follow_redirects=False)
    assert res.status_code == 302
    assert '/faculty/dashboard' in res.headers['Location']


# Requirement 11: Existing administrators can log in
def test_11_existing_administrators_login(client):
    # College Admin
    res_adm = client.post('/auth/login', data={'identifier': 'admin@abccollege.edu', 'password': 'Password@123'}, follow_redirects=False)
    assert res_adm.status_code == 302
    assert '/college-admin/dashboard' in res_adm.headers['Location']

    # Super Admin
    client.get('/auth/logout')
    res_sup = client.post('/auth/login', data={'identifier': 'superadmin@portal.edu', 'password': 'Password@123'}, follow_redirects=False)
    assert res_sup.status_code == 302
    assert '/super-admin/dashboard' in res_sup.headers['Location']


# Requirement 12: Users are redirected to the correct dashboards
def test_12_role_redirection(client):
    # Test that each role arrives at their authorized home
    client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Password@123'})
    dashboard_res = client.get('/student/dashboard')
    assert dashboard_res.status_code == 200
    assert b'Student Portal' in dashboard_res.data


# Requirement 13: Pending accounts cannot access protected features
def test_13_pending_accounts_blocked(client):
    # Create unapproved faculty
    client.post('/auth/signup/faculty', data={
        'full_name': 'Pending Prof', 'college_id': 1, 'faculty_id': 'FAC-PENDING-01',
        'phone_number': '9876543210', 'email': 'pending.prof@abc.edu',
        'department_name': 'CSE', 'password': 'Password@123', 'confirm_password': 'Password@123'
    })
    # Login blocked
    res = client.post('/auth/login', data={'identifier': 'FAC-PENDING-01', 'password': 'Password@123'})
    assert b'pending approval' in res.data

    # Direct access to dashboard blocked
    dash_res = client.get('/faculty/dashboard')
    assert dash_res.status_code == 302
    assert '/auth/login' in dash_res.headers['Location']


# Requirement 14: Forgot Password works correctly
def test_14_forgot_password_works(client):
    # Request reset
    req_res = client.post('/auth/forgot-password', data={'identifier_or_email': 'sai.kumar@abccollege.edu'})
    assert req_res.status_code == 200
    assert b'password recovery instructions' in req_res.data

    user = User.query.filter_by(email='sai.kumar@abccollege.edu').first()
    assert user.reset_token is not None

    # Fulfill reset
    token = user.reset_token
    reset_res = client.post(f'/auth/reset-password/{token}', data={
        'password': 'BrandNewPassword@2026',
        'confirm_password': 'BrandNewPassword@2026'
    }, follow_redirects=True)
    assert reset_res.status_code == 200
    assert b'reset successfully' in reset_res.data

    # Log in with new password
    new_login = client.post('/auth/login', data={'identifier': 'sai.kumar@abccollege.edu', 'password': 'BrandNewPassword@2026'}, follow_redirects=False)
    assert new_login.status_code == 302
    assert '/student/dashboard' in new_login.headers['Location']


# Requirement 15: Existing accounts remain functional
def test_15_existing_accounts_remain_functional(client):
    # Student login with roll number
    res1 = client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Password@123'}, follow_redirects=False)
    assert res1.status_code == 302

    # Faculty login with faculty ID
    client.get('/auth/logout')
    res2 = client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Password@123'}, follow_redirects=False)
    assert res2.status_code == 302

    # College Admin login with Admin ID
    client.get('/auth/logout')
    res3 = client.post('/auth/login', data={'identifier': 'ADM-ABC-01', 'password': 'Password@123'}, follow_redirects=False)
    assert res3.status_code == 302


# Requirement 16: Students cannot access faculty or admin dashboards
def test_16_students_cannot_access_faculty_or_admin_dashboards(client):
    client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Password@123'})

    # Try faculty dashboard -> 403 Forbidden
    res_fac = client.get('/faculty/dashboard')
    assert res_fac.status_code == 403

    # Try college admin dashboard -> 403 Forbidden
    res_adm = client.get('/college-admin/dashboard')
    assert res_adm.status_code == 403

    # Try super admin dashboard -> 403 Forbidden
    res_sup = client.get('/super-admin/dashboard')
    assert res_sup.status_code == 403


# Requirement 17: Faculty cannot access admin dashboards
def test_17_faculty_cannot_access_admin_dashboards(client):
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Password@123'})

    res_adm = client.get('/college-admin/dashboard')
    assert res_adm.status_code == 403

    res_sup = client.get('/super-admin/dashboard')
    assert res_sup.status_code == 403


# Requirement 18: College-level data isolation continues working
def test_18_college_level_isolation(client):
    # College 1 Admin logs in
    client.post('/auth/login', data={'identifier': 'ADM-ABC-01', 'password': 'Password@123'})
    overview = client.get('/college-admin/dashboard')
    assert overview.status_code == 200
    assert b'ABC Engineering College' in overview.data

    # Check that College 2 students are NOT shown
    assert b'Apex Institute' not in overview.data


# Requirement 19: Tab elements and active states for Student, Faculty, and Admin
def test_19_tab_elements_and_state(client):
    # Student Login tab active by default
    res_st_login = client.get('/auth/login?role=student&tab=login')
    assert res_st_login.status_code == 200
    assert b'tab-btn-student-login' in res_st_login.data
    assert b'tab-btn-student-signup' in res_st_login.data
    assert b'Student Login' in res_st_login.data
    assert b'Student Sign Up' in res_st_login.data

    # Student Sign Up tab active when tab=signup
    res_st_signup = client.get('/auth/login?role=student&tab=signup')
    assert res_st_signup.status_code == 200
    assert b'tab-btn-student-signup' in res_st_signup.data

    # Faculty tabs
    res_fac = client.get('/auth/login?role=faculty&tab=login')
    assert res_fac.status_code == 200
    assert b'tab-btn-faculty-login' in res_fac.data
    assert b'tab-btn-faculty-signup' in res_fac.data
    assert b'Faculty Login' in res_fac.data
    assert b'Faculty Sign Up' in res_fac.data

    # Admin tabs
    res_adm = client.get('/auth/login?role=admin&tab=login')
    assert res_adm.status_code == 200
    assert b'tab-btn-admin-login' in res_adm.data
    assert b'tab-btn-admin-signup' in res_adm.data
    assert b'Admin Login' in res_adm.data
    assert b'Admin Sign Up' in res_adm.data


# Requirement 20: Complete removal of public demo credentials and references
def test_20_public_demo_credentials_completely_removed(client):
    urls = [
        '/auth/login',
        '/auth/login?role=student',
        '/auth/login?role=student&tab=signup',
        '/auth/login?role=faculty',
        '/auth/login?role=faculty&tab=signup',
        '/auth/login?role=admin',
        '/auth/login?role=admin&tab=signup',
        '/auth/select-role'
    ]
    for url in urls:
        res = client.get(url)
        assert res.status_code == 200
        # Assert heading and sample passwords are completely absent from HTML
        assert b'Quick Evaluation Credentials Reference' not in res.data
        assert b'Password@123' not in res.data
        assert b'SUPERADMIN' not in res.data or b'e.g. SUPERADMIN' not in res.data


# Requirement 21: Enhanced password complexity validation
def test_21_password_complexity_validation(client):
    base_data = {
        'full_name': 'Validation Candidate',
        'college_id': 1,
        'roll_number': '2025DAMBT88888',
        'phone_number': '9876543210',
        'email': 'complex.pwd@example.com'
    }

    # 1. Missing uppercase
    d1 = dict(base_data, password='password@123', confirm_password='password@123')
    r1 = client.post('/auth/signup/student', data=d1)
    assert b'uppercase letter' in r1.data

    # 2. Missing lowercase
    d2 = dict(base_data, password='PASSWORD@123', confirm_password='PASSWORD@123')
    r2 = client.post('/auth/signup/student', data=d2)
    assert b'lowercase letter' in r2.data

    # 3. Missing digit
    d3 = dict(base_data, password='Password@Special', confirm_password='Password@Special')
    r3 = client.post('/auth/signup/student', data=d3)
    assert b'numerical digit' in r3.data

    # 4. Missing special character
    d4 = dict(base_data, password='Password1234', confirm_password='Password1234')
    r4 = client.post('/auth/signup/student', data=d4)
    assert b'special character' in r4.data

import pytest
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import College, User, StudentProfile, Course, Branch


@pytest.fixture
def auth_app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # College 1
        col1 = College(
            name='ABC Engineering College', code='ABCENG',
            address='Tech City, Hyderabad', email='info@abccollege.edu',
            contact_number='+91 40 1234', email_domain='abccollege.edu',
            status='active'
        )
        db.session.add(col1)
        db.session.flush()

        course1 = Course(college_id=col1.id, code='BTECH', name='Bachelor of Technology')
        branch1 = Branch(college_id=col1.id, course=course1, code='CSE', name='Computer Science')
        db.session.add_all([course1, branch1])
        db.session.flush()

        # Super Admin
        sup = User(identifier='SUPERADMIN', email='super@uni.edu', role='super_admin')
        sup.set_password('Password@123')

        # College Admin
        adm = User(identifier='ADM-ABC-01', email='admin@abc.edu', role='college_admin', college_id=col1.id)
        adm.set_password('Password@123')

        # Faculty
        fac = User(identifier='FAC-ABC-01', email='fac@abc.edu', role='faculty', college_id=col1.id)
        fac.set_password('Password@123')

        # Existing Student (Active)
        st = User(identifier='2025DAMBT11765', email='sai@abc.edu', role='student', college_id=col1.id, registration_status='active', is_active=True)
        st.set_password('Password@123')
        st_p = StudentProfile(
            user=st, registration_number='2025DAMBT11765', first_name='Sai', last_name='Kumar',
            college_id=col1.id, course_id=course1.id, branch_id=branch1.id, semester=3
        )

        db.session.add_all([sup, adm, fac, st, st_p])
        db.session.commit()

        yield app

        db.drop_all()


@pytest.fixture
def client(auth_app):
    return auth_app.test_client()


def test_existing_student_login_with_plain_roll(client):
    """Existing student can log in using their roll number."""
    res = client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Password@123'}, follow_redirects=False)
    assert res.status_code == 302
    assert '/student/dashboard' in res.headers['Location']


def test_student_login_with_college_domain_email(client):
    """Student can log in using college-configured email identifier (roll@abccollege.edu)."""
    res = client.post('/auth/login', data={'identifier': '2025DAMBT11765@abccollege.edu', 'password': 'Password@123'}, follow_redirects=False)
    assert res.status_code == 302
    assert '/student/dashboard' in res.headers['Location']


def test_student_login_with_generic_college_com(client):
    """Student can log in using common generic institutional alias (roll@college.com)."""
    res = client.post('/auth/login', data={'identifier': '2025DAMBT11765@college.com', 'password': 'Password@123'}, follow_redirects=False)
    assert res.status_code == 302
    assert '/student/dashboard' in res.headers['Location']


def test_all_existing_roles_login(client):
    """Faculty, College Admin, and Super Admin can log in cleanly."""
    # Faculty
    res_fac = client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Password@123'}, follow_redirects=False)
    assert res_fac.status_code == 302
    assert '/faculty/dashboard' in res_fac.headers['Location']

    # College Admin
    client.get('/auth/logout')
    res_adm = client.post('/auth/login', data={'identifier': 'ADM-ABC-01', 'password': 'Password@123'}, follow_redirects=False)
    assert res_adm.status_code == 302
    assert '/college-admin/dashboard' in res_adm.headers['Location']

    # Super Admin
    client.get('/auth/logout')
    res_sup = client.post('/auth/login', data={'identifier': 'SUPERADMIN', 'password': 'Password@123'}, follow_redirects=False)
    assert res_sup.status_code == 302
    assert '/super-admin/dashboard' in res_sup.headers['Location']


def test_invalid_credentials_rejected(client):
    """Incorrect passwords are rejected with clear warning."""
    res = client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'WrongPassword'})
    assert res.status_code == 200
    assert b'Invalid credentials' in res.data


def test_student_signup_validation_failures(client):
    """Validates form checks: invalid mobile, invalid email, short password, confirm password mismatch."""
    # Invalid mobile (letters)
    res1 = client.post('/auth/signup', data={
        'full_name': 'Test Candidate', 'mobile_number': 'not-a-number',
        'email': 'valid@example.com', 'roll_number': 'TEST9901',
        'college_id': 1, 'password': 'Password@123', 'confirm_password': 'Password@123'
    })
    assert b'valid mobile phone number' in res1.data

    # Invalid email
    res2 = client.post('/auth/signup', data={
        'full_name': 'Test Candidate', 'mobile_number': '9876543210',
        'email': 'invalid-email-format', 'roll_number': 'TEST9902',
        'college_id': 1, 'password': 'Password@123', 'confirm_password': 'Password@123'
    })
    assert b'valid institutional or personal email' in res2.data

    # Password too short (< 8 chars)
    res3 = client.post('/auth/signup', data={
        'full_name': 'Test Candidate', 'mobile_number': '9876543210',
        'email': 'valid@example.com', 'roll_number': 'TEST9903',
        'college_id': 1, 'password': 'short', 'confirm_password': 'short'
    })
    assert b'at least 8 characters' in res3.data

    # Confirm password mismatch
    res4 = client.post('/auth/signup', data={
        'full_name': 'Test Candidate', 'mobile_number': '9876543210',
        'email': 'valid@example.com', 'roll_number': 'TEST9904',
        'college_id': 1, 'password': 'Password@123', 'confirm_password': 'DifferentPassword'
    })
    assert b'Confirm Password does not match' in res4.data


def test_student_signup_duplicate_rejection(client):
    """Rejects duplicate email and duplicate roll number."""
    # Duplicate roll number (2025DAMBT11765 already exists)
    res1 = client.post('/auth/signup', data={
        'full_name': 'Another Student', 'mobile_number': '9876543210',
        'email': 'different@example.com', 'roll_number': '2025DAMBT11765',
        'college_id': 1, 'password': 'Password@123', 'confirm_password': 'Password@123'
    })
    assert b'already registered' in res1.data

    # Duplicate email (sai@abc.edu already exists)
    res2 = client.post('/auth/signup', data={
        'full_name': 'Another Student', 'mobile_number': '9876543210',
        'email': 'sai@abc.edu', 'roll_number': 'NEWROLL999',
        'college_id': 1, 'password': 'Password@123', 'confirm_password': 'Password@123'
    })
    assert b'email address is already registered' in res2.data


def test_student_signup_creates_pending_verification(client):
    """Valid student registration creates account with pending_verification status and blocks login until approved."""
    res = client.post('/auth/signup', data={
        'full_name': 'Kavya Madhavan', 'mobile_number': '9876512345',
        'email': 'kavya@gmail.com', 'roll_number': '2025DAMBT11799',
        'college_id': 1, 'password': 'Password@123', 'confirm_password': 'Password@123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'PENDING VERIFICATION' in res.data
    assert b'2025DAMBT11799@abccollege.edu' in res.data

    # Attempting to log in while pending verification must be blocked
    login_attempt = client.post('/auth/login', data={'identifier': '2025DAMBT11799', 'password': 'Password@123'})
    assert b'pending verification' in login_attempt.data

    # Verify student is in DB with pending_verification status
    user = User.query.filter_by(identifier='2025DAMBT11799').first()
    assert user is not None
    assert user.registration_status == 'pending_verification'
    assert user.is_active is False


def test_college_admin_approval_workflow(client):
    """College admin can approve pending student registration, enabling them to log in."""
    # 1. Register student
    client.post('/auth/signup', data={
        'full_name': 'Vikram Mehra', 'mobile_number': '9876599999',
        'email': 'vikram.m@gmail.com', 'roll_number': '2025DAMBT11800',
        'college_id': 1, 'password': 'Password@123', 'confirm_password': 'Password@123'
    })
    st_p = StudentProfile.query.filter_by(registration_number='2025DAMBT11800').first()
    assert st_p is not None

    # 2. Login College Admin
    client.post('/auth/login', data={'identifier': 'ADM-ABC-01', 'password': 'Password@123'})
    students_page = client.get('/college-admin/students')
    assert b'2025DAMBT11800' in students_page.data
    assert b'Pending Verification' in students_page.data

    # 3. Approve student
    approve_res = client.post(f'/college-admin/students/{st_p.id}/approve', follow_redirects=True)
    assert approve_res.status_code == 200
    assert b'approved and activated' in approve_res.data

    # 4. Student can now log in successfully!
    client.get('/auth/logout')
    login_ok = client.post('/auth/login', data={'identifier': '2025DAMBT11800', 'password': 'Password@123'}, follow_redirects=False)
    assert login_ok.status_code == 302
    assert '/student/dashboard' in login_ok.headers['Location']


def test_forgot_password_and_reset_workflow(client):
    """Forgot password generates time-limited reset token and updates password upon verification."""
    # 1. Request reset
    req_res = client.post('/auth/forgot-password', data={'identifier_or_email': '2025DAMBT11765'})
    assert req_res.status_code == 200
    assert b'password recovery instructions' in req_res.data

    user = User.query.filter_by(identifier='2025DAMBT11765').first()
    assert user.reset_token is not None
    assert user.reset_token_expiry > datetime.utcnow()

    token = user.reset_token

    # 2. Access reset page
    page_res = client.get(f'/auth/reset-password/{token}')
    assert page_res.status_code == 200
    assert b'Set New Account Password' in page_res.data

    # 3. Submit new password
    reset_res = client.post(f'/auth/reset-password/{token}', data={
        'password': 'NewPassword@2026',
        'confirm_password': 'NewPassword@2026'
    }, follow_redirects=True)
    assert reset_res.status_code == 200
    assert b'Your password has been reset successfully' in reset_res.data

    # 4. Old password fails, new password succeeds
    fail_old = client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'Password@123'})
    assert b'Invalid credentials' in fail_old.data

    ok_new = client.post('/auth/login', data={'identifier': '2025DAMBT11765', 'password': 'NewPassword@2026'}, follow_redirects=False)
    assert ok_new.status_code == 302
    assert '/student/dashboard' in ok_new.headers['Location']

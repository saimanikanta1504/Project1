import re
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import (
    User, StudentProfile, FacultyProfile, CollegeAdminProfile,
    AdminProfile, PasswordResetToken, AccountVerification,
    College, Course, Branch
)
from app.extensions import db
from app.demo_service import (
    authenticate_demo_student, authenticate_demo_faculty,
    authenticate_demo_college_admin, get_or_create_demo_college
)

auth_bp = Blueprint('auth', __name__)


def redirect_by_role(user):
    """Direct each user exclusively to their authorized role dashboard."""
    if user.is_super_admin:
        return redirect(url_for('super_admin.dashboard'))
    elif user.is_college_admin:
        return redirect(url_for('college_admin.dashboard'))
    elif user.is_faculty:
        return redirect(url_for('faculty.dashboard'))
    elif user.is_student:
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))


def resolve_user_by_identifier(identifier):
    """
    Resolves user account by:
    1. Exact User.identifier match (e.g. '2025DAMBT11765', 'FAC-ABC-01', 'ADM-ABC-01', 'SUPERADMIN')
    2. Exact User.email match (e.g. 'sai.kumar@abccollege.edu')
    3. College-configured email-style identifier (e.g. '2025DAMBT11765@abccollege.edu' or '2025DAMBT11765@college.com')
    """
    if not identifier:
        return None
    identifier = identifier.strip()

    # 1. Direct match by identifier or registered email
    user = User.query.filter(
        (User.identifier == identifier) | (User.email == identifier.lower())
    ).first()
    if user:
        return user

    # 2. Check college-configured email identifier pattern (e.g. roll@college_domain)
    if '@' in identifier:
        roll_part, domain_part = identifier.split('@', 1)
        roll_part = roll_part.strip()
        domain_part = domain_part.strip().lower()

        candidate = User.query.filter_by(identifier=roll_part).first()
        if candidate and candidate.college:
            college_domain = (candidate.college.email_domain or '').lower()
            if domain_part == college_domain or domain_part in ('college.com', 'college.edu'):
                return candidate

    return None


def validate_password_strength(password):
    if not password or len(password) < 8:
        return False, 'Password must be at least 8 characters long.'
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter (A-Z).'
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter (a-z).'
    if not re.search(r'\d', password):
        return False, 'Password must contain at least one numerical digit (0-9).'
    if not re.search(r'[@$!%*?&^#_~\-\.,:;+=()\[\]{}|\\/]', password):
        return False, 'Password must contain at least one special character (e.g. @$!%*?&).'
    return True, None


def validate_phone_number(phone):
    if not phone or not re.match(r'^\+?[0-9]{10,15}$', phone.strip()):
        return False, 'Please enter a valid mobile phone number (10 to 15 digits).'
    return True, None


def validate_email_format(email):
    if not email or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email.strip()):
        return False, 'Please enter a valid institutional or personal email address.'
    return True, None


@auth_bp.route('/select-role')
def select_role():
    """Initial Screen: Display three user categories without email or password inputs."""
    if current_user.is_authenticated:
        return redirect_by_role(current_user)
    colleges = College.query.filter_by(status='active').order_by(College.name).all()
    auth_mode = request.args.get('auth_mode') or request.args.get('mode', 'normal')
    return render_template('login.html', selected_role=None, active_tab='login', colleges=colleges, auth_mode=auth_mode)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Multi-Role Authentication Gateway:
    - Supports Normal Login Mode and Demo Login Mode.
    - Screen 1: If no role selected, shows category selector (Student / Faculty / Admin).
    - Screen 2: If role selected, shows Sign Up / Login for that category.
    - Authenticates real database credentials with Werkzeug password hashing.
    """
    if current_user.is_authenticated:
        return redirect_by_role(current_user)

    colleges = College.query.filter_by(status='active').order_by(College.name).all()
    selected_role = request.args.get('role') or request.args.get('category')
    active_tab = request.args.get('tab', 'login')
    auth_mode = request.args.get('auth_mode') or request.args.get('mode', 'normal')

    if request.method == 'POST':
        identifier = (request.form.get('identifier') or request.form.get('email', '')).strip()
        password = request.form.get('password', '').strip()
        remember = bool(request.form.get('remember'))
        submitted_role = request.form.get('role') or selected_role
        submitted_mode = request.form.get('auth_mode', auth_mode)

        if not identifier or not password:
            flash('Please enter both your Email / Identifier and Password.', 'warning')
            return render_template(
                'login.html',
                selected_role=submitted_role,
                active_tab='login',
                identifier=identifier,
                colleges=colleges,
                auth_mode=submitted_mode
            )

        user = resolve_user_by_identifier(identifier)

        if not user or not user.check_password(password):
            flash('Invalid credentials. Please verify your Email / Identifier and Password.', 'danger')
            return render_template(
                'login.html',
                selected_role=submitted_role,
                active_tab='login',
                identifier=identifier,
                colleges=colleges,
                auth_mode=submitted_mode
            )

        # Account Status & Verification Checks
        status = getattr(user, 'registration_status', 'active')
        if status in ('pending_approval', 'pending_verification') or not user.is_active:
            if user.is_student:
                flash('Your student account registration is currently pending verification and approval by your college administrator.', 'warning')
            elif user.is_faculty:
                flash('Your faculty account registration is currently pending approval by your college administrator.', 'warning')
            elif user.is_college_admin:
                flash('Your college administrator account registration is currently pending approval by the Super Admin.', 'warning')
            else:
                flash('Your account registration is currently pending administrative verification.', 'warning')
            return render_template(
                'login.html',
                selected_role=submitted_role,
                active_tab='login',
                identifier=identifier,
                colleges=colleges
            )

        if status == 'rejected':
            flash('Your account registration has been rejected by the administration. Please contact your institution office.', 'danger')
            return render_template(
                'login.html',
                selected_role=submitted_role,
                active_tab='login',
                identifier=identifier,
                colleges=colleges
            )

        if not user.is_active or status == 'deactivated':
            flash('Your account has been deactivated. Please contact your institution administrator.', 'danger')
            return render_template(
                'login.html',
                selected_role=submitted_role,
                active_tab='login',
                identifier=identifier,
                colleges=colleges
            )

        if user.college_id:
            college = db.session.get(College, user.college_id)
            if college and college.status != 'active':
                flash(f'Access restricted: {college.name} is currently {college.status}. Contact administrator.', 'danger')
                return render_template(
                    'login.html',
                    selected_role=submitted_role,
                    active_tab='login',
                    identifier=identifier,
                    colleges=colleges
                )

        # Successful Login
        user.record_login()
        login_user(user, remember=remember)

        if user.is_student and user.student_profile:
            flash(f'College Identified: {user.college.name}. Welcome {user.student_profile.full_name}!', 'success')
        elif user.is_faculty and user.faculty_profile:
            flash(f'College Identified: {user.college.name}. Welcome {user.faculty_profile.full_name}!', 'success')
        elif user.college:
            flash(f'College Identified: {user.college.name}. Welcome {user.identifier}!', 'success')
        else:
            flash(f'Super Administrator Session Verified: {user.identifier}', 'success')

        return redirect_by_role(user)

    return render_template(
        'login.html',
        selected_role=selected_role,
        active_tab=active_tab,
        colleges=colleges
    )


@auth_bp.route('/login/<category>', methods=['GET', 'POST'])
def login_category(category):
    """Direct route for specific category login."""
    if current_user.is_authenticated:
        return redirect_by_role(current_user)
    if request.method == 'POST':
        return login()
    return redirect(url_for('auth.login', role=category, tab='login'))


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Backwards-compatible student signup endpoint."""
    if request.method == 'POST':
        return signup_student()
    return redirect(url_for('auth.login', role='student', tab='signup'))


@auth_bp.route('/signup/student', methods=['GET', 'POST'])
def signup_student():
    """
    Student Self-Registration:
    Requires Name, College, Roll Number, Phone, Email, Password.
    Sets status to pending_approval / pending_verification.
    """
    if current_user.is_authenticated:
        return redirect_by_role(current_user)

    colleges = College.query.filter_by(status='active').order_by(College.name).all()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        college_id = request.form.get('college_id', type=int)
        phone_number = (request.form.get('phone_number') or request.form.get('mobile_number', '')).strip()
        email = request.form.get('email', '').strip().lower()
        roll_number = (request.form.get('roll_number') or request.form.get('registration_number', '')).strip().upper()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 1. Required Fields
        if not all([full_name, college_id, phone_number, email, roll_number, password, confirm_password]):
            flash('All required fields must be completed.', 'danger')
            return render_template('login.html', selected_role='student', active_tab='signup', colleges=colleges, form_data=request.form)

        if len(full_name) < 2:
            flash('Full Name is required and must contain at least 2 characters.', 'danger')
            return render_template('login.html', selected_role='student', active_tab='signup', colleges=colleges, form_data=request.form)

        # 2. Phone Validation
        valid_phone, phone_err = validate_phone_number(phone_number)
        if not valid_phone:
            flash(phone_err, 'danger')
            return render_template('login.html', selected_role='student', active_tab='signup', colleges=colleges, form_data=request.form)

        # 3. Email Validation
        valid_email, email_err = validate_email_format(email)
        if not valid_email:
            flash(email_err, 'danger')
            return render_template('login.html', selected_role='student', active_tab='signup', colleges=colleges, form_data=request.form)

        # 4. Roll Number Validation
        if len(roll_number) < 3:
            flash('Roll Number / Registration Number is required.', 'danger')
            return render_template('login.html', selected_role='student', active_tab='signup', colleges=colleges, form_data=request.form)

        # 5. Password Validation
        valid_pwd, pwd_err = validate_password_strength(password)
        if not valid_pwd:
            flash(pwd_err, 'danger')
            return render_template('login.html', selected_role='student', active_tab='signup', colleges=colleges, form_data=request.form)

        if password != confirm_password:
            flash('Confirm Password does not match Password. Please re-enter carefully.', 'danger')
            return render_template('login.html', selected_role='student', active_tab='signup', colleges=colleges, form_data=request.form)

        # 6. College Validation
        college = db.session.get(College, college_id)
        if not college or college.status != 'active':
            flash('Please select an active, registered college institution.', 'danger')
            return render_template('login.html', selected_role='student', active_tab='signup', colleges=colleges, form_data=request.form)

        # 7. Duplicate Checks
        if User.query.filter_by(email=email).first():
            flash('This email address is already registered in the examination platform. Please sign in or use another email.', 'danger')
            return render_template('login.html', selected_role='student', active_tab='signup', colleges=colleges, form_data=request.form)

        if User.query.filter_by(identifier=roll_number).first():
            flash('This Roll Number / Registration Number is already registered. Please sign in.', 'danger')
            return render_template('login.html', selected_role='student', active_tab='signup', colleges=colleges, form_data=request.form)

        # Name split
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else 'Student'

        # Resolve Academic Structure
        existing_profile = StudentProfile.query.filter_by(
            college_id=college.id, registration_number=roll_number
        ).first()

        course = college.courses[0] if college.courses else None
        branch = course.branches[0] if (course and course.branches) else None
        if not course or not branch:
            course = Course(college_id=college.id, code='BTECH', name='Bachelor of Technology')
            branch = Branch(college_id=college.id, course=course, code='GEN', name='General Engineering')
            db.session.add_all([course, branch])
            db.session.flush()

        # Create Student User (status: pending_verification)
        new_user = User(
            identifier=roll_number,
            email=email,
            mobile_number=phone_number,
            phone_number=phone_number,
            role='student',
            college_id=college.id,
            registration_status='pending_verification',
            is_active=False
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        if existing_profile:
            existing_profile.user_id = new_user.id
            existing_profile.contact_number = phone_number
            existing_profile.registration_status = 'pending_verification'
        else:
            new_profile = StudentProfile(
                user_id=new_user.id,
                registration_number=roll_number,
                first_name=first_name,
                last_name=last_name,
                college_id=college.id,
                course_id=course.id,
                branch_id=branch.id,
                semester=1,
                academic_year='2026-2027',
                contact_number=phone_number,
                registration_status='pending_verification'
            )
            db.session.add(new_profile)

        # Record Verification Request
        verification = AccountVerification(
            user_id=new_user.id,
            requested_role='student',
            college_id=college.id,
            status='pending_verification'
        )
        db.session.add(verification)
        db.session.commit()

        login_domain_id = college.get_login_identifier(roll_number) if hasattr(college, 'get_login_identifier') else f"{roll_number}@{college.email_domain}"
        flash(
            f'Registration submitted successfully! Your institutional login identifier will be: {login_domain_id}. '
            'Your account is currently PENDING VERIFICATION by your college administrator. You will be able to log in once approved.',
            'success'
        )
        return redirect(url_for('auth.login', role='student', tab='login', identifier=roll_number))

    return redirect(url_for('auth.login', role='student', tab='signup'))


@auth_bp.route('/signup/faculty', methods=['GET', 'POST'])
def signup_faculty():
    """
    Faculty Registration:
    Requires Full Name, College, Faculty ID, Phone, Email, Password.
    Sets status to pending_approval (requires College Admin approval).
    """
    if current_user.is_authenticated:
        return redirect_by_role(current_user)

    colleges = College.query.filter_by(status='active').order_by(College.name).all()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        college_id = request.form.get('college_id', type=int)
        faculty_id = (request.form.get('faculty_id') or request.form.get('employee_id', '')).strip().upper()
        phone_number = (request.form.get('phone_number') or request.form.get('contact_number', '')).strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        department = request.form.get('department_name', 'General Engineering').strip()

        # 1. Required Fields
        if not all([full_name, college_id, faculty_id, phone_number, email, password, confirm_password]):
            flash('All required fields must be completed for faculty registration.', 'danger')
            return render_template('login.html', selected_role='faculty', active_tab='signup', colleges=colleges, form_data=request.form)

        if len(full_name) < 2:
            flash('Full Name must contain at least 2 characters.', 'danger')
            return render_template('login.html', selected_role='faculty', active_tab='signup', colleges=colleges, form_data=request.form)

        # 2. Phone Validation
        valid_phone, phone_err = validate_phone_number(phone_number)
        if not valid_phone:
            flash(phone_err, 'danger')
            return render_template('login.html', selected_role='faculty', active_tab='signup', colleges=colleges, form_data=request.form)

        # 3. Email Validation
        valid_email, email_err = validate_email_format(email)
        if not valid_email:
            flash(email_err, 'danger')
            return render_template('login.html', selected_role='faculty', active_tab='signup', colleges=colleges, form_data=request.form)

        # 4. Faculty ID Validation
        if len(faculty_id) < 3:
            flash('Faculty ID / Employee ID is required.', 'danger')
            return render_template('login.html', selected_role='faculty', active_tab='signup', colleges=colleges, form_data=request.form)

        # 5. Password Validation
        valid_pwd, pwd_err = validate_password_strength(password)
        if not valid_pwd:
            flash(pwd_err, 'danger')
            return render_template('login.html', selected_role='faculty', active_tab='signup', colleges=colleges, form_data=request.form)

        if password != confirm_password:
            flash('Confirm Password does not match Password.', 'danger')
            return render_template('login.html', selected_role='faculty', active_tab='signup', colleges=colleges, form_data=request.form)

        # 6. College Validation
        college = db.session.get(College, college_id)
        if not college or college.status != 'active':
            flash('Please select an active, registered college institution.', 'danger')
            return render_template('login.html', selected_role='faculty', active_tab='signup', colleges=colleges, form_data=request.form)

        # 7. Duplicate Checks
        if User.query.filter_by(email=email).first():
            flash('This email address is already registered in the platform.', 'danger')
            return render_template('login.html', selected_role='faculty', active_tab='signup', colleges=colleges, form_data=request.form)

        if User.query.filter_by(identifier=faculty_id).first():
            flash('This Faculty ID / Employee ID is already registered.', 'danger')
            return render_template('login.html', selected_role='faculty', active_tab='signup', colleges=colleges, form_data=request.form)

        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else 'Faculty'

        new_user = User(
            identifier=faculty_id,
            email=email,
            mobile_number=phone_number,
            phone_number=phone_number,
            role='faculty',
            college_id=college.id,
            registration_status='pending_approval',
            is_active=False
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        new_profile = FacultyProfile(
            user_id=new_user.id,
            faculty_id_code=faculty_id,
            first_name=first_name,
            last_name=last_name,
            college_id=college.id,
            designation='Assistant Professor',
            department_name=department,
            contact_number=phone_number,
            registration_status='pending_approval'
        )
        db.session.add(new_profile)

        verification = AccountVerification(
            user_id=new_user.id,
            requested_role='faculty',
            college_id=college.id,
            status='pending_approval'
        )
        db.session.add(verification)
        db.session.commit()

        flash(
            f'Faculty registration for {full_name} ({faculty_id}) submitted successfully! '
            'Your account is currently PENDING APPROVAL by your College Administrator. You will be able to log in once approved.',
            'success'
        )
        return redirect(url_for('auth.login', role='faculty', tab='login', identifier=faculty_id))

    return redirect(url_for('auth.login', role='faculty', tab='signup'))


@auth_bp.route('/signup/admin', methods=['GET', 'POST'])
def signup_admin():
    """
    College Administrator Registration:
    Requires Full Name, College, Admin ID, Phone, Email, Password.
    Sets status to pending_approval (requires Super Admin authorization).
    NOTE: Super Admin public registration is strictly prohibited.
    """
    if current_user.is_authenticated:
        return redirect_by_role(current_user)

    colleges = College.query.filter_by(status='active').order_by(College.name).all()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        college_id = request.form.get('college_id', type=int)
        admin_id = request.form.get('admin_id', '').strip().upper()
        phone_number = (request.form.get('phone_number') or request.form.get('contact_number', '')).strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 1. Required Fields
        if not all([full_name, college_id, admin_id, phone_number, email, password, confirm_password]):
            flash('All required fields must be completed for College Administrator registration.', 'danger')
            return render_template('login.html', selected_role='admin', active_tab='signup', colleges=colleges, form_data=request.form)

        # 2. Phone Validation
        valid_phone, phone_err = validate_phone_number(phone_number)
        if not valid_phone:
            flash(phone_err, 'danger')
            return render_template('login.html', selected_role='admin', active_tab='signup', colleges=colleges, form_data=request.form)

        # 3. Email Validation
        valid_email, email_err = validate_email_format(email)
        if not valid_email:
            flash(email_err, 'danger')
            return render_template('login.html', selected_role='admin', active_tab='signup', colleges=colleges, form_data=request.form)

        # 4. Password Validation
        valid_pwd, pwd_err = validate_password_strength(password)
        if not valid_pwd:
            flash(pwd_err, 'danger')
            return render_template('login.html', selected_role='admin', active_tab='signup', colleges=colleges, form_data=request.form)

        if password != confirm_password:
            flash('Confirm Password does not match Password.', 'danger')
            return render_template('login.html', selected_role='admin', active_tab='signup', colleges=colleges, form_data=request.form)

        # 5. College Validation
        college = db.session.get(College, college_id)
        if not college or college.status != 'active':
            flash('Please select an active, registered college institution.', 'danger')
            return render_template('login.html', selected_role='admin', active_tab='signup', colleges=colleges, form_data=request.form)

        # 6. Duplicate Checks
        if User.query.filter_by(email=email).first():
            flash('This email address is already registered in the platform.', 'danger')
            return render_template('login.html', selected_role='admin', active_tab='signup', colleges=colleges, form_data=request.form)

        if User.query.filter_by(identifier=admin_id).first():
            flash('This Administrator ID is already registered.', 'danger')
            return render_template('login.html', selected_role='admin', active_tab='signup', colleges=colleges, form_data=request.form)

        # Create College Admin User (status: pending_approval)
        new_user = User(
            identifier=admin_id,
            email=email,
            mobile_number=phone_number,
            phone_number=phone_number,
            role='college_admin',
            college_id=college.id,
            registration_status='pending_approval',
            is_active=False
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        college_admin_prof = CollegeAdminProfile(
            user_id=new_user.id,
            admin_id_code=admin_id,
            full_name=full_name,
            college_id=college.id,
            contact_number=phone_number,
            registration_status='pending_approval'
        )
        admin_prof = AdminProfile(
            user_id=new_user.id,
            admin_id_code=admin_id,
            full_name=full_name,
            college_id=college.id,
            contact_number=phone_number,
            registration_status='pending_approval'
        )
        verification = AccountVerification(
            user_id=new_user.id,
            requested_role='college_admin',
            college_id=college.id,
            status='pending_approval'
        )
        db.session.add_all([college_admin_prof, admin_prof, verification])
        db.session.commit()

        flash(
            f'College Administrator registration for {full_name} ({admin_id}) submitted successfully! '
            'Your account is currently PENDING APPROVAL by the Super Administrator. You will be able to log in once authorized.',
            'success'
        )
        return redirect(url_for('auth.login', role='admin', tab='login', identifier=admin_id))

    return redirect(url_for('auth.login', role='admin', tab='signup'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Password Reset Request:
    Generates time-limited reset tokens securely without leaking account existence.
    """
    dev_reset_url = None

    if request.method == 'POST':
        identifier_or_email = (request.form.get('identifier_or_email') or request.form.get('email', '')).strip()
        user = resolve_user_by_identifier(identifier_or_email)

        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)

            # Store in dedicated PasswordResetToken model
            db_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=user.reset_token_expiry
            )
            db.session.add(db_token)
            db.session.commit()

            dev_reset_url = url_for('auth.reset_password', token=token, _external=True)

        # Generic safe security notice (prevents user enumeration)
        flash(
            'If a matching registered account exists, password recovery instructions and a secure reset token have been generated.',
            'info'
        )
        return render_template('forgot_password.html', dev_reset_url=dev_reset_url, submitted=True)

    return render_template('forgot_password.html', dev_reset_url=None, submitted=False)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
    Password Reset Fulfillment:
    Validates token expiration, updates password hash, and invalidates token.
    """
    user = User.query.filter_by(reset_token=token).first()
    now = datetime.utcnow()

    if not user or not user.reset_token_expiry or user.reset_token_expiry < now:
        # Also check PasswordResetToken table
        token_record = PasswordResetToken.query.filter_by(token=token).first()
        if token_record and token_record.is_valid:
            user = token_record.user
        else:
            flash('This password reset link is invalid or has expired. Please submit a new request.', 'danger')
            return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        valid_pwd, pwd_err = validate_password_strength(password)
        if not valid_pwd:
            flash(pwd_err, 'danger')
            return render_template('reset_password.html', token=token, user=user)

        if password != confirm_password:
            flash('Confirm Password does not match Password.', 'danger')
            return render_template('reset_password.html', token=token, user=user)

        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None

        # Mark all active tokens for this user as used
        for t in PasswordResetToken.query.filter_by(user_id=user.id, used_at=None).all():
            t.used_at = datetime.utcnow()

        db.session.commit()

        flash('Your password has been reset successfully! Please sign in with your new credentials.', 'success')
        target_role = 'admin' if user.role == 'college_admin' else user.role
        return redirect(url_for('auth.login', role=target_role, tab='login', identifier=user.identifier))

    return render_template('reset_password.html', token=token, user=user)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/demo-login', methods=['POST'])
def demo_login():
    """
    Demonstration Mode Authentication Gateway:
    - Provides instant, flexible evaluation logins for Student, Faculty, and College Admin.
    - Operates only when DEMO_MODE_ENABLED=True in application configuration.
    - Guaranteed Isolation: Creates or links accounts exclusively to the isolated Demo College.
    - Protected: Super Admin dynamic creation is strictly rejected.
    """
    if not current_app.config.get('DEMO_MODE_ENABLED', False):
        flash('Demonstration Mode is disabled in this environment. Please log in with registered credentials.', 'danger')
        return redirect(url_for('auth.login', auth_mode='normal'))

    role = (request.form.get('role') or 'student').lower().strip()
    password = request.form.get('password', '').strip() or 'Demo@123'

    # Security Constraint: Super Admin dynamic creation is strictly prohibited
    if role in ('super_admin', 'superadmin'):
        flash('Super Administrator accounts cannot be created dynamically in Demo Mode. Please use authorized credentials in Normal Login Mode.', 'danger')
        return redirect(url_for('auth.login', auth_mode='demo', role='admin'))

    if role == 'student':
        name = request.form.get('name', '').strip() or 'Demo Student'
        email = request.form.get('email', '').strip()
        roll_number = request.form.get('roll_number', '').strip()
        college_name = request.form.get('college_name', '').strip()
        branch_name = request.form.get('branch', '').strip()

        user, err = authenticate_demo_student(
            name=name,
            email=email,
            roll_number=roll_number,
            college_name=college_name,
            branch_name=branch_name,
            password=password
        )
        if err:
            flash(err, 'danger')
            return redirect(url_for('auth.login', auth_mode='demo', role='student'))

        login_user(user, remember=False)
        flash(f'Demonstration Session Active: Signed in as Student {user.identifier}. Real university data is strictly isolated.', 'success')
        return redirect(url_for('student.dashboard'))

    elif role == 'faculty':
        name = request.form.get('name', '').strip() or 'Demo Professor'
        email = request.form.get('email', '').strip()
        faculty_id = request.form.get('faculty_id', '').strip()
        college_name = request.form.get('college_name', '').strip()
        department = request.form.get('department', '').strip()

        user, err = authenticate_demo_faculty(
            name=name,
            email=email,
            faculty_id=faculty_id,
            college_name=college_name,
            department_name=department,
            password=password
        )
        if err:
            flash(err, 'danger')
            return redirect(url_for('auth.login', auth_mode='demo', role='faculty'))

        login_user(user, remember=False)
        flash(f'Demonstration Session Active: Signed in as Faculty {user.identifier}. Connected to demo examination reports and evaluations.', 'success')
        return redirect(url_for('faculty.dashboard'))

    elif role in ('admin', 'college_admin'):
        name = request.form.get('name', '').strip() or 'Demo Administrator'
        email = request.form.get('email', '').strip()
        college_name = request.form.get('college_name', '').strip()
        admin_id = request.form.get('admin_id', '').strip()

        user, err = authenticate_demo_college_admin(
            name=name,
            email=email,
            college_name=college_name,
            admin_id=admin_id,
            password=password
        )
        if err:
            flash(err, 'danger')
            return redirect(url_for('auth.login', auth_mode='demo', role='admin'))

        login_user(user, remember=False)
        flash(f'Demonstration Session Active: Signed in as College Administrator {user.identifier}. Restricted strictly to Demo College.', 'success')
        return redirect(url_for('college_admin.dashboard'))

    flash('Invalid role specified for demonstration login.', 'danger')
    return redirect(url_for('auth.login', auth_mode='demo'))

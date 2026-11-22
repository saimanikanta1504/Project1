from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.extensions import db
from app.models import (
    College, User, StudentProfile, FacultyProfile, CollegeAdminProfile,
    AdminProfile, AccountVerification, Examination, ExamAttempt, ExamResult
)
from app.utils import super_admin_required, save_college_logo
from app.demo_service import get_demo_metrics, reset_demo_examination_data, purge_demo_accounts

super_admin_bp = Blueprint('super_admin', __name__)
super_admin_bp.before_request(super_admin_required)


@super_admin_bp.route('/dashboard')
def dashboard():
    total_colleges = College.query.count()
    active_colleges = College.query.filter_by(status='active').count()
    pending_colleges = College.query.filter_by(status='pending').count()
    total_students = StudentProfile.query.count()
    total_faculty = FacultyProfile.query.count()
    total_exams = Examination.query.count()
    total_attempts = ExamAttempt.query.count()

    colleges = College.query.order_by(College.created_at.desc()).limit(5).all()
    recent_exams = Examination.query.order_by(Examination.created_at.desc()).limit(5).all()

    return render_template(
        'super_admin/dashboard.html',
        total_colleges=total_colleges,
        active_colleges=active_colleges,
        pending_colleges=pending_colleges,
        total_students=total_students,
        total_faculty=total_faculty,
        total_exams=total_exams,
        total_attempts=total_attempts,
        colleges=colleges,
        recent_exams=recent_exams
    )


@super_admin_bp.route('/colleges')
def colleges():
    all_colleges = College.query.order_by(College.created_at.desc()).all()
    return render_template('super_admin/colleges.html', colleges=all_colleges)


@super_admin_bp.route('/colleges/new', methods=['GET', 'POST'])
def new_college():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        email = request.form.get('email', '').strip()
        contact_number = request.form.get('contact_number', '').strip()
        address = request.form.get('address', '').strip()
        status = request.form.get('status', 'active')

        # Admin details
        admin_id = request.form.get('admin_id', '').strip()
        admin_name = request.form.get('admin_name', '').strip()
        admin_email = request.form.get('admin_email', '').strip()
        admin_password = request.form.get('admin_password', '').strip()

        # Validation
        if not all([name, code, email, contact_number, address, admin_id, admin_name, admin_email, admin_password]):
            flash('All college and initial administrator fields are mandatory.', 'warning')
            return render_template('super_admin/college_form.html', is_edit=False)

        if College.query.filter((College.code == code) | (College.email == email)).first():
            flash('A college with this code or email address already exists.', 'danger')
            return render_template('super_admin/college_form.html', is_edit=False)

        if User.query.filter((User.identifier == admin_id) | (User.email == admin_email)).first():
            flash('An administrator user with this ID or email already exists.', 'danger')
            return render_template('super_admin/college_form.html', is_edit=False)

        # Handle Logo Upload
        logo_filename = 'default_college_logo.png'
        if 'logo' in request.files:
            uploaded_logo = save_college_logo(request.files['logo'])
            if uploaded_logo:
                logo_filename = uploaded_logo

        # Create College
        college = College(
            name=name,
            code=code,
            email=email,
            contact_number=contact_number,
            address=address,
            logo_filename=logo_filename,
            status=status
        )
        db.session.add(college)
        db.session.flush()

        # Create Administrator User & Profile
        admin_user = User(
            identifier=admin_id,
            email=admin_email,
            role='college_admin',
            college_id=college.id,
            is_active=True
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
        db.session.flush()

        admin_profile = CollegeAdminProfile(
            user_id=admin_user.id,
            admin_id_code=admin_id,
            full_name=admin_name,
            college_id=college.id,
            contact_number=contact_number
        )
        db.session.add(admin_profile)
        db.session.commit()

        flash(f'College "{name}" and College Administrator "{admin_name}" registered successfully.', 'success')
        return redirect(url_for('super_admin.colleges'))

    return render_template('super_admin/college_form.html', is_edit=False)


@super_admin_bp.route('/colleges/<int:college_id>/edit', methods=['GET', 'POST'])
def edit_college(college_id):
    college = College.query.get_or_404(college_id)

    if request.method == 'POST':
        college.name = request.form.get('name', '').strip()
        new_code = request.form.get('code', '').strip().upper()
        college.email = request.form.get('email', '').strip()
        college.contact_number = request.form.get('contact_number', '').strip()
        college.address = request.form.get('address', '').strip()
        college.status = request.form.get('status', 'active')

        # Check unique code
        existing = College.query.filter(College.code == new_code, College.id != college.id).first()
        if existing:
            flash(f'Code {new_code} is already utilized by another college.', 'danger')
            return render_template('super_admin/college_form.html', college=college, is_edit=True)

        college.code = new_code

        # Logo replacement
        if 'logo' in request.files and request.files['logo'].filename != '':
            uploaded_logo = save_college_logo(request.files['logo'])
            if uploaded_logo:
                college.logo_filename = uploaded_logo

        db.session.commit()
        flash(f'College details for "{college.name}" updated successfully.', 'success')
        return redirect(url_for('super_admin.colleges'))

    return render_template('super_admin/college_form.html', college=college, is_edit=True)


@super_admin_bp.route('/colleges/<int:college_id>/toggle-status', methods=['POST'])
def toggle_college_status(college_id):
    college = College.query.get_or_404(college_id)
    if college.status == 'active':
        college.status = 'deactivated'
        flash(f'College "{college.name}" has been deactivated.', 'warning')
    else:
        college.status = 'active'
        flash(f'College "{college.name}" is now active.', 'success')
    db.session.commit()
    return redirect(url_for('super_admin.colleges'))


@super_admin_bp.route('/users')
def users():
    role_filter = request.args.get('role', '')
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    all_users = query.order_by(User.created_at.desc()).all()
    return render_template('super_admin/users.html', users=all_users, current_filter=role_filter)


@super_admin_bp.route('/admins/<int:user_id>/approve', methods=['POST'])
def approve_admin(user_id):
    admin_user = User.query.filter_by(id=user_id, role='college_admin').first_or_404()
    admin_user.registration_status = 'approved'
    admin_user.is_active = True
    if admin_user.college_admin_profile:
        admin_user.college_admin_profile.registration_status = 'approved'
    if admin_user.admin_profile:
        admin_user.admin_profile.registration_status = 'approved'
    ver = AccountVerification.query.filter_by(user_id=admin_user.id, status='pending_approval').first()
    if ver:
        ver.status = 'approved'
        ver.reviewed_at = datetime.utcnow()
        from flask_login import current_user
        ver.reviewed_by_id = current_user.id
    db.session.commit()
    flash(f'College Administrator "{admin_user.identifier}" has been approved and activated.', 'success')
    return redirect(url_for('super_admin.users', role='college_admin'))


@super_admin_bp.route('/admins/<int:user_id>/reject', methods=['POST'])
def reject_admin(user_id):
    admin_user = User.query.filter_by(id=user_id, role='college_admin').first_or_404()
    admin_user.registration_status = 'rejected'
    admin_user.is_active = False
    if admin_user.college_admin_profile:
        admin_user.college_admin_profile.registration_status = 'rejected'
    if admin_user.admin_profile:
        admin_user.admin_profile.registration_status = 'rejected'
    ver = AccountVerification.query.filter_by(user_id=admin_user.id, status='pending_approval').first()
    if ver:
        ver.status = 'rejected'
        ver.reviewed_at = datetime.utcnow()
        from flask_login import current_user
        ver.reviewed_by_id = current_user.id
    db.session.commit()
    flash(f'College Administrator "{admin_user.identifier}" registration has been rejected.', 'warning')
    return redirect(url_for('super_admin.users', role='college_admin'))


@super_admin_bp.route('/super-admins/new', methods=['GET', 'POST'])
def new_super_admin():
    """Only existing Super Admins can provision additional Super Admin accounts."""
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip().upper()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not identifier or not email or not password:
            flash('All fields are mandatory for Super Administrator provisioning.', 'warning')
            return render_template('super_admin/super_admin_form.html')

        if len(password) < 8:
            flash('Password must contain at least 8 characters.', 'danger')
            return render_template('super_admin/super_admin_form.html')

        if password != confirm_password:
            flash('Confirm Password does not match Password.', 'danger')
            return render_template('super_admin/super_admin_form.html')

        if User.query.filter((User.identifier == identifier) | (User.email == email)).first():
            flash('A user with this Identifier or Email already exists.', 'danger')
            return render_template('super_admin/super_admin_form.html')

        new_user = User(
            identifier=identifier,
            email=email,
            role='super_admin',
            college_id=None,
            is_active=True,
            registration_status='approved'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash(f'Super Administrator account "{identifier}" provisioned successfully.', 'success')
        return redirect(url_for('super_admin.users', role='super_admin'))

    return render_template('super_admin/super_admin_form.html')


@super_admin_bp.route('/demo-management')
def demo_management():
    metrics = get_demo_metrics()
    return render_template('super_admin/demo_management.html', metrics=metrics)


@super_admin_bp.route('/demo-reset-exams', methods=['POST'])
def demo_reset_exams():
    count = reset_demo_examination_data()
    flash(f'Reset completed: {count} demonstration attempts and results were purged. Real college records remained untouched.', 'info')
    return redirect(url_for('super_admin.demo_management'))


@super_admin_bp.route('/demo-clean-accounts', methods=['POST'])
def demo_clean_accounts():
    count = purge_demo_accounts(preserve_baseline_cohort=True)
    flash(f'Cleaned {count} transient demo accounts. Baseline evaluation cohort and all real accounts preserved.', 'success')
    return redirect(url_for('super_admin.demo_management'))

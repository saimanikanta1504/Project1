from flask import Blueprint, redirect, url_for
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/api')
@main_bp.route('/api/index')
@main_bp.route('/api/index.py')
def index():
    """Single entrypoint: Automatically redirects authenticated users to their specific role dashboard, or to the login page."""
    if current_user.is_authenticated:
        if current_user.is_super_admin:
            return redirect(url_for('super_admin.dashboard'))
        elif current_user.is_college_admin:
            return redirect(url_for('college_admin.dashboard'))
        elif current_user.is_faculty:
            return redirect(url_for('faculty.dashboard'))
        elif current_user.is_student:
            return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))

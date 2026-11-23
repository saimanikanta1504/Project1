import os
from flask import Flask, render_template
from config import config
from app.extensions import db, login_manager, csrf


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure required directories exist safely (avoid read-only filesystem crash on serverless)
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except OSError:
        pass
    try:
        os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)
    except OSError:
        pass

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.super_admin import super_admin_bp
    from app.routes.college_admin import college_admin_bp
    from app.routes.faculty import faculty_bp
    from app.routes.student import student_bp
    from app.routes.examination import examination_bp
    from app.routes.results import results_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(super_admin_bp, url_prefix='/super-admin')
    app.register_blueprint(college_admin_bp, url_prefix='/college-admin')
    app.register_blueprint(faculty_bp, url_prefix='/faculty')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(examination_bp, url_prefix='/exam')
    app.register_blueprint(results_bp, url_prefix='/results')

    # Template context processors
    @app.context_processor
    def inject_global_data():
        return {
            'platform_name': 'ExamSphere Multi-College Platform',
            'current_year': 2026,
            'chr': chr,
            'demo_mode_enabled': app.config.get('DEMO_MODE_ENABLED', False)
        }

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # Ensure database schema is up-to-date with new tables and columns
    with app.app_context():
        from sqlalchemy import inspect, text
        db.create_all()
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            with db.engine.connect() as conn:
                if 'users' in tables:
                    user_cols = [c['name'] for c in inspector.get_columns('users')]
                    if 'phone_number' not in user_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(30)"))
                    if 'last_login_date' not in user_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN last_login_date DATETIME"))
                    if 'is_demo' not in user_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN is_demo BOOLEAN DEFAULT 0"))
                    if 'demo_session_id' not in user_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN demo_session_id VARCHAR(100)"))
                    if 'account_type' not in user_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN account_type VARCHAR(30) DEFAULT 'standard'"))

                if 'colleges' in tables:
                    col_cols = [c['name'] for c in inspector.get_columns('colleges')]
                    if 'is_demo' not in col_cols:
                        conn.execute(text("ALTER TABLE colleges ADD COLUMN is_demo BOOLEAN DEFAULT 0"))

                if 'examinations' in tables:
                    exam_cols = [c['name'] for c in inspector.get_columns('examinations')]
                    if 'is_demo' not in exam_cols:
                        conn.execute(text("ALTER TABLE examinations ADD COLUMN is_demo BOOLEAN DEFAULT 0"))

                if 'faculty_profiles' in tables:
                    fac_cols = [c['name'] for c in inspector.get_columns('faculty_profiles')]
                    if 'registration_status' not in fac_cols:
                        conn.execute(text("ALTER TABLE faculty_profiles ADD COLUMN registration_status VARCHAR(30) DEFAULT 'active'"))

                if 'college_admin_profiles' in tables:
                    adm_cols = [c['name'] for c in inspector.get_columns('college_admin_profiles')]
                    if 'registration_status' not in adm_cols:
                        conn.execute(text("ALTER TABLE college_admin_profiles ADD COLUMN registration_status VARCHAR(30) DEFAULT 'active'"))
                conn.commit()
        except Exception as e:
            app.logger.warning(f"Schema check notice: {e}")

    return app

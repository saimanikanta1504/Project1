import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IS_VERCEL = bool(os.environ.get('VERCEL'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'multi-college-exam-sec-key-2026-hermes')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = '/tmp/uploads' if IS_VERCEL else os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'svg', 'webp'}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 7200  # 2 hours CSRF validity for exams
    DEMO_MODE_ENABLED = os.environ.get('DEMO_MODE_ENABLED', 'true').lower() in ('true', '1', 'yes')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'examination_system.db')}"
    )
    DEMO_MODE_ENABLED = os.environ.get('DEMO_MODE_ENABLED', 'true').lower() in ('true', '1', 'yes')

class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    DEBUG = True
    DEMO_MODE_ENABLED = True

class ProductionConfig(Config):
    DEBUG = False
    _db_url = os.environ.get('DATABASE_URL')
    if _db_url and _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = _db_url or (
        'sqlite:////tmp/examination_system.db' if IS_VERCEL else f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'examination_system.db')}"
    )
    DEMO_MODE_ENABLED = os.environ.get('DEMO_MODE_ENABLED', 'true').lower() in ('true', '1', 'yes')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

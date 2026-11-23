import os
import sys

# Ensure root directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

config_name = os.environ.get('FLASK_CONFIG', os.environ.get('FLASK_ENV', 'production'))
app = create_app(config_name)

class VercelPathFixMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # 1. Clean SCRIPT_NAME if Vercel set it to /api/index
        script_name = environ.get('SCRIPT_NAME', '')
        if script_name.startswith('/api'):
            environ['SCRIPT_NAME'] = ''

        # 2. Extract real path from Vercel matched path or PATH_INFO
        path_info = environ.get('PATH_INFO', '')
        matched_path = environ.get('HTTP_X_MATCHED_PATH')

        if matched_path and not matched_path.startswith('/api/index'):
            environ['PATH_INFO'] = matched_path
        elif path_info.startswith('/api/index.py'):
            remainder = path_info[len('/api/index.py'):]
            environ['PATH_INFO'] = remainder if remainder else '/'
        elif path_info.startswith('/api/index'):
            remainder = path_info[len('/api/index'):]
            environ['PATH_INFO'] = remainder if remainder else '/'

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

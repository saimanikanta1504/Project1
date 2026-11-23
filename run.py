import os
from app import create_app
from app.extensions import db

default_config = 'production' if os.environ.get('VERCEL') else 'development'
config_name = os.environ.get('FLASK_CONFIG', os.environ.get('FLASK_ENV', default_config))

app = create_app(config_name)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)

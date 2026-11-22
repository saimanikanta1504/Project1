import os
from app import create_app
from app.extensions import db

app = create_app(os.environ.get('FLASK_CONFIG', 'development'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)

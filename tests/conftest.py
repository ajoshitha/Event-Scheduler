# tests/conftest.py
import sys
import os
import pytest

os.environ["FLASK_ENV"] = "testing"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.drop_all()
        db.create_all()

        # Add admin user only if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='test@admin.com', password='adminpass', role='admin')
            db.session.add(admin)

        # Add student user only if not exists
        if not User.query.filter_by(username='student').first():
            student = User(username='student', email='student@example.com', password='studentpass', role='student')
            db.session.add(student)

        db.session.commit()
        yield app.test_client()

        db.session.remove()
        db.drop_all()

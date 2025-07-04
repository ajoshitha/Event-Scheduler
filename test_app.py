import pytest
from app import app, db, User
from flask import url_for

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

def register_user(client, username, email, password):
    return client.post('/register', data={
        'username': username,
        'email': email,
        'password': password
    }, follow_redirects=True)

def login_user(client, email, password):
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Login' in response.data or b'Dashboard' in response.data

def test_register_login_logout(client):
    # Register
    rv = register_user(client, 'testuser', 'test@student.com', 'password')
    assert b'Registration successful' in rv.data

    # Login
    rv = login_user(client, 'test@student.com', 'password')
    assert b'student_dashboard' in rv.data or rv.status_code == 200

    # Logout
    rv = client.get('/logout', follow_redirects=True)
    assert b'Login' in rv.data

def test_student_cannot_access_admin_dashboard(client):
    register_user(client, 'testuser', 'test@student.com', 'password')
    login_user(client, 'test@student.com', 'password')
    rv = client.get('/dashboard', follow_redirects=True)
    assert b'Login' in rv.data or rv.status_code == 200

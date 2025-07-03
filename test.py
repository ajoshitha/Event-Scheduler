import pytest
from app import app, db, User, Event
from flask import session
from datetime import datetime

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

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

def test_register_success(client):
    response = register_user(client, 'testuser', 'test@example.com', '12345')
    assert b'Registration successful' in response.data

def test_register_duplicate_email(client):
    register_user(client, 'user1', 'dup@example.com', 'pass')
    response = register_user(client, 'user2', 'dup@example.com', 'pass')
    assert b'Email already registered' in response.data

def test_register_missing_fields(client):
    response = client.post('/register', data={}, follow_redirects=True)
    assert b'All fields are required' in response.data

def test_login_success(client):
    register_user(client, 'loginuser', 'login@example.com', 'abc123')
    response = login_user(client, 'login@example.com', 'abc123')
    assert b'dashboard' in response.data.lower()

def test_login_invalid_credentials(client):
    response = login_user(client, 'notfound@example.com', 'wrong')
    assert b'Invalid credentials' in response.data

def test_logout(client):
    register_user(client, 'logoutuser', 'logout@example.com', 'outpass')
    login_user(client, 'logout@example.com', 'outpass')
    response = client.get('/logout', follow_redirects=True)
    assert b'login' in response.data.lower() or b'home' in response.data.lower()

def test_dashboard_requires_login(client):
    response = client.get('/dashboard', follow_redirects=True)
    assert b'login' in response.data.lower()

def test_dashboard_authenticated(client):
    register_user(client, 'dashuser', 'dash@example.com', 'dashpass')
    login_user(client, 'dash@example.com', 'dashpass')
    response = client.get('/dashboard')
    assert b'Event' in response.data or b'dashboard' in response.data.lower()

def test_add_event(client):
    register_user(client, 'addevent', 'add@example.com', 'addpass')
    login_user(client, 'add@example.com', 'addpass')

    response = client.post('/add', data={
        'name': 'New Event',
        'description': 'An awesome event',
        'date': '2025-12-25',
        'time': '14:00'
    }, follow_redirects=True)
    assert b'New Event' in response.data or b'dashboard' in response.data.lower()

def test_update_event(client):
    register_user(client, 'updateuser', 'update@example.com', 'pass')
    login_user(client, 'update@example.com', 'pass')

    # Create an event
    with app.app_context():
        user = User.query.filter_by(email='update@example.com').first()
        event = Event(user_id=user.id, name='Old Name', description='Old', date=datetime.now().date(), time=datetime.now().time())
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    response = client.post(f'/update/{event_id}', data={
        'name': 'Updated Name',
        'description': 'Updated description',
        'date': '2025-11-11',
        'time': '11:11'
    }, follow_redirects=True)
    assert b'Updated Name' in response.data or b'dashboard' in response.data.lower()

def test_delete_event(client):
    register_user(client, 'deleteuser', 'delete@example.com', 'pass')
    login_user(client, 'delete@example.com', 'pass')

    # Add event
    with app.app_context():
        user = User.query.filter_by(email='delete@example.com').first()
        event = Event(user_id=user.id, name='To Delete', description='...', date=datetime.now().date(), time=datetime.now().time())
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    response = client.get(f'/delete/{event_id}', follow_redirects=True)
    assert b'To Delete' not in response.data  # Event should be gone

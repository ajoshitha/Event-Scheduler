# tests/test_routes.py
from app import app, db, Event, Feedback, Attendance, User
from flask import url_for
from datetime import datetime, timedelta


def test_homepage_redirect(client):
    client.post('/login', data={'email': 'test@admin.com', 'password': 'adminpass'})
    res = client.get('/')
    assert res.status_code == 302
    assert '/dashboard' in res.headers['Location']


def test_register_student(client):
    res = client.post('/register', data={
        'username': 'student1',
        'email': 'student1@example.com',
        'password': 'studentpass'
    }, follow_redirects=True)
    assert b'Login' in res.data

def test_register_admin(client):
    from app import db, User

    # Clean up any pre-existing user
    existing = User.query.filter_by(email='test@admin.com').first()
    if existing:
        db.session.delete(existing)
        db.session.commit()

    res = client.post('/register', data={
        'username': 'admin',
        'email': 'test@admin.com',
        'password': 'adminpass'
    }, follow_redirects=True)

    assert b'Login' in res.data  # If redirected properly


def test_login_valid_admin(client):
    res = client.post('/login', data={
        'email': 'test@admin.com',
        'password': 'adminpass'
    }, follow_redirects=True)
    assert b'Dashboard' in res.data or b'Event' in res.data


def test_login_invalid(client):
    res = client.post('/login', data={
        'email': 'wrong@example.com',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert b'Login' in res.data


def test_login_valid_student(client):
    res = client.post('/login', data={
        'email': 'student@example.com',
        'password': 'studentpass'
    }, follow_redirects=True)
    assert b'Student Dashboard' in res.data or b'Mark Attendance' in res.data


def test_add_event(client):
    client.post('/login', data={'email': 'test@admin.com', 'password': 'adminpass'}, follow_redirects=True)
    res = client.post('/add', data={
        'name': 'Test Event',
        'description': 'Event Description',
        'date': '2025-07-08',
        'time': '12:00'
    }, follow_redirects=True)
    assert b'Test Event' in res.data or b'Dashboard' in res.data


def test_mark_attendance_and_feedback(client):
    from app import db, User, Event, app

    with app.app_context():
        # Clean previous users if any
        User.query.filter_by(email='student@example.com').delete()
        User.query.filter_by(email='admin@example.com').delete()
        db.session.commit()

        # Add test admin
        admin = User(username='adminuser', email='admin@example.com', password='adminpass', role='admin')
        db.session.add(admin)
        db.session.commit()

        # Add test event
        event = Event(name='Test Event', description='Testing', date=datetime.now().date(),
                      time=datetime.now().time(), user_id=admin.id)
        db.session.add(event)
        db.session.commit()

        # Capture event_id before session ends
        event_id = event.id

        # Add student
        student = User(username='teststudent', email='student@example.com', password='studentpass', role='student')
        db.session.add(student)
        db.session.commit()

    # Login as student
    client.post('/login', data={'email': 'student@example.com', 'password': 'studentpass'}, follow_redirects=True)

    # Mark attendance
    res1 = client.post(f'/mark_present/{event_id}', follow_redirects=True)
    assert b'Marked as present' in res1.data or b'already marked' in res1.data

    # Submit feedback
    res2 = client.post(f'/feedback/{event_id}', data={'feedback': 'Great event!'}, follow_redirects=True)
    assert b'Feedback submitted' in res2.data or b'already given the feedback' in res2.data

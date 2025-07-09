from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from datetime import datetime
import os
import pymysql

pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.secret_key = 'your_secret_key'

if os.environ.get("FLASK_ENV") == "testing":
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Adminadmin123@localhost/event_scheduler'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    attendances = db.relationship('Attendance', cascade='all, delete', backref='event', lazy=True)
    feedbacks = db.relationship('Feedback', cascade='all, delete', backref='event', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    present = db.Column(db.Boolean, default=False)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    feedback = db.Column(db.Text, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')  
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields are required.')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered!')
        else:
            role = 'admin' if email.endswith('@admin.com') else 'student'
            user = User(username=username, email=email, password=password, role=role)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful!')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid credentials')            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    admin_id = request.args.get('admin_id', 'all')
    admins = User.query.filter_by(role='admin').all()

    if admin_id == 'all':
        events = Event.query.order_by(Event.date, Event.time).all()
    else:
        events = Event.query.filter_by(user_id=int(admin_id)).order_by(Event.date, Event.time).all()

    event_feedback = {}
    event_attendance = {}
    for event in events:
        feedbacks = db.session.query(Feedback, User).join(User, Feedback.user_id == User.id).filter(Feedback.event_id == event.id).all()
        event_feedback[event.id] = feedbacks
        attendances = db.session.query(Attendance, User).join(User, Attendance.user_id == User.id).filter(Attendance.event_id == event.id).all()
        event_attendance[event.id] = attendances

    return render_template('dashboard.html', events=events, event_feedback=event_feedback, event_attendance=event_attendance, admins=admins, selected_admin=admin_id)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_event():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        time = datetime.strptime(request.form['time'], '%H:%M').time()
        event = Event(name=name, description=description, date=date, time=time, user_id=current_user.id)
        db.session.add(event)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_event.html')

@app.route('/update/<int:event_id>', methods=['GET', 'POST'])
@login_required
def update_event(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        event.name = request.form['name']
        event.description = request.form['description']
        event.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        event.time = datetime.strptime(request.form['time'], '%H:%M').time()
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('update_event.html', event=event)

@app.route('/delete/<int:event_id>')
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))

    events = Event.query.order_by(Event.date, Event.time).all()
    for event in events:
        event.attendances = Attendance.query.filter_by(event_id=event.id).all()
        event.feedbacks = Feedback.query.filter_by(event_id=event.id).all()
    return render_template('student_dashboard.html', events=events)

@app.route('/mark_present/<int:event_id>', methods=['POST'])
@login_required
def mark_present(event_id):
    if current_user.role != 'student':
        return redirect(url_for('home'))
    attendance = Attendance.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if attendance:
        flash('You have already marked as present.')
    else:
        attendance = Attendance(user_id=current_user.id, event_id=event_id, present=True)
        db.session.add(attendance)
        db.session.commit()
        flash('Marked as present!')
    return redirect(url_for('student_dashboard'))

@app.route('/feedback/<int:event_id>', methods=['POST'])
@login_required
def submit_feedback(event_id):
    if current_user.role != 'student':
        return redirect(url_for('home'))
    feedback_text = request.form['feedback'].strip()
    if not feedback_text:
        flash('Please enter some text.')
        return redirect(url_for('student_dashboard'))
    existing_feedback = Feedback.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if existing_feedback:
        flash('You have already given the feedback.')
        return redirect(url_for('student_dashboard'))
    feedback = Feedback(user_id=current_user.id, event_id=event_id, feedback=feedback_text)
    db.session.add(feedback)
    db.session.commit()
    flash('Feedback submitted!')
    return redirect(url_for('student_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)

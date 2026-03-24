import os
from flask import Flask, render_template, flash, redirect, url_for, session, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Regexp, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------------------------------------
# App Configuration
# --------------------------------------------------
app = Flask(__name__)

# Use environment variable for secret key (production safe)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# --- DATABASE CONFIGURATION START ---
# Get the database URL from Render's environment variable
uri = os.environ.get("DATABASE_URL")

# Fix for Render: SQLAlchemy 1.4+ requires 'postgresql://' instead of 'postgres://'
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri

# Removed the MySQL SSL 'connect_args' as they are not needed for internal Postgres
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# --- DATABASE CONFIGURATION END ---

db = SQLAlchemy(app)

# --------------------------------------------------
# Database Models
# --------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('Task', backref='user', lazy=True)
    sessions = db.relationship('StudySession', backref='user', lazy=True)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"<Task {self.content}>"

class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    duration = db.Column(db.Integer, nullable=False)  # stored in seconds
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

# --------------------------------------------------
# Forms
# --------------------------------------------------
class UserForm(FlaskForm):
    username = StringField(validators=[DataRequired(), Length(min=5, max=20)])
    email = StringField("Enter email here", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Enter password here",
        validators=[
            DataRequired(),
            Length(min=8),
            Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])\S{8,}$',
                message="Password must contain uppercase, lowercase, number and special character"
            )
        ]
    )
    confirm_password = PasswordField(
        "Re-enter password",
        validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField("Submit")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class FeedbackForm(FlaskForm):
    name = StringField("Your Name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=100)])
    message = TextAreaField("Feedback", validators=[DataRequired()])
    submit = SubmitField("Submit Feedback")

# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/Aboutus')
def Aboutus():
    return render_template("Aboutus.html")

@app.route('/Contact', methods=['GET', 'POST'])
def Contact():
    form = FeedbackForm()
    if form.validate_on_submit():
        feedback = Feedback(
            name=form.name.data,
            email=form.email.data,
            message=form.message.data,
            user_id=session.get('user_id')
        )
        db.session.add(feedback)
        db.session.commit()
        flash("Thank you for your feedback!", "success")
        return redirect(url_for('Contact'))
    return render_template("contact.html", form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = UserForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password
        )
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login')) # Changed index to login for better UX
    return render_template("signup.html", form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            session['user_id'] = user.id
            session['username'] = user.username
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        flash("Invalid email or password", "danger")
    return render_template("login.html", form=form)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.date_added.desc()).all()

    week_ago = datetime.utcnow() - timedelta(days=7)
    sessions_data = StudySession.query.filter(
        StudySession.user_id == user_id,
        StudySession.date >= week_ago
    ).all()

    total_seconds = sum(s.duration for s in sessions_data)
    total_hours = round(total_seconds / 3600, 1)
    avg_per_day = round(total_hours / 7, 1)

    return render_template(
        "dashboard.html",
        username=session['username'],
        tasks=tasks,
        total_hours=total_hours,
        avg_per_day=avg_per_day
    )

@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    task_content = request.form['task']
    subject = request.form['subject']
    deadline_str = request.form.get('deadline')
    deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date() if deadline_str else None

    new_task = Task(
        content=task_content,
        subject=subject,
        deadline=deadline,
        user_id=session['user_id']
    )
    db.session.add(new_task)
    db.session.commit()
    flash("Task added successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    task = Task.query.get_or_404(task_id)
    if task.user_id != session['user_id']:
        return ('Unauthorized', 403)

    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/toggle_task/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    if 'user_id' not in session:
        return ('', 401)

    task = Task.query.get_or_404(task_id)
    if task.user_id != session['user_id']:
        return ('', 403)

    task.completed = not task.completed
    db.session.commit()
    return ('', 204)

@app.route('/timer')
def timer():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("timer.html")

@app.route('/save_session', methods=['POST'])
def save_session():
    if 'user_id' not in session:
        return ('', 401)

    duration = int(request.json['duration'])
    if duration <= 0:
        return ('Invalid duration', 400)

    session_entry = StudySession(
        duration=duration,
        user_id=session['user_id']
    )
    db.session.add(session_entry)
    db.session.commit()
    return ('', 204)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash("You have been logged out", "info")
    return redirect(url_for('index'))

@app.route("/initdb")
def initdb():
    try:
        with app.app_context():
            db.create_all()
        return "Database initialized successfully"
    except Exception as e:
        return f"Database initialization failed: {str(e)}"

# --------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

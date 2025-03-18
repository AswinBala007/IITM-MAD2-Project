from datetime import datetime

# from app import app
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()
bcrypt = Bcrypt()
# migrate = Migrate(app, db)

### 1️⃣ User Model (Admin & User) ###


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True,
                         nullable=False)  # Email ID
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(100))
    dob = db.Column(db.Date)
    role = db.Column(db.String(10), default="user")  # 'admin' or 'user'

    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(
            password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}', '{self.role}')"


### 2️⃣ Subject Model ###
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    chapters = db.relationship('Chapter', backref='subject', lazy=True)

    def __repr__(self):
        return f"Subject('{self.name}')"


### 3️⃣ Chapter Model ###
class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey(
        'subject.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)

    quizzes = db.relationship('Quiz', backref='chapter', lazy=True)

    def __repr__(self):
        return f"Chapter('{self.name}', Subject ID: {self.subject_id})"


### 4️⃣ Quiz Model ###
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey(
        'chapter.id'), nullable=False)
    date_of_quiz = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    time_duration = db.Column(
        db.Integer, nullable=False)  # Duration in minutes
    remarks = db.Column(db.Text, nullable=True)

    questions = db.relationship('Question', backref='quiz', lazy=True)
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True)

    def __repr__(self):
        return f"Quiz('{self.id}', Chapter ID: {self.chapter_id})"


### 5️⃣ Question Model ###
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(255), nullable=False)
    option2 = db.Column(db.String(255), nullable=False)
    option3 = db.Column(db.String(255), nullable=True)
    option4 = db.Column(db.String(255), nullable=True)
    correct_option = db.Column(
        db.Integer, nullable=False)  # Stores 1, 2, 3, or 4

    def __repr__(self):
        return f"Question('{self.id}', Quiz ID: {self.quiz_id})"


### 6️⃣ Quiz Attempt Model ###
class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)

    score = db.relationship('Score', backref='quiz_attempt', uselist=False)

    def __repr__(self):
        return f"QuizAttempt(User ID: {self.user_id}, Quiz ID: {self.quiz_id})"


### 7️⃣ Score Model ###
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_attempt_id = db.Column(db.Integer, db.ForeignKey(
        'quiz_attempt.id'), nullable=False)
    total_score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Score('{self.total_score}', Attempt ID: {self.quiz_attempt_id}')"


### Database Initialization ###
def create_admin():
    """Create the default admin user if not exists."""
    admin_user = User.query.filter_by(role="admin").first()
    if not admin_user:
        admin = User(username="admin@example.com",
                     full_name="Quiz Master", role="admin")
        admin.set_password("admin123")  # Change this in production
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created: admin@example.com / admin123")

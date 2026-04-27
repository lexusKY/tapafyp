from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)

    # Student profile only
    full_name = db.Column(db.String(150), nullable=True)
    student_id = db.Column(db.String(30), nullable=True)
    programme = db.Column(db.String(150), nullable=True)
    faculty = db.Column(db.String(150), nullable=True)
    year_of_study = db.Column(db.String(30), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    materials = db.relationship(
        "Material",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan"
    )

    quiz_attempts = db.relationship(
        "QuizAttempt",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)

    # Each uploaded material belongs to one user
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Basic material information
    course_code = db.Column(db.String(30), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), nullable=False)

    # Favourite / pinned material
    is_pinned = db.Column(db.Boolean, nullable=False, default=False)

    # Extraction text
    extracted_text = db.Column(db.Text, nullable=True)

    # User-reviewed cleaned text used for quiz generation
    cleaned_text = db.Column(db.Text, nullable=True)

    # Preferences for this specific material/quiz
    quiz_difficulty = db.Column(db.String(20), nullable=True, default="All")
    question_count = db.Column(db.Integer, nullable=True, default=5)
    question_style = db.Column(db.String(50), nullable=True, default="MCQ")
    quiz_focus = db.Column(db.Text, nullable=True)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    questions = db.relationship(
        "Question",
        backref="material",
        lazy=True,
        cascade="all, delete-orphan"
    )

    quiz_attempts = db.relationship(
        "QuizAttempt",
        backref="material",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)

    material_id = db.Column(
        db.Integer,
        db.ForeignKey("materials.id"),
        nullable=False
    )

    question_text = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    question_type = db.Column(db.String(50), nullable=True, default="mcq")
    hint = db.Column(db.Text, nullable=True)
    explanation = db.Column(db.Text, nullable=True)

    choices = db.relationship(
        "Choice",
        backref="question",
        lazy=True,
        cascade="all, delete-orphan"
    )

    quiz_answers = db.relationship(
        "QuizAnswer",
        backref="question",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Choice(db.Model):
    __tablename__ = "choices"

    id = db.Column(db.Integer, primary_key=True)

    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id"),
        nullable=False
    )

    choice_text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    selected_answers = db.relationship(
        "QuizAnswer",
        foreign_keys="QuizAnswer.selected_choice_id",
        backref="selected_choice",
        lazy=True
    )

    correct_answers = db.relationship(
        "QuizAnswer",
        foreign_keys="QuizAnswer.correct_choice_id",
        backref="correct_choice",
        lazy=True
    )


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    material_id = db.Column(
        db.Integer,
        db.ForeignKey("materials.id"),
        nullable=False
    )

    level = db.Column(db.String(30), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)

    attempt_type = db.Column(db.String(20), nullable=False, default="normal")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    answers = db.relationship(
        "QuizAnswer",
        backref="attempt",
        lazy=True,
        cascade="all, delete-orphan"
    )


class QuizAnswer(db.Model):
    __tablename__ = "quiz_answers"

    id = db.Column(db.Integer, primary_key=True)

    attempt_id = db.Column(
        db.Integer,
        db.ForeignKey("quiz_attempts.id"),
        nullable=False
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id"),
        nullable=False
    )

    selected_choice_id = db.Column(
        db.Integer,
        db.ForeignKey("choices.id"),
        nullable=True
    )

    correct_choice_id = db.Column(
        db.Integer,
        db.ForeignKey("choices.id"),
        nullable=True
    )

    is_correct = db.Column(db.Boolean, nullable=False, default=False)
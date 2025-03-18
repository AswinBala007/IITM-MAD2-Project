from functools import wraps

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from models import Chapter, Question, Quiz, Subject, User, db

# Define Blueprint
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

### 1️⃣ Admin Role Checker Decorator ###


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

### 2️⃣ Admin Dashboard - Welcome Endpoint ###


@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def admin_dashboard():
    return jsonify({"message": "Welcome to the Admin Dashboard"}), 200


### 3️⃣ CRUD Operations ###

# ➤ Create Subject
@admin_bp.route("/subjects", methods=["POST"])
@admin_required
def create_subject():
    data = request.json
    name = data.get("name")
    description = data.get("description", "")

    if not name:
        return jsonify({"error": "Subject name is required"}), 400

    subject = Subject(name=name, description=description)
    db.session.add(subject)
    db.session.commit()

    return jsonify({"message": "Subject created successfully", "subject_id": subject.id}), 201


# ➤ Get All Subjects
@admin_bp.route("/subjects", methods=["GET"])
@admin_required
def get_subjects():
    subjects = Subject.query.all()
    return jsonify([{"id": s.id, "name": s.name, "description": s.description} for s in subjects]), 200


# ➤ Update Subject
@admin_bp.route("/subjects/<int:subject_id>", methods=["PUT"])
@admin_required
def update_subject(subject_id):
    data = request.json
    subject = Subject.query.get(subject_id)

    if not subject:
        return jsonify({"error": "Subject not found"}), 404

    subject.name = data.get("name", subject.name)
    subject.description = data.get("description", subject.description)

    db.session.commit()
    return jsonify({"message": "Subject updated successfully"}), 200


# ➤ Delete Subject
@admin_bp.route("/subjects/<int:subject_id>", methods=["DELETE"])
@admin_required
def delete_subject(subject_id):
    subject = Subject.query.get(subject_id)

    if not subject:
        return jsonify({"error": "Subject not found"}), 404

    db.session.delete(subject)
    db.session.commit()
    return jsonify({"message": "Subject deleted successfully"}), 200


# ➤ Create Chapter Under a Subject
@admin_bp.route("/subjects/<int:subject_id>/chapters", methods=["POST"])
@admin_required
def create_chapter(subject_id):
    data = request.json
    name = data.get("name")
    description = data.get("description", "")

    if not name:
        return jsonify({"error": "Chapter name is required"}), 400

    chapter = Chapter(name=name, subject_id=subject_id,
                      description=description)
    db.session.add(chapter)
    db.session.commit()

    return jsonify({"message": "Chapter created successfully", "chapter_id": chapter.id}), 201


# ➤ Get Chapters of a Subject
@admin_bp.route("/subjects/<int:subject_id>/chapters", methods=["GET"])
@admin_required
def get_chapters(subject_id):
    chapters = Chapter.query.filter_by(subject_id=subject_id).all()
    return jsonify([{"id": c.id, "name": c.name, "description": c.description} for c in chapters]), 200


# ➤ Create Quiz Under a Chapter
@admin_bp.route("/chapters/<int:chapter_id>/quizzes", methods=["POST"])
@admin_required
def create_quiz(chapter_id):
    data = request.json
    time_duration = data.get("time_duration", 30)  # Default 30 minutes
    remarks = data.get("remarks", "")

    quiz = Quiz(chapter_id=chapter_id,
                time_duration=time_duration, remarks=remarks)
    db.session.add(quiz)
    db.session.commit()

    return jsonify({"message": "Quiz created successfully", "quiz_id": quiz.id}), 201


# ➤ Get Quizzes Under a Chapter
@admin_bp.route("/chapters/<int:chapter_id>/quizzes", methods=["GET"])
@admin_required
def get_quizzes(chapter_id):
    quizzes = Quiz.query.filter_by(chapter_id=chapter_id).all()
    return jsonify([{"id": q.id, "time_duration": q.time_duration, "remarks": q.remarks} for q in quizzes]), 200


# ➤ Create Question Under a Quiz
@admin_bp.route("/quizzes/<int:quiz_id>/questions", methods=["POST"])
@admin_required
def create_question(quiz_id):
    data = request.json
    question_text = data.get("question_text")
    options = [data.get("option1"), data.get("option2"),
               data.get("option3"), data.get("option4")]
    correct_option = data.get("correct_option")

    if not question_text or not correct_option or not options[0] or not options[1]:
        return jsonify({"error": "Question, at least 2 options, and correct answer are required"}), 400

    question = Question(
        quiz_id=quiz_id,
        question_text=question_text,
        option1=options[0],
        option2=options[1],
        option3=options[2],
        option4=options[3],
        correct_option=correct_option
    )

    db.session.add(question)
    db.session.commit()

    return jsonify({"message": "Question created successfully", "question_id": question.id}), 201


# ➤ Get All Users (Admin View)
@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_users():
    users = User.query.all()
    return jsonify([{"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role} for u in users]), 200


# ➤ Delete User (Admin Action)
@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted successfully"}), 200

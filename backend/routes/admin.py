from functools import wraps

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import cache, db
from models import Chapter, Question, Quiz, Subject, User, QuizAttempt, Score

# Define Blueprint
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

### 1️⃣ Admin Role Checker Decorator ###


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        
        # Check if user has admin role in database
        user = User.query.get(user_id)
        if not user or user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
            
        return fn(*args, **kwargs)
    return wrapper

### 2️⃣ Admin Dashboard - Welcome Endpoint ###
@admin_bp.route("/statistics", methods=["GET"])
@admin_required
@cache.cached(timeout=300, key_prefix='admin_statistics')  # Cache for 5 minutes
def get_dashboard_statistics():
    # Get counts of various entities
    total_users = User.query.filter_by(role="user").count()
    total_admins = User.query.filter_by(role="admin").count()
    total_subjects = Subject.query.count()
    total_chapters = Chapter.query.count()
    total_quizzes = Quiz.query.count()
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5)
    recent_users_data = [{
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "joined": user.created_at.strftime("%Y-%m-%d")
    } for user in recent_users]

    # Get quiz statistics
    quiz_stats = db.session.query(
        Quiz.id,
        Quiz.date_of_quiz,
        db.func.count(QuizAttempt.id).label('total_attempts'),
        db.func.avg(Score.total_score).label('avg_score')
    ).select_from(Quiz).outerjoin(QuizAttempt).outerjoin(Score).group_by(Quiz.id).limit(5).all()

    quiz_stats_data = [{
        "quiz_id": stat.id,
        "date": stat.date_of_quiz.strftime("%Y-%m-%d") if stat.date_of_quiz else None,
        "total_attempts": int(stat.total_attempts),
        "avg_score": round(float(stat.avg_score if stat.avg_score else 0), 2)
    } for stat in quiz_stats]

    # Get subject-wise chapter counts
    subject_stats = db.session.query(
        Subject.name,
        db.func.count(Chapter.id).label('chapter_count')
    ).outerjoin(Chapter).group_by(Subject.id).all()

    subject_stats_data = [{
        "subject": stat.name,
        "chapters": int(stat.chapter_count)
    } for stat in subject_stats]

    return jsonify({
        "overview": {
            "total_users": total_users,
            "total_admins": total_admins,
            "total_subjects": total_subjects,
            "total_chapters": total_chapters,
            "total_quizzes": total_quizzes
        },
        "recent_users": recent_users_data,
        "quiz_statistics": quiz_stats_data,
        "subject_statistics": subject_stats_data
    }), 200


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
    
    # Clear subject caches
    cache.delete('all_subjects')
    
    return jsonify({"message": "Subject created successfully", "subject_id": subject.id}), 201


# ➤ Get All Subjects
@admin_bp.route("/subjects", methods=["GET"])
@admin_required
@cache.cached(timeout=3600, key_prefix='admin_subjects')  # Cache for 1 hour
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
    
    # Clear subject caches
    cache.delete('all_subjects')
    cache.delete('admin_subjects')
    
    # Clear related quiz caches
    chapters = Chapter.query.filter_by(subject_id=subject_id).all()
    for chapter in chapters:
        cache.delete(f'subject_quizzes_{subject_id}')
    
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
    
    # Clear subject caches
    cache.delete('all_subjects')
    cache.delete('admin_subjects')
    cache.delete(f'subject_quizzes_{subject_id}')
    
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
    
    # Clear related caches
    cache.delete(f'subject_chapters_{subject_id}')
    cache.delete('admin_statistics')
    
    return jsonify({"message": "Chapter created successfully", "chapter_id": chapter.id}), 201


# ➤ Get Chapters of a Subject
@admin_bp.route("/subjects/<int:subject_id>/chapters", methods=["GET"])
@admin_required
@cache.cached(timeout=1800, key_prefix=lambda: f'subject_chapters_{request.view_args["subject_id"]}')  # Cache for 30 minutes
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
    
    # Clear related caches
    chapter = Chapter.query.get(chapter_id)
    if chapter:
        cache.delete(f'subject_quizzes_{chapter.subject_id}')
    cache.delete(f'chapter_quizzes_{chapter_id}')
    cache.delete('admin_statistics')
    
    return jsonify({"message": "Quiz created successfully", "quiz_id": quiz.id}), 201


# ➤ Get Quizzes Under a Chapter
@admin_bp.route("/chapters/<int:chapter_id>/quizzes", methods=["GET"])
@admin_required
@cache.cached(timeout=1800, key_prefix=lambda: f'chapter_quizzes_{request.view_args["chapter_id"]}')  # Cache for 30 minutes
def get_quizzes(chapter_id):
    quizzes = Quiz.query.filter_by(chapter_id=chapter_id).all()
    return jsonify([{"id": q.id, "time_duration": q.time_duration, "remarks": q.remarks} for q in quizzes]), 200


# ➤ Create Question Under a Quiz
@admin_bp.route("/quizzes/<int:quiz_id>/questions", methods=["POST"])
@admin_required
def create_question(quiz_id):
    data = request.json
    question_text = data.get("question_text")
    option1 = data.get("option1")
    option2 = data.get("option2")
    option3 = data.get("option3")
    option4 = data.get("option4")
    correct_option = data.get("correct_option")

    if not question_text or not option1 or not option2 or not correct_option:
        return jsonify({"error": "Missing required question data"}), 400

    question = Question(
        quiz_id=quiz_id,
        question_text=question_text,
        option1=option1,
        option2=option2,
        option3=option3,
        option4=option4,
        correct_option=correct_option
    )
    db.session.add(question)
    db.session.commit()
    
    # Clear question cache
    cache.delete(f'quiz_questions_{quiz_id}')
    
    return jsonify({"message": "Question created successfully", "question_id": question.id}), 201


# ➤ Get Questions of a Quiz
@admin_bp.route("/quizzes/<int:quiz_id>/questions", methods=["GET"])
@admin_required
@cache.cached(timeout=1800, key_prefix=lambda: f'admin_quiz_questions_{request.view_args["quiz_id"]}')  # Cache for 30 minutes
def get_questions(quiz_id):
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    return jsonify([{
        "id": q.id,
        "question_text": q.question_text,
        "option1": q.option1,
        "option2": q.option2,
        "option3": q.option3,
        "option4": q.option4,
        "correct_option": q.correct_option
    } for q in questions]), 200


# ➤ Update Question
@admin_bp.route("/questions/<int:question_id>", methods=["PUT"])
@admin_required
def update_question(question_id):
    data = request.json
    question = Question.query.get(question_id)

    if not question:
        return jsonify({"error": "Question not found"}), 404

    # Update fields
    if "question_text" in data:
        question.question_text = data["question_text"]
    if "option1" in data:
        question.option1 = data["option1"]
    if "option2" in data:
        question.option2 = data["option2"]
    if "option3" in data:
        question.option3 = data["option3"]
    if "option4" in data:
        question.option4 = data["option4"]
    if "correct_option" in data:
        question.correct_option = data["correct_option"]

    db.session.commit()
    
    # Clear question caches
    cache.delete(f'quiz_questions_{question.quiz_id}')
    cache.delete(f'admin_quiz_questions_{question.quiz_id}')
    
    return jsonify({"message": "Question updated successfully"}), 200


# ➤ Delete Question
@admin_bp.route("/questions/<int:question_id>", methods=["DELETE"])
@admin_required
def delete_question(question_id):
    question = Question.query.get(question_id)

    if not question:
        return jsonify({"error": "Question not found"}), 404

    quiz_id = question.quiz_id
    db.session.delete(question)
    db.session.commit()
    
    # Clear question caches
    cache.delete(f'quiz_questions_{quiz_id}')
    cache.delete(f'admin_quiz_questions_{quiz_id}')
    
    return jsonify({"message": "Question deleted successfully"}), 200


# ➤ Update Quiz
@admin_bp.route("/quizzes/<int:quiz_id>", methods=["PUT"])
@admin_required
def update_quiz(quiz_id):
    data = request.json
    quiz = Quiz.query.get(quiz_id)

    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404

    quiz.time_duration = data.get("time_duration", quiz.time_duration)
    quiz.remarks = data.get("remarks", quiz.remarks)

    db.session.commit()
    
    # Clear related caches
    chapter = Chapter.query.get(quiz.chapter_id)
    if chapter:
        cache.delete(f'subject_quizzes_{chapter.subject_id}')
    cache.delete(f'chapter_quizzes_{quiz.chapter_id}')
    cache.delete(f'quiz_{quiz_id}')
    
    return jsonify({"message": "Quiz updated successfully"}), 200


# ➤ Delete Quiz
@admin_bp.route("/quizzes/<int:quiz_id>", methods=["DELETE"])
@admin_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)

    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    
    chapter_id = quiz.chapter_id
    chapter = Chapter.query.get(chapter_id)
    
    db.session.delete(quiz)
    db.session.commit()
    
    # Clear related caches
    if chapter:
        cache.delete(f'subject_quizzes_{chapter.subject_id}')
    cache.delete(f'chapter_quizzes_{chapter_id}')
    cache.delete(f'quiz_{quiz_id}')
    cache.delete(f'quiz_questions_{quiz_id}')
    cache.delete(f'admin_quiz_questions_{quiz_id}')
    cache.delete('admin_statistics')
    
    return jsonify({"message": "Quiz deleted successfully"}), 200


# ➤ Get User Quiz Attempts for Admin
@admin_bp.route("/users/<int:user_id>/attempts", methods=["GET"])
@admin_required
@cache.cached(timeout=300, key_prefix=lambda: f'admin_user_attempts_{request.view_args["user_id"]}')  # Cache for 5 minutes
def get_user_attempts(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    attempts = QuizAttempt.query.filter_by(user_id=user_id).all()
    attempts_data = []

    for attempt in attempts:
        try:
            quiz = Quiz.query.get(attempt.quiz_id)
            score_value = attempt.score.total_score if attempt.score else None

            attempts_data.append({
                "attempt_id": attempt.id,
                "quiz_id": attempt.quiz_id,
                "quiz_name": f"Quiz #{quiz.id}" if quiz else "Unknown",
                "start_time": attempt.start_time.strftime("%Y-%m-%d %H:%M") if attempt.start_time else None,
                "end_time": attempt.end_time.strftime("%Y-%m-%d %H:%M") if attempt.end_time else None,
                "score": score_value
            })
        except Exception as e:
            # Skip invalid attempts
            continue

    return jsonify(attempts_data), 200


# ➤ Search Users
@admin_bp.route("/search/users", methods=["GET"])
@admin_required
def search_users():
    query = request.args.get("q", "")
    if not query or len(query) < 2:
        return jsonify({"error": "Search query must be at least 2 characters"}), 400

    users = User.query.filter(
        (User.email.like(f"%{query}%")) |
        (User.full_name.like(f"%{query}%"))
    ).limit(10).all()

    return jsonify([{
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role
    } for user in users]), 200


# ➤ Search Subjects
@admin_bp.route("/search/subjects", methods=["GET"])
@admin_required
def search_subjects():
    query = request.args.get("q", "")
    if not query or len(query) < 2:
        return jsonify({"error": "Search query must be at least 2 characters"}), 400

    subjects = Subject.query.filter(
        Subject.name.like(f"%{query}%")
    ).limit(10).all()

    return jsonify([{
        "id": subject.id,
        "name": subject.name
    } for subject in subjects]), 200


# ➤ Search Quizzes
@admin_bp.route("/search/quizzes", methods=["GET"])
@admin_required
def search_quizzes():
    query = request.args.get("q", "")
    if not query or len(query) < 1:  # Allow searching by quiz ID, which might be just one digit
        return jsonify({"error": "Search query required"}), 400

    # Search by ID if the query is a number
    if query.isdigit():
        quizzes = Quiz.query.filter_by(id=int(query)).all()
    else:
        # Otherwise search by remarks
        quizzes = Quiz.query.filter(
            Quiz.remarks.like(f"%{query}%")
        ).limit(10).all()

    result = []
    for quiz in quizzes:
        chapter = Chapter.query.get(quiz.chapter_id)
        subject = Subject.query.get(chapter.subject_id) if chapter else None

        result.append({
            "id": quiz.id,
            "remarks": quiz.remarks,
            "chapter": chapter.name if chapter else "Unknown",
            "subject": subject.name if subject else "Unknown"
        })

    return jsonify(result), 200

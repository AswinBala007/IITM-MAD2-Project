from datetime import datetime, timezone, timedelta
import json
import os

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import cache, db
from models import Chapter, Question, Quiz, QuizAttempt, Score, Subject, User

user_bp = Blueprint('user', __name__, url_prefix='/user')

### 1️⃣ Fetch Available Subjects & Quizzes ###

@user_bp.route('/subjects', methods=['GET'])
@jwt_required()
@cache.cached(timeout=3600, key_prefix='all_subjects')  # Cache for 1 hour
def get_subjects():
    subjects = Subject.query.all()
    return jsonify([{"id": sub.id, "name": sub.name} for sub in subjects])


@user_bp.route('/quizzes/<int:subject_id>', methods=['GET'])
@jwt_required()
@cache.cached(timeout=900, key_prefix=lambda: f'subject_quizzes_{request.view_args["subject_id"]}')  # Cache for 15 minutes
def get_quizzes(subject_id):
    quizzes = Quiz.query.join(Chapter).filter(
        Chapter.subject_id == subject_id).all()
    return jsonify([{
        "id": quiz.id, 
        "date": quiz.date_of_quiz.strftime('%Y-%m-%d') if quiz.date_of_quiz else None, 
        "duration": quiz.time_duration
    } for quiz in quizzes])

### 2️⃣ Start a Quiz Attempt ###

@user_bp.route('/quiz/<int:quiz_id>/start', methods=['POST'])
@jwt_required()
def start_quiz_attempt(quiz_id):
    user_id = get_jwt_identity()
    
    # Check if quiz exists - use cached data if available
    quiz_cache_key = f'quiz_{quiz_id}'
    cached_quiz = None  # Simple cache instead of Redis
    
    if cached_quiz:
        quiz_data = json.loads(cached_quiz.decode('utf-8'))
        quiz_obj = type('Quiz', (), {
            'id': quiz_data['id'],
            'time_duration': quiz_data['time_duration']
        })
    else:
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return jsonify({"error": "Quiz not found"}), 404
        
        # Cache the quiz data (using in-memory cache)
        quiz_data = {
            'id': quiz.id,
            'time_duration': quiz.time_duration
        }
        quiz_obj = quiz
    
    # Check if user already has an active attempt for this quiz
    active_attempt = QuizAttempt.query.filter_by(
        user_id=user_id, 
        quiz_id=quiz_id, 
        end_time=None
    ).first()
    
    if active_attempt:
        # Calculate remaining time
        elapsed = datetime.now(timezone.utc) - active_attempt.start_time
        remaining_seconds = max(0, (quiz_obj.time_duration * 60) - elapsed.total_seconds())
        
        return jsonify({
            "message": "Quiz already started",
            "attempt_id": active_attempt.id,
            "remaining_seconds": remaining_seconds,
            "questions": get_quiz_questions_data(quiz_id)
        })
    
    # Create new attempt
    now = datetime.now(timezone.utc)
    quiz_attempt = QuizAttempt(
        user_id=user_id,
        quiz_id=quiz_id,
        start_time=now
    )
    db.session.add(quiz_attempt)
    db.session.commit()
    
    # Clear user history cache
    cache.delete_memoized(get_user_history, user_id)
    
    return jsonify({
        "message": "Quiz started",
        "attempt_id": quiz_attempt.id,
        "remaining_seconds": quiz_obj.time_duration * 60,
        "questions": get_quiz_questions_data(quiz_id)
    })

@cache.memoize(timeout=900)  # Cache for 15 minutes
def get_quiz_questions_data(quiz_id):
    # Check if questions are cached in Redis
    questions_cache_key = f'quiz_questions_{quiz_id}'
    cached_questions = None  # Simple cache instead of Redis
    
    if cached_questions:
        return json.loads(cached_questions.decode('utf-8'))
    
    # If not cached, fetch from database
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    result = [{
        "id": q.id, 
        "question": q.question_text,
        "options": [q.option1, q.option2, q.option3, q.option4]
    } for q in questions]
    
    # Cache the results (using SimpleCache)
    
    return result

### 3️⃣ Get Quiz Questions ###
@user_bp.route('/quiz/<int:quiz_id>', methods=['GET'])
@jwt_required()
def get_quiz_questions(quiz_id):
    user_id = get_jwt_identity()
    
    # Check if user has an active attempt
    active_attempt = QuizAttempt.query.filter_by(
        user_id=user_id, 
        quiz_id=quiz_id, 
        end_time=None
    ).first()
    
    if not active_attempt:
        return jsonify({"error": "No active quiz attempt found"}), 400
        
    # Check if time has expired
    quiz = Quiz.query.get(quiz_id)
    elapsed = datetime.now(timezone.utc) - active_attempt.start_time
    remaining_seconds = max(0, (quiz.time_duration * 60) - elapsed.total_seconds())
    
    if remaining_seconds <= 0:
        # Auto-submit with empty answers if time expired
        active_attempt.end_time = datetime.now(timezone.utc)
        db.session.commit()
        
        # Clear user history cache
        cache.delete_memoized(get_user_history, user_id)
        
        return jsonify({"error": "Quiz time has expired"}), 400
    
    questions = get_quiz_questions_data(quiz_id)
    return jsonify({
        "attempt_id": active_attempt.id,
        "remaining_seconds": remaining_seconds,
        "questions": questions
    })

### 4️⃣ Submit Quiz Attempt ###
@user_bp.route('/quiz/submit', methods=['POST'])
@jwt_required()
def submit_quiz_attempt():
    user_id = get_jwt_identity()
    data = request.json
    attempt_id = data.get('attempt_id')
    answers = data.get('answers', {})  # Format: {question_id: selected_option}

    if not attempt_id:
        return jsonify({"error": "Attempt ID required"}), 400

    # Get the attempt
    quiz_attempt = QuizAttempt.query.get(attempt_id)
    if not quiz_attempt:
        return jsonify({"error": "Quiz attempt not found"}), 404
        
    # Check if this attempt belongs to the current user
    if quiz_attempt.user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403
        
    # Check if already submitted
    if quiz_attempt.end_time is not None:
        return jsonify({"error": "Quiz already submitted"}), 400
    
    # Check if time has expired
    quiz = Quiz.query.get(quiz_attempt.quiz_id)
    elapsed = datetime.now(timezone.utc) - quiz_attempt.start_time
    if elapsed.total_seconds() > (quiz.time_duration * 60):
        # Time expired - give zero score
        quiz_attempt.end_time = datetime.now(timezone.utc)
        
        score = Score(
            quiz_attempt_id=quiz_attempt.id,
            user_id=user_id,
            total_score=0
        )
        db.session.add(score)
        db.session.commit()
        
        # Clear user history cache
        cache.delete_memoized(get_user_history, user_id)
        
        return jsonify({
            "message": "Quiz time expired",
            "score": 0
        }), 200

    # Set end time
    quiz_attempt.end_time = datetime.now(timezone.utc)
    
    # Calculate score
    correct_answers = 0
    total_questions = Question.query.filter_by(quiz_id=quiz_attempt.quiz_id).count()
    
    if total_questions == 0:
        total_questions = 1  # Avoid division by zero
    
    for qid, selected_option in answers.items():
        question = Question.query.get(int(qid))
        if question and int(selected_option) == question.correct_option:
            correct_answers += 1

    # Create score record
    score_value = int((correct_answers / total_questions) * 100)
    score = Score(
        quiz_attempt_id=quiz_attempt.id, 
        user_id=user_id,
        total_score=score_value
    )
    db.session.add(score)
    db.session.commit()
    
    # Clear user history cache
    cache.delete_memoized(get_user_history, user_id)

    return jsonify({
        "message": "Quiz submitted successfully", 
        "score": score_value,
        "correct": correct_answers,
        "total": total_questions
    })

### 5️⃣ Fetch User Quiz History ###

@user_bp.route('/history', methods=['GET'])
@jwt_required()
def get_user_history_route():
    user_id = get_jwt_identity()
    return jsonify(get_user_history(user_id))

@cache.memoize(timeout=300)  # Cache for 5 minutes
def get_user_history(user_id):
    attempts = QuizAttempt.query.filter_by(user_id=user_id).all()

    history = []
    for attempt in attempts:
        try:
            entry = {
                "quiz_id": attempt.quiz_id,
                "start_time": attempt.start_time.strftime('%Y-%m-%d %H:%M') if attempt.start_time else "N/A",
                "end_time": attempt.end_time.strftime('%Y-%m-%d %H:%M') if attempt.end_time else "In Progress",
                "score": attempt.score.total_score if attempt.score else "N/A"
            }
            history.append(entry)
        except Exception as e:
            # Skip any attempts with missing data
            continue

    return history
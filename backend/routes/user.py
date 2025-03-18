from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from models import Question, Quiz, QuizAttempt, Score, Subject, User, db

user_bp = Blueprint('user', __name__, url_prefix='/user')

### 1️⃣ Fetch Available Subjects & Quizzes ###


@user_bp.route('/subjects', methods=['GET'])
@jwt_required()
def get_subjects():
    subjects = Subject.query.all()
    return jsonify([{"id": sub.id, "name": sub.name} for sub in subjects])


@user_bp.route('/quizzes/<int:subject_id>', methods=['GET'])
@jwt_required()
def get_quizzes(subject_id):
    quizzes = Quiz.query.join(Chapter).filter(
        Chapter.subject_id == subject_id).all()
    return jsonify([{"id": quiz.id, "date": quiz.date_of_quiz.strftime('%Y-%m-%d'), "duration": quiz.time_duration} for quiz in quizzes])

### 2️⃣ Fetch Quiz Questions ###


@user_bp.route('/quiz/<int:quiz_id>', methods=['GET'])
@jwt_required()
def get_quiz_questions(quiz_id):
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    return jsonify([{
        "id": q.id, "question": q.question_text,
        "options": [q.option1, q.option2, q.option3, q.option4]
    } for q in questions])

### 3️⃣ Submit Quiz Attempt ###


@user_bp.route('/quiz/attempt', methods=['POST'])
@jwt_required()
def submit_quiz_attempt():
    user_id = get_jwt_identity()
    data = request.json
    quiz_id = data.get('quiz_id')
    answers = data.get('answers')  # Format: {question_id: selected_option}

    if not quiz_id or not answers:
        return jsonify({"error": "Quiz ID and answers required"}), 400

    quiz_attempt = QuizAttempt(user_id=user_id, quiz_id=quiz_id,
                               start_time=datetime.utcnow(), end_time=datetime.utcnow())
    db.session.add(quiz_attempt)
    db.session.commit()

    correct_answers = 0
    total_questions = len(answers)

    for qid, selected_option in answers.items():
        question = Question.query.get(qid)
        if question and int(selected_option) == question.correct_option:
            correct_answers += 1

    score = Score(quiz_attempt_id=quiz_attempt.id, total_score=(
        correct_answers / total_questions) * 100)
    db.session.add(score)
    db.session.commit()

    return jsonify({"message": "Quiz submitted", "score": score.total_score})

### 4️⃣ Fetch User Quiz History ###


@user_bp.route('/history', methods=['GET'])
@jwt_required()
def get_user_history():
    user_id = get_jwt_identity()
    attempts = QuizAttempt.query.filter_by(user_id=user_id).all()

    history = [{
        "quiz_id": attempt.quiz_id,
        "start_time": attempt.start_time.strftime('%Y-%m-%d %H:%M'),
        "score": attempt.score.total_score if attempt.score else "N/A"
    } for attempt in attempts]

    return jsonify(history)

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (create_access_token, get_jwt_identity,
                                jwt_required)
from models import User, db

auth_bp = Blueprint('auth', __name__)

### ✅ User Registration ###


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"message": "User already exists"}), 400

    new_user = User(
        username=data['username'],
        full_name=data['full_name'],
        qualification=data.get('qualification'),
        dob=datetime.strptime(data.get('dob'), "%d/%m/%Y"),
        role=data.get('role', 'user')  # Default role is 'user'
    )
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


### ✅ User Login ###
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(
        identity={"id": user.id, "role": user.role})
    return jsonify(access_token=access_token), 200


### ✅ Admin-Only Role Check Decorator ###
def admin_required(fn):
    """Decorator to restrict access to admin-only routes."""
    from functools import wraps

    from flask_jwt_extended import get_jwt

    @wraps(fn)
    def wrapper(*args, **kwargs):
        jwt_data = get_jwt_identity()
        if jwt_data["role"] != "admin":
            return jsonify({"message": "Admins only!"}), 403
        return fn(*args, **kwargs)

    return wrapper


### ✅ Get Current User (Protected) ###
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    jwt_data = get_jwt_identity()
    user = User.query.get(jwt_data["id"])

    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role
    }), 200

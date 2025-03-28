from datetime import datetime, timezone
import json
from functools import wraps

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (create_access_token, get_jwt_identity,
                                jwt_required)

from app import cache, db
from models import User

auth_bp = Blueprint('auth', __name__)

### ✅ User Registration ###

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"message": "User already exists"}), 400

    new_user = User(
        email=data['email'],
        full_name=data['full_name'],
        qualification=data.get('qualification'),
        dob=datetime.strptime(data.get('dob'), "%d/%m/%Y") if data.get('dob') else None,
        role=data.get('role', 'user')  # Default role is 'user'
    )
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()

    # Clear any related caches
    cache.delete('all_subjects')  # Force reload of subject lists
    
    return jsonify({"message": "User registered successfully"}), 201


### ✅ User Login ###
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({"message": "Invalid credentials"}), 401

    # Update last login time
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()
    
    # Create access token
    access_token = create_access_token(identity=user.id)
    
    return jsonify(access_token=access_token), 200


### ✅ Admin-Only Role Check Decorator ###
def admin_required(fn):
    """Decorator to restrict access to admin-only routes."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        
        # Check database for admin role
        user = User.query.get(current_user_id)
        if not user or user.role != "admin":
            return jsonify({"message": "Admins only!"}), 403
            
        return fn(*args, **kwargs)
    return wrapper


### ✅ Get Current User (Protected) ###
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
@cache.memoize(timeout=300)  # Cache user profile for 5 minutes
def get_current_user():
    current_user_id = get_jwt_identity()
    
    # Get from database
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404
    
    # Prepare user data
    user_data = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "last_login": user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else None
    }

    return jsonify(user_data), 200


### ✅ Update User Profile ###
@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    data = request.get_json()
    
    # Update allowed fields
    if 'full_name' in data:
        user.full_name = data['full_name']
    if 'qualification' in data:
        user.qualification = data['qualification']
    if 'dob' in data and data['dob']:
        user.dob = datetime.strptime(data['dob'], "%d/%m/%Y")
        
    db.session.commit()
    
    # Clear user cache
    cache.delete_memoized(get_current_user, current_user_id)
    
    return jsonify({"message": "Profile updated successfully"}), 200

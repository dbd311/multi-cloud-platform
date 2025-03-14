from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    create_refresh_token,
    jwt_required,
)
from models import db, User, TokenBlocklist
import bcrypt
from datetime import datetime, timedelta, timezone

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username, password, role = data['username'], data['password'], data['role']
    
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    new_user = User(username=username, password_hash=password_hash, role=role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"status": "User registered"})

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()

    if user and bcrypt.checkpw(data['password'].encode('utf-8'), user.password_hash.encode('utf-8')):
        access_token = create_access_token(identity={"username": user.username, "role": user.role})
        return jsonify({
            "success": True,
            "access_token": access_token,
            "role": user.role
        })
    
    return jsonify({"error": "Invalid credentials"}), 401

# Helper function to add a token to the blocklist to invalidate the token on the server side (token blacklisting)
def add_token_to_blocklist(jti):
    blocked_token = TokenBlocklist(jti=jti, created_at=datetime.now(timezone.utc))
    db.session.add(blocked_token)
    db.session.commit()

@auth_bp.route('/logout', methods=['DELETE'])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]  # Get the unique identifier (JTI) of the token
    add_token_to_blocklist(jti)
    return jsonify({"status": "Logged out successfully"})

# Token blacklist check (callback for Flask-JWT-Extended)
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    token = TokenBlocklist.query.filter_by(jti=jti).first()
    return token is not None
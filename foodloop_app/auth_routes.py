# backend/foodloop_app/auth_routes.py
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_security.utils import hash_password, verify_password, login_user, logout_user
from flask_jwt_extended import create_access_token
from flask_security import roles_accepted, roles_required
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import jwt_required, get_jwt_identity

# Import db and user_datastore initialized in __init__.py
from foodloop_app import db, user_datastore

# Import models
from .models import User, Role

auth_bp = Blueprint("auth", __name__, url_prefix="/")


@auth_bp.route("/sign-up", methods=["POST"])
def sign_up():
    print(f"data: {request.get_json()}")
    print("Raw data:", request.data)
    data = request.get_json()
    if not data or not all(
        key in data
        for key in ["email", "password", "city", "pincode", "contact", "role"]
    ):
        return jsonify({"error": "Missing required fields"}), 402

    email = data["email"].strip()
    password = data["password"]
    city = data["city"].strip()
    pincode = data["pincode"].strip()
    contact = data["contact"].strip()
    role_name = data["role"].strip().capitalize()

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email address is already registered"}), 409

    print(f"Received role: {role_name}")
    valid_roles = ["Retailer", "Ngo", "Farmer", "Admin"]
    if role_name not in valid_roles:
        return jsonify({"error": f"Invalid role: {role_name}"}), 403

    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return jsonify({"error": f"Role '{role_name}' not found"}), 400

    try:
        user = User(
            email=email,
            password=hash_password(password),
            active=True,
            city=city,
            pincode=pincode,
            contact=contact,
            fs_uniquifier=str(uuid.uuid4()),
        )
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "User created successfully"}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"User creation failed: {e}, data received {request.get_json()}"
        )
        return (
            jsonify({"error": f"An error occurred during registration: {str(e)}"}),
            500,
        )


@auth_bp.route("/auth-login", methods=["POST"])
def login():
    print("logn route")
    print("Authorization header:", request.headers.get("Authorization"))

    data = request.get_json()
    if not data or not all(key in data for key in ["email", "password"]):
        return jsonify({"error": "Email and password are required"}), 402

    email = data["email"].strip()
    password = data["password"]

    user = User.query.filter_by(email=email).first()

    print("user exists")

    if user and verify_password(password, user.password):
        login_user(user)

        print("user logged in")
        access_token = create_access_token(identity=email)
        user_data = {
            "id": user.id,
            "email": user.email,
            "city": user.city,
            "pincode": user.pincode,
            "contact": user.contact,
            "roles": [role.name for role in user.roles],
        }
        return (
            jsonify(
                {
                    "message": "Login successful",
                    "token": access_token,
                    "user": user_data,
                }
            ),
            200,
        )
    else:
        return jsonify({"error": "Invalid email or password"}), 401


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200

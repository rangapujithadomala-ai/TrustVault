import re

from flask import Blueprint, request, jsonify
from sqlalchemy import func
from flask_login import login_user, logout_user

from extensions import db
from models.user import User

from security.password import (
    validate_password,
    hash_password,
    verify_password
)

from security.email_verification import (
    generate_verification_token,
    save_verification_token,
    verify_email_token
)

from security.email_service import send_email


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# --------------------------------------------------
# 1. USER REGISTRATION
# --------------------------------------------------

@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new Viewer account."""

    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    # Validate required fields
    if not all([name, email, password, confirm_password]):
        return jsonify({
            "error": "All fields are required."
        }), 400

    # Validate name
    if not re.fullmatch(r"[A-Za-z][A-Za-z\s'-]{1,99}", name):
        return jsonify({
            "error": "Please enter a valid name."
        }), 400

    # Validate email format
    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    if not re.fullmatch(email_pattern, email):
        return jsonify({
            "error": "Please enter a valid email address."
        }), 400

    # Check password strength
    is_valid, message = validate_password(password)

    if not is_valid:
        return jsonify({
            "error": message
        }), 400

    # Check password confirmation
    if password != confirm_password:
        return jsonify({
            "error": "Passwords do not match."
        }), 400

    # Check whether email already exists
    existing_user = User.query.filter(
        func.lower(User.email) == email
    ).first()

    if existing_user:
        return jsonify({
            "error": "An account with this email already exists."
        }), 409

    # Create Viewer account
    new_user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="viewer",
        is_active=True,
        email_verified=False
    )

    db.session.add(new_user)
    db.session.commit()

    # Generate email verification token
    token = generate_verification_token()

    # Save the hashed verification token
    save_verification_token(new_user.id, token)

    # Create verification link
    verification_link = (
        f"http://127.0.0.1:5000/auth/verify-email/{token}"
    )

    # Prepare verification email
    email_subject = "Verify your TrustVault account"

    email_body = f"""
Hello {new_user.name},

Thank you for registering with TrustVault!

Please click the link below to verify your email address:

{verification_link}

This verification link expires in 24 hours.

If you did not create this account, please ignore this email.

Regards,
TrustVault Team
"""

    # Send verification email
    send_email(
        new_user.email,
        email_subject,
        email_body
    )

    return jsonify({
        "message": "Registration successful. Please check your email to verify your account."
    }), 201


# --------------------------------------------------
# 2. USER LOGIN
# --------------------------------------------------

@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and start their session."""

    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required."
        }), 400

    # Find user by email
    user = User.query.filter(
        func.lower(User.email) == email
    ).first()

    # Verify email and password
    if user is None or not verify_password(
        user.password_hash, password
    ):
        return jsonify({
            "error": "Invalid email or password."
        }), 401

    # Check account status
    if not user.is_active:
        return jsonify({
            "error": "Your account is inactive."
        }), 403

    # Check email verification
    if not user.email_verified:
        return jsonify({
            "error": "Please verify your email before logging in."
        }), 403

    # Start login session
    login_user(user)

    # Redirect according to saved role
    if user.role == "admin":
        dashboard = "/admin/dashboard"

    elif user.role == "owner":
        dashboard = "/owner/dashboard"

    else:
        dashboard = "/viewer/dashboard"

    return jsonify({
        "message": "Login successful.",
        "redirect": dashboard
    }), 200


# --------------------------------------------------
# 3. EMAIL VERIFICATION
# --------------------------------------------------

@auth_bp.route("/verify-email/<token>", methods=["GET"])
def verify_email(token):
    """Verify a user's email address."""

    if verify_email_token(token):
        return jsonify({
            "message": "Email verified successfully. You can now log in."
        }), 200

    return jsonify({
        "error": "Invalid, expired, or already used verification link."
    }), 400

@auth_bp.route("/logout", methods=["POST"])
def logout():
    """End the current user's authenticated session."""

    logout_user()

    return jsonify({
        "message": "Logout successful."
    }), 200
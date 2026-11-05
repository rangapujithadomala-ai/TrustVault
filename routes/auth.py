
import re
from datetime import datetime, timezone

from flask import (
    Blueprint,
    request,
    jsonify,
    render_template
)

from sqlalchemy import func
from flask_login import login_user, logout_user

from extensions import db

from models.user import User
from models.email_verification_token import EmailVerificationToken

from security.password import (
    validate_password,
    hash_password,
    verify_password
)

from security.email_verification import (
    generate_verification_token,
    save_verification_token,
    verify_email_token,
    hash_verification_token
)

from security.email_service import send_email


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# --------------------------------------------------
# 1. VIEWER REGISTRATION
# --------------------------------------------------

@auth_bp.route("/register", methods=["POST"])
def register():

    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not all([name, email, password, confirm_password]):
        return jsonify({
            "error": "All fields are required."
        }), 400

    if not re.fullmatch(r"[A-Za-z][A-Za-z\s'-]{1,99}", name):
        return jsonify({
            "error": "Please enter a valid name."
        }), 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({
            "error": "Please enter a valid email address."
        }), 400

    is_valid, message = validate_password(password)

    if not is_valid:
        return jsonify({
            "error": message
        }), 400

    if password != confirm_password:
        return jsonify({
            "error": "Passwords do not match."
        }), 400

    existing_user = User.query.filter(
        func.lower(User.email) == email
    ).first()

    if existing_user:
        return jsonify({
            "error": "An account with this email already exists."
        }), 409

    new_user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="viewer",
        is_active=True,
        email_verified=False
    )

    try:

        db.session.add(new_user)
        db.session.commit()

        # Generate and save email verification token
        token = generate_verification_token()

        save_verification_token(new_user.id, token)

        verification_link = (
            f"{request.url_root.rstrip('/')}"
            f"/auth/verify-email/{token}"
        )

        email_body = f"""
Hello {new_user.name},

Thank you for registering with TrustVault!

Please verify your email address using this link:

{verification_link}

This link expires in 24 hours and can only be used once.

Regards,
TrustVault Team
"""

        send_email(
            new_user.email,
            "Verify your TrustVault account",
            email_body
        )

    except Exception:

        db.session.rollback()

        # Remove incomplete registration if email delivery fails
        try:

            if new_user.id:

                EmailVerificationToken.query.filter_by(
                    user_id=new_user.id
                ).delete(synchronize_session=False)

                saved_user = db.session.get(
                    User,
                    new_user.id
                )

                if saved_user:
                    db.session.delete(saved_user)

                db.session.commit()

        except Exception:

            db.session.rollback()

        return jsonify({
            "error": (
                "Registration or verification email delivery failed. "
                "Please try again."
            )
        }), 500

    return jsonify({
        "message": (
            "Registration successful. "
            "Please check your email to verify your account."
        )
    }), 201


# --------------------------------------------------
# 2. LOGIN
# --------------------------------------------------

@auth_bp.route("/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required."
        }), 400

    user = User.query.filter(
        func.lower(User.email) == email
    ).first()

    if user is None or not verify_password(
        user.password_hash, password
    ):
        return jsonify({
            "error": "Invalid email or password."
        }), 401

    if not user.is_active:
        return jsonify({
            "error": "Your account is inactive."
        }), 403

    if not user.email_verified:
        return jsonify({
            "error": "Please verify your email before logging in."
        }), 403

    login_user(user)

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
# 3. VIEWER EMAIL VERIFICATION
# --------------------------------------------------

@auth_bp.route("/verify-email/<token>", methods=["GET"])
def verify_email(token):

    if verify_email_token(token):

        return jsonify({
            "message": (
                "Email verified successfully. "
                "You can now log in."
            )
        }), 200

    return jsonify({
        "error": (
            "Invalid, expired, or already used verification link."
        )
    }), 400


# --------------------------------------------------
# 4. OWNER INVITATION AND PASSWORD SETUP
# --------------------------------------------------

@auth_bp.route(
    "/accept-owner-invitation/<token>",
    methods=["GET", "POST"]
)
def accept_owner_invitation(token):

    token_hash = hash_verification_token(token)

    verification_record = EmailVerificationToken.query.filter_by(
        token_hash=token_hash,
        used_at=None
    ).first()

    if verification_record is None:

        return (
            "This invitation link is invalid or has already been used.",
            400
        )

    expiry_time = verification_record.expires_at

    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(
            tzinfo=timezone.utc
        )

    if datetime.now(timezone.utc) >= expiry_time:

        return "This invitation link has expired.", 400

    owner = db.session.get(
        User,
        verification_record.user_id
    )

    if (
        owner is None
        or owner.role != "owner"
        or not owner.is_active
        or owner.email_verified
    ):

        return "This Owner invitation is no longer valid.", 400

    if request.method == "GET":

        return render_template(
            "owner-invitation.html",
            token=token
        )

    data = request.get_json(silent=True) or {}

    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not password or not confirm_password:

        return jsonify({
            "error": "Both password fields are required."
        }), 400

    is_valid, message = validate_password(password)

    if not is_valid:

        return jsonify({
            "error": message
        }), 400

    if password != confirm_password:

        return jsonify({
            "error": "Passwords do not match."
        }), 400

    try:

        # Set the password chosen by the invited Owner
        owner.password_hash = hash_password(password)

        # Verify Owner email after accepting invitation
        owner.email_verified = True

        # Make invitation single-use
        verification_record.used_at = datetime.now(timezone.utc)

        db.session.commit()

    except Exception:

        db.session.rollback()

        return jsonify({
            "error": (
                "Unable to activate your account. "
                "Please try again."
            )
        }), 500

    return jsonify({
        "message": (
            "Your Owner account is now verified. "
            "You can log in."
        ),
        "redirect": "/login.html"
    }), 200


# --------------------------------------------------
# 5. LOGOUT
# --------------------------------------------------

@auth_bp.route("/logout", methods=["POST"])
def logout():

    logout_user()

    return jsonify({
        "message": "Logout successful."
    }), 200

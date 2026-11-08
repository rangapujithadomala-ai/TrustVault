
import re
import hashlib
import secrets
from urllib.parse import urlsplit
from datetime import timedelta
from datetime import datetime, timezone
from flask import redirect

from flask import (
    Blueprint,
    session,
    request,
    jsonify,
    render_template,
    redirect,
    current_app
)

from sqlalchemy import func
from flask_login import login_user, logout_user, current_user

from extensions import db

from models.user import User
from models.email_verification_token import EmailVerificationToken
from models.password_reset_token import PasswordResetToken

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
from security.rate_limit import is_limited, record_failure, clear_attempts
from security.audit import append_audit


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# --------------------------------------------------
# 1. PUBLIC REGISTRATION DISABLED
# Viewer accounts can only be created through valid invitations.
# --------------------------------------------------

@auth_bp.route("/register", methods=["POST"])
def register():
    append_audit(
        None,
        "public_registration_attempt",
        "denied",
        details={"reason": "invitation_only_registration"}
    )
    db.session.commit()

    return jsonify(
        error="Public registration is disabled. A valid TrustVault invitation is required."
    ), 403
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

    throttle_key = f"{request.remote_addr or 'unknown'}:{email}"
    if is_limited(throttle_key):
        append_audit(None,"login_attempt","denied",details={"reason":"rate_limited","email_sha256":hashlib.sha256(email.encode("utf-8")).hexdigest()})
        db.session.commit()
        return jsonify({"error": "Too many login attempts. Please wait 15 minutes."}), 429

    user = User.query.filter(
        func.lower(User.email) == email
    ).first()

    if user is None or not verify_password(
        user.password_hash, password
    ):
        append_audit(None,"login_attempt","denied",target_user_id=user.id if user else None,details={"reason":"invalid_credentials","email_sha256":hashlib.sha256(email.encode("utf-8")).hexdigest()})
        db.session.commit()
        record_failure(throttle_key)
        return jsonify({"error": "Invalid email or password."}), 401

    if not user.is_active:
        append_audit(user.id,"login_attempt","denied",details={"reason":"account_inactive"}); db.session.commit()
        return jsonify({"error":"Your account is inactive."}),403

    if not user.email_verified:
        append_audit(user.id,"login_attempt","denied",details={"reason":"email_unverified"}); db.session.commit()
        return jsonify({"error":"Please verify your email before logging in."}),403

    clear_attempts(throttle_key)
    login_user(user, remember=False, fresh=True)
    session.permanent = True
    session["_trustvault_password_snapshot"] = hashlib.sha256(user.password_hash.encode("utf-8")).hexdigest()
    append_audit(user.id,"login","success",details={"role":user.role})
    db.session.commit()

    if user.role == "admin":
        dashboard = "/admin/dashboard"

    elif user.role == "owner":
        dashboard = "/owner/dashboard"

    else:
        dashboard = "/viewer/dashboard"

    # Return the recipient to the invitation they opened before login.
    invitation_next = session.pop(
        "_trustvault_invitation_next",
        None
    )

    if isinstance(invitation_next, str) and invitation_next:
        parsed_next = urlsplit(invitation_next)

        # Accept only safe, local application paths.
        if (
            invitation_next.startswith("/")
            and not invitation_next.startswith("//")
            and not parsed_next.scheme
            and not parsed_next.netloc
            and "\\" not in invitation_next
        ):
            dashboard = invitation_next

    return jsonify({
        "message": "Login successful.",
        "redirect": dashboard
    }), 200


# --------------------------------------------------
# 3. VIEWER EMAIL VERIFICATION
# --------------------------------------------------

@auth_bp.route("/verify-email/<token>", methods=["GET"])
def verify_email(token):

    token_hash=hash_verification_token(token)
    if verify_email_token(token):
        record=EmailVerificationToken.query.filter_by(token_hash=token_hash).first()
        append_audit(record.user_id if record else None,"email_verification","success",target_user_id=record.user_id if record else None)
        db.session.commit()
        return redirect("/email-verification.html?status=success", code=302)
    record=EmailVerificationToken.query.filter_by(token_hash=token_hash).first()
    append_audit(record.user_id if record else None,"email_verification_attempt","denied",target_user_id=record.user_id if record else None,details={"token_hash_prefix":token_hash[:12]})
    db.session.commit()
    return render_template("email-verification.html", verification_status="invalid"), 400


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
        record=EmailVerificationToken.query.filter_by(token_hash=token_hash).first()
        append_audit(record.user_id if record else None,"owner_invitation_accept_attempt","denied",target_user_id=record.user_id if record else None,details={"reason":"invalid_or_used"})
        db.session.commit()
        return ("This invitation link is invalid or has already been used.",400)

    expiry_time = verification_record.expires_at

    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(
            tzinfo=timezone.utc
        )

    if datetime.now(timezone.utc) >= expiry_time:
        append_audit(verification_record.user_id,"owner_invitation_accept_attempt","denied",target_user_id=verification_record.user_id,details={"reason":"expired"})
        db.session.commit()
        return "This invitation link has expired.",400

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
        append_audit(verification_record.user_id,"owner_invitation_accept_attempt","denied",target_user_id=verification_record.user_id,details={"reason":"account_state_invalid"})
        db.session.commit()
        return "This Owner invitation is no longer valid.",400

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
        append_audit(owner.id,"owner_invitation_accepted","success",target_user_id=owner.id)
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

    if current_user.is_authenticated:
        append_audit(current_user.id,"logout","success")
        db.session.commit()
    logout_user()
    session.pop("_trustvault_password_snapshot", None)
    return jsonify({
    "message": "Logged out successfully.",
    "redirect": "/login.html?logout=1"
}), 200


@auth_bp.route("/profile/update", methods=["POST"])
def update_authenticated_profile():
    from flask_login import login_required, current_user
    # Decorator is applied below as an explicit wrapper to keep the blueprint route registered.
    if not current_user.is_authenticated: return jsonify(error="Authentication required."), 401
    data=request.get_json(silent=True) or {}
    name=(data.get("name") or "").strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z\s'.-]{1,99}", name):
        return jsonify(error="Please enter a valid full name."),400
    before=current_user.name; current_user.name=name
    append_audit(current_user.id,"profile_update","success",details={"previous_name":before,"new_name":name})
    db.session.commit()
    return jsonify(message="Profile updated successfully.",name=current_user.name)

@auth_bp.route("/change-password", methods=["POST"])
def change_authenticated_password():
    from flask_login import current_user
    if not current_user.is_authenticated: return jsonify(error="Authentication required."),401
    data=request.get_json(silent=True) or {}
    old=data.get("current_password",""); new=data.get("new_password",""); confirm=data.get("confirm_password","")
    if not old or not new or not confirm: return jsonify(error="All password fields are required."),400
    if not verify_password(current_user.password_hash,old): return jsonify(error="Current password is incorrect."),403
    valid,message=validate_password(new)
    if not valid: return jsonify(error=message),400
    if new != confirm: return jsonify(error="New passwords do not match."),400
    if old == new: return jsonify(error="Choose a different new password."),400
    user=current_user
    user.password_hash=hash_password(new)
    append_audit(user.id,"password_change","success")
    db.session.commit()
    # Replace current session with a fresh authenticated session after credential change.
    logout_user(); login_user(user,remember=False,fresh=True)
    session["_trustvault_password_snapshot"] = hashlib.sha256(user.password_hash.encode("utf-8")).hexdigest()
    return jsonify(message="Password changed successfully.")


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data=request.get_json(silent=True) or {}
    email=(data.get("email") or "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email):
        return jsonify(error="Please enter a valid email address."),400
    throttle_key=f"password-reset:{request.remote_addr or 'unknown'}"
    if is_limited(throttle_key):
        # Generic response prevents account enumeration and reveals no reset state.
        return jsonify(message="If an active verified account exists, a reset link will be sent."),200
    user=User.query.filter(func.lower(User.email)==email,User.is_active.is_(True),User.email_verified.is_(True)).first()
    if user:
        now=datetime.now(timezone.utc)
        PasswordResetToken.query.filter_by(user_id=user.id,used_at=None).update({"used_at":now},synchronize_session=False)
        raw=secrets.token_urlsafe(32)
        record=PasswordResetToken(user_id=user.id,token_hash=hash_verification_token(raw),expires_at=now+timedelta(hours=1))
        db.session.add(record); db.session.commit()
        link=f"{request.url_root.rstrip('/')}/reset-password.html?token={raw}"
        try:
            send_email(user.email,"TrustVault Password Reset",f"Hello {user.name},\n\nUse this single-use link to reset your TrustVault password within one hour:\n{link}\n\nIf you did not request this, ignore this email.")
            append_audit(None,"password_reset_request","success",target_user_id=user.id,details={"delivery":"accepted_by_mail_transport"})
        except Exception:
            current_app.logger.exception("Password reset email delivery failed")
            append_audit(None,"password_reset_request","error",target_user_id=user.id,details={"delivery":"failed"})
        db.session.commit()
    else:
        append_audit(None,"password_reset_request","success",details={"eligible_account_found":False})
        db.session.commit()
    record_failure(throttle_key)
    return jsonify(message="If an active verified account exists, a reset link will be sent."),200

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data=request.get_json(silent=True) or {}
    token=(data.get("token") or "").strip(); password=data.get("password",""); confirm=data.get("confirm_password","")
    if not token or not password or not confirm: return jsonify(error="Reset token and both password fields are required."),400
    record=PasswordResetToken.query.filter_by(token_hash=hash_verification_token(token),used_at=None).first()
    if record is None: return jsonify(error="This password reset link is invalid or has already been used."),400
    expiry=record.expires_at
    if expiry.tzinfo is None: expiry=expiry.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc)>=expiry: return jsonify(error="This password reset link has expired."),400
    user=db.session.get(User,record.user_id)
    if user is None or not user.is_active or not user.email_verified: return jsonify(error="This password reset link is no longer valid."),400
    valid,message=validate_password(password)
    if not valid: return jsonify(error=message),400
    if password!=confirm: return jsonify(error="Passwords do not match."),400
    user.password_hash=hash_password(password); record.used_at=datetime.now(timezone.utc)
    append_audit(user.id,"password_reset","success",details={"reset_token_id":record.id})
    db.session.commit()
    return jsonify(message="Password reset successfully. You can now log in.",redirect="/login.html"),200


@auth_bp.route("/resend-verification", methods=["POST"])
def resend_verification():
    data=request.get_json(silent=True) or {}
    email=(data.get("email") or "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email):
        return jsonify(error="Please enter a valid email address."),400
    throttle_key=f"resend-verification:{request.remote_addr or 'unknown'}:{email}"
    generic="If the account is eligible, a verification email will be sent."
    if is_limited(throttle_key): return jsonify(message=generic),200
    user=User.query.filter(func.lower(User.email)==email,User.is_active.is_(True),User.email_verified.is_(False),User.role=="viewer").first()
    if user:
        now=datetime.now(timezone.utc)
        EmailVerificationToken.query.filter_by(user_id=user.id,used_at=None).update({"used_at":now},synchronize_session=False)
        token=generate_verification_token()
        record=EmailVerificationToken(user_id=user.id,token_hash=hash_verification_token(token),expires_at=now+timedelta(hours=24))
        db.session.add(record); db.session.commit()
        link=f"{request.url_root.rstrip('/')}/auth/verify-email/{token}"
        try:
            send_email(user.email,"Verify your TrustVault account",f"Hello {user.name},\n\nVerify your account with this single-use link (expires in 24 hours):\n{link}\n")
            append_audit(None,"verification_email_resend","success",target_user_id=user.id,details={"delivery":"accepted_by_mail_transport"})
        except Exception:
            current_app.logger.exception("Resend verification email failed")
            append_audit(None,"verification_email_resend","error",target_user_id=user.id,details={"delivery":"failed"})
        db.session.commit()
    else:
        append_audit(None,"verification_email_resend","success",details={"eligible_account_found":False})
        db.session.commit()
    record_failure(throttle_key)
    return jsonify(message=generic),200

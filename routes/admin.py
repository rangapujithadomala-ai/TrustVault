
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, abort, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models import User, Document, AuditLog, Notification
from models.email_verification_token import EmailVerificationToken

from security.password import hash_password
from security.email_verification import (
    generate_verification_token,
    hash_verification_token
)
from security.email_service import send_email


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
def admin_access_required():
    if getattr(current_user, "role", None) != "admin":
        abort(403)


@admin_bp.route("/dashboard")
def dashboard():
    total_viewers = User.query.filter_by(role="viewer").count()
    total_owners = User.query.filter_by(role="owner").count()
    total_documents = Document.query.count()
    total_audit_events = AuditLog.query.count()

    audit_records = (
        AuditLog.query
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )

    recent_activity = []

    for record in audit_records:
        actor = (
            User.query.filter_by(id=record.actor_id).first()
            if record.actor_id else None
        )

        document = (
            Document.query.filter_by(id=record.document_id).first()
            if record.document_id else None
        )

        recent_activity.append({
            "user": actor.name if actor else "System",
            "action": record.action or "Activity recorded",
            "outcome": record.outcome or "",
            "document": document.title if document else "—",
            "date": (
                record.created_at.strftime("%d %b %Y, %I:%M %p")
                if record.created_at else "—"
            )
        })

    return render_template(
        "admin-dashboard.html",
        total_viewers=total_viewers,
        total_owners=total_owners,
        total_documents=total_documents,
        total_audit_events=total_audit_events,
        recent_activity=recent_activity
    )


@admin_bp.route("/users")
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()

    return render_template(
        "admin-users.html",
        users=all_users,
        total_users=User.query.count(),
        total_admins=User.query.filter_by(role="admin").count(),
        total_viewers=User.query.filter_by(role="viewer").count(),
        total_owners=User.query.filter_by(role="owner").count()
    )


@admin_bp.route("/invite-owner", methods=["POST"])
def invite_owner():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()

    if not name or not email:
        return jsonify({
            "error": "Name and email address are required."
        }), 400

    if not re.fullmatch(r"[A-Za-z][A-Za-z\s'.-]{1,99}", name):
        return jsonify({
            "error": "Please enter a valid name."
        }), 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({
            "error": "Please enter a valid email address."
        }), 400

    existing_user = User.query.filter(
        func.lower(User.email) == email
    ).first()

    if existing_user:
        return jsonify({
            "error": "An account with this email address already exists."
        }), 409

    # The Owner creates their own password after opening the invitation.
    temporary_password = secrets.token_urlsafe(32)

    new_owner = User(
        name=name,
        email=email,
        password_hash=hash_password(temporary_password),
        role="owner",
        is_active=True,
        email_verified=False
    )

    token = generate_verification_token()

    try:
        db.session.add(new_owner)
        db.session.flush()

        token_record = EmailVerificationToken(
            user_id=new_owner.id,
            token_hash=hash_verification_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )

        db.session.add(token_record)
        db.session.commit()

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unable to create Owner invitation.")

        return jsonify({
            "error": "Unable to create the Owner invitation. Please try again."
        }), 500

    verification_link = (
        f"{request.url_root.rstrip('/')}"
        f"/auth/accept-owner-invitation/{token}"
    )

    email_subject = "TrustVault Owner Invitation"

    email_body = f"""
Hello {name},

You have been invited to join TrustVault as an Owner.

Please open the link below to create your password and activate your account:

{verification_link}

This invitation expires in 24 hours and can only be used once.

If you were not expecting this invitation, please ignore this email.

Regards,
TrustVault Team
"""

    try:
        send_email(email, email_subject, email_body)

    except Exception:
        current_app.logger.exception("Unable to send Owner invitation email.")

        # Remove the pending account and token so the Admin can retry.
        try:
            db.session.delete(token_record)
            db.session.delete(new_owner)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Unable to clean up failed Owner invitation."
            )

        return jsonify({
            "error": (
                "The invitation email could not be sent. "
                "Check your mail configuration and try again."
            )
        }), 502

    return jsonify({
        "message": f"Owner invitation sent successfully to {email}."
    }), 201


@admin_bp.route("/documents")
def documents():
    all_documents = (
        Document.query
        .filter_by(deleted_at=None)
        .order_by(Document.created_at.desc())
        .all()
    )

    return render_template(
        "admin-documents.html",
        documents=all_documents,
        total_documents=len(all_documents)
    )


@admin_bp.route("/audit-logs")
def audit_logs():
    logs = (
        AuditLog.query
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    return render_template(
        "admin-audit-logs.html",
        audit_logs=logs,
        logs=logs
    )


@admin_bp.route("/security-alerts")
def security_alerts():
    alerts = (
        AuditLog.query
        .filter(AuditLog.outcome.isnot(None))
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )

    return render_template(
        "admin-security-alerts.html",
        alerts=alerts
    )


@admin_bp.route("/notifications")
def notifications():
    user_notifications = (
        Notification.query
        .filter_by(recipient_user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    unread_count = sum(
        1 for notification in user_notifications
        if notification.read_at is None
    )

    return render_template(
        "admin-notifications.html",
        notifications=user_notifications,
        unread_count=unread_count
    )


@admin_bp.route("/settings")
def settings():
    return render_template("admin-settings.html")


@admin_bp.route("/profile")
def profile():
    return render_template(
        "admin-profile.html",
        user=current_user
    )

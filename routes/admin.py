
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, abort, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models import User, Document, AuditLog, Notification, Permission
from models.email_verification_token import EmailVerificationToken
from models.password_reset_token import PasswordResetToken

from security.notifications import notify_admins
from security.password import hash_password
from security.email_verification import (
    generate_verification_token,
    hash_verification_token
)
from security.email_service import send_email
from security.audit import append_audit, verify_audit_chain


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
def admin_access_required():
    if getattr(current_user, "role", None) != "admin":
        abort(403)


# ---------------------------------------------------------
# ADMIN DASHBOARD
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# MANAGE USERS
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# INVITE OWNER
# ---------------------------------------------------------

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
        current_app.logger.exception(
            "Unable to create Owner invitation."
        )

        return jsonify({
            "error": "Unable to create the Owner invitation. Please try again."
        }), 500

    verification_link = (
        f"{current_app.config['APP_BASE_URL']}"
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
        current_app.logger.exception(
            "Unable to send Owner invitation email."
        )

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

    # Record the successful invitation in the audit trail.
    append_audit(
        current_user.id,
        "owner_invitation_sent",
        "success",
        target_user_id=new_owner.id,
        details={"recipient_email": email}
    )

    # Notify all active Admins.
    notify_admins(
        notification_type="owner_invitation_sent",
        message=f"An Owner invitation was successfully sent to {email}."
    )

    db.session.commit()

    return jsonify({
        "message": f"Owner invitation sent successfully to {email}."
    }), 201


# ---------------------------------------------------------
# MANAGE DOCUMENTS
# ---------------------------------------------------------

@admin_bp.route("/documents")
def documents():
    all_documents = (
        Document.query
        .filter_by(deleted_at=None)
        .order_by(Document.created_at.desc())
        .all()
    )

    owner_names = {
        user.id: user.name
        for user in User.query.filter(User.role == "owner").all()
    }

    return render_template(
        "admin-documents.html",
        documents=all_documents,
        owner_names=owner_names,
        total_documents=len(all_documents)
    )


# ---------------------------------------------------------
# AUDIT LOGS
# ---------------------------------------------------------

@admin_bp.route("/audit-logs")
def audit_logs():
    logs = (
        AuditLog.query
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    all_users = User.query.all()
    actor_names = {u.id: u.name for u in all_users}
    doc_titles = {
        d.id: d.title
        for d in Document.query.all()
    }

    return render_template(
        "admin-audit-logs.html",
        audit_logs=logs,
        logs=logs,
        actor_names=actor_names,
        doc_titles=doc_titles
    )


# ---------------------------------------------------------
# SECURITY ALERTS
# ---------------------------------------------------------

@admin_bp.route("/security-alerts")
def security_alerts():
    alerts = (
        AuditLog.query
        .filter(AuditLog.outcome.in_(["denied", "error", "failure"]))
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )

    actor_names = {
        u.id: u.name
        for u in User.query.all()
    }

    severity_by_id = {
        a.id: (
            "High"
            if a.outcome in ("error", "failure")
            else "Medium"
        )
        for a in alerts
    }

    high_count = sum(
        1 for a in alerts
        if severity_by_id[a.id] == "High"
    )

    return render_template(
        "admin-security-alerts.html",
        alerts=alerts,
        actor_names=actor_names,
        severity_by_id=severity_by_id,
        high_count=high_count,
        unresolved_count=len(alerts)
    )


# ---------------------------------------------------------
# ADMIN NOTIFICATION MONITORING
# ---------------------------------------------------------

@admin_bp.route("/notifications")
def notifications():
    # Admin monitoring view: notification metadata for all recipients.
    # Protected document contents are not exposed here.

    user_notifications = (
        Notification.query
        .order_by(Notification.created_at.desc())
        .limit(500)
        .all()
    )

    unread_count = sum(
        1 for notification in user_notifications
        if notification.read_at is None
    )

    recipient_names = {
        user.id: user.name
        for user in User.query.all()
    }

    return render_template(
        "admin-notifications.html",
        notifications=user_notifications,
        unread_count=unread_count,
        recipient_names=recipient_names
    )


# ---------------------------------------------------------
# ADMIN SETTINGS
# ---------------------------------------------------------

@admin_bp.route("/settings")
def settings():
    return render_template("admin-settings.html")


# ---------------------------------------------------------
# ADMIN PROFILE
# ---------------------------------------------------------

@admin_bp.route("/profile")
def profile():
    return render_template(
        "admin-profile.html",
        user=current_user
    )


# ---------------------------------------------------------
# DEACTIVATE USER
# ---------------------------------------------------------

@admin_bp.route("/users/<user_id>/deactivate", methods=["POST"])
def deactivate_user(user_id):
    target = db.session.get(User, user_id)

    if target is None:
        abort(404)

    if target.role == "admin" or target.id == current_user.id:
        return jsonify(
            error="Administrators cannot deactivate this account."
        ), 403

    if not target.is_active:
        return jsonify(
            message="Account is already inactive."
        ), 200

    if (
        target.role == "owner"
        and Document.query.filter_by(owner_id=target.id).count()
    ):
        return jsonify(
            error=(
                "Transfer the Owner's active documents to another "
                "active Owner before deactivation."
            ),
            needs_transfer=True
        ), 409

    target.is_active = False

    # Rotate the stored password hash to invalidate existing sessions.
    target.password_hash = hash_password(
        secrets.token_urlsafe(48)
    )

    PasswordResetToken.query.filter_by(
        user_id=target.id,
        used_at=None
    ).update(
        {"used_at": datetime.now(timezone.utc)},
        synchronize_session=False
    )

    now = datetime.now(timezone.utc)

    # Revoke every active document permission held by this person.
    grants = Permission.query.filter_by(
        user_id=target.id,
        revoked_at=None
    ).all()

    for grant in grants:
        grant.revoked_at = now

        append_audit(
            current_user.id,
            "offboarding_permission_revoke",
            "success",
            document_id=grant.document_id,
            target_user_id=target.id,
            details={"permission_id": grant.id}
        )

    append_audit(
        current_user.id,
        "user_deactivate",
        "success",
        target_user_id=target.id,
        details={
            "email": target.email,
            "revoked_grants": len(grants)
        }
    )

    db.session.commit()

    return jsonify(
        message="Account deactivated and document grants revoked."
    )


# ---------------------------------------------------------
# ACTIVATE USER
# ---------------------------------------------------------

@admin_bp.route("/users/<user_id>/activate", methods=["POST"])
def activate_user(user_id):
    target = db.session.get(User, user_id)

    if target is None:
        abort(404)

    if target.email_verified is False:
        return jsonify(
            error="Account email must be verified before activation."
        ), 400

    target.is_active = True

    append_audit(
        current_user.id,
        "user_activate",
        "success",
        target_user_id=target.id
    )

    db.session.commit()

    return jsonify(message="Account activated.")


# ---------------------------------------------------------
# AUDIT INTEGRITY CHECK
# ---------------------------------------------------------

@admin_bp.route("/audit-integrity", methods=["GET"])
def audit_integrity():
    valid, failed_id = verify_audit_chain()

    return jsonify(
        valid=valid,
        failed_event_id=failed_id,
        message=(
            "Audit chain verified."
            if valid
            else "Audit chain integrity failure."
        )
    ), (200 if valid else 409)


# ---------------------------------------------------------
# TRANSFER OWNER DOCUMENTS
# ---------------------------------------------------------

@admin_bp.route(
    "/users/<user_id>/transfer-documents",
    methods=["POST"]
)
def transfer_owner_documents(user_id):
    former_owner = db.session.get(User, user_id)

    data = request.get_json(silent=True) or {}
    new_owner = db.session.get(User, data.get("new_owner_id"))

    if former_owner is None or former_owner.role != "owner":
        abort(404)

    if (
        new_owner is None
        or new_owner.role != "owner"
        or not new_owner.is_active
        or not new_owner.email_verified
    ):
        return jsonify(
            error="Select an active, verified Owner."
        ), 400

    docs = Document.query.filter_by(
        owner_id=former_owner.id
    ).all()

    for doc in docs:
        doc.owner_id = new_owner.id

        append_audit(
            current_user.id,
            "document_ownership_transfer",
            "success",
            document_id=doc.id,
            target_user_id=new_owner.id,
            details={"previous_owner_id": former_owner.id}
        )

        db.session.add(
            Notification(
                recipient_user_id=new_owner.id,
                notification_type="ownership_transfer",
                message=(
                    f"Document '{doc.title}' was transferred "
                    "to you by an administrator."
                ),
                related_document_id=doc.id
            )
        )

    db.session.commit()

    return jsonify(
        message=f"Transferred {len(docs)} document(s).",
        transferred=len(docs)
    )


# ---------------------------------------------------------
# RESEND OWNER INVITATION
# ---------------------------------------------------------

@admin_bp.route(
    "/users/<user_id>/resend-invitation",
    methods=["POST"]
)
def resend_owner_invitation(user_id):
    target = db.session.get(User, user_id)

    if (
        target is None
        or target.role != "owner"
        or target.email_verified
    ):
        return jsonify(
            error="Only a pending Owner invitation can be resent."
        ), 400

    now = datetime.now(timezone.utc)

    EmailVerificationToken.query.filter_by(
        user_id=target.id,
        used_at=None
    ).update(
        {"used_at": now},
        synchronize_session=False
    )

    target.is_active = True

    token = generate_verification_token()

    token_record = EmailVerificationToken(
        user_id=target.id,
        token_hash=hash_verification_token(token),
        expires_at=now + timedelta(hours=24)
    )

    db.session.add(token_record)
    db.session.commit()

    link = (
        f"{current_app.config['APP_BASE_URL']}"
        f"/auth/accept-owner-invitation/{token}"
    )

    body = f"""
Hello {target.name},

Your TrustVault Owner invitation has been resent.

Create your password using this single-use link within 24 hours:

{link}
"""

    try:
        send_email(
            target.email,
            "TrustVault Owner Invitation (Resent)",
            body
        )

        append_audit(
            current_user.id,
            "owner_invitation_resent",
            "success",
            target_user_id=target.id,
            details={"recipient_email": target.email}
        )

        db.session.commit()

    except Exception:
        current_app.logger.exception(
            "Owner invitation resend failed"
        )

        token_record.used_at = datetime.now(timezone.utc)

        append_audit(
            current_user.id,
            "owner_invitation_resent",
            "error",
            target_user_id=target.id,
            details={"mail_delivery": "failed"}
        )

        db.session.commit()

        return jsonify(
            error=(
                "Invitation email could not be sent. "
                "Check mail configuration and retry."
            )
        ), 502

    return jsonify(message="Owner invitation resent."), 200


# ---------------------------------------------------------
# RESEND VIEWER EMAIL VERIFICATION
# ---------------------------------------------------------

@admin_bp.route(
    "/users/<user_id>/resend-verification",
    methods=["POST"]
)
def resend_viewer_verification(user_id):
    target = db.session.get(User, user_id)

    if (
        target is None
        or target.role != "viewer"
        or target.email_verified
    ):
        return jsonify(
            error=(
                "Only an unverified Viewer account can receive "
                "a new verification email."
            )
        ), 400

    now = datetime.now(timezone.utc)

    EmailVerificationToken.query.filter_by(
        user_id=target.id,
        used_at=None
    ).update(
        {"used_at": now},
        synchronize_session=False
    )

    target.is_active = True

    token = generate_verification_token()

    token_record = EmailVerificationToken(
        user_id=target.id,
        token_hash=hash_verification_token(token),
        expires_at=now + timedelta(hours=24)
    )

    db.session.add(token_record)
    db.session.commit()

    link = (
        f"{current_app.config['APP_BASE_URL']}"
        f"/auth/verify-email/{token}"
    )

    body = f"""
Hello {target.name},

Verify your TrustVault account with this single-use link within 24 hours:

{link}
"""

    try:
        send_email(
            target.email,
            "TrustVault Email Verification (Resent)",
            body
        )

        append_audit(
            current_user.id,
            "viewer_verification_resent",
            "success",
            target_user_id=target.id,
            details={"recipient_email": target.email}
        )

        db.session.commit()

    except Exception:
        current_app.logger.exception(
            "Viewer verification resend failed"
        )

        token_record.used_at = datetime.now(timezone.utc)

        append_audit(
            current_user.id,
            "viewer_verification_resent",
            "error",
            target_user_id=target.id,
            details={"mail_delivery": "failed"}
        )

        db.session.commit()

        return jsonify(
            error=(
                "Verification email could not be sent. "
                "Check mail configuration and retry."
            )
        ), 502

    return jsonify(
        message="Verification email sent successfully."
    ), 200

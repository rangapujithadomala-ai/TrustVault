
import re

from flask import Blueprint, render_template, abort, request, jsonify
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf

from extensions import db
from models import Document, Permission, AuditLog, Notification, User


owner_bp = Blueprint("owner", __name__, url_prefix="/owner")


@owner_bp.before_request
@login_required
def owner_access_required():
    if getattr(current_user, "role", None) != "owner":
        abort(403)


# --------------------------------------------------
# 1. OWNER DASHBOARD
# --------------------------------------------------

@owner_bp.route("/dashboard")
def dashboard():
    documents = (
        Document.query
        .filter_by(owner_id=current_user.id, deleted_at=None)
        .order_by(Document.created_at.desc())
        .all()
    )

    shared_permissions = (
        Permission.query
        .join(Document, Permission.document_id == Document.id)
        .filter(
            Document.owner_id == current_user.id,
            Permission.revoked_at.is_(None)
        )
        .all()
    )

    total_shared = len({
        permission.document_id
        for permission in shared_permissions
    })

    edit_access_count = sum(
        1 for permission in shared_permissions
        if permission.permission_type == "edit"
    )

    recent_activities = (
        AuditLog.query
        .filter_by(actor_id=current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "owner-dashboard.html",
        documents=documents,
        total_documents=len(documents),
        total_shared=total_shared,
        shared_permissions=shared_permissions,
        edit_access_count=edit_access_count,
        recent_activities=recent_activities
    )


# --------------------------------------------------
# 2. OWNER ACTIVITY
# --------------------------------------------------

@owner_bp.route("/activity")
def activity():
    activities = (
        AuditLog.query
        .filter_by(actor_id=current_user.id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    return render_template(
        "owner-activity.html",
        activities=activities,
        audit_logs=activities
    )


# --------------------------------------------------
# 3. OWNER SHARED DOCUMENTS
# --------------------------------------------------

@owner_bp.route("/shared-documents")
def shared_documents():
    permissions = (
        Permission.query
        .join(Document, Permission.document_id == Document.id)
        .filter(
            Document.owner_id == current_user.id,
            Permission.revoked_at.is_(None),
            Document.deleted_at.is_(None)
        )
        .order_by(Permission.granted_at.desc())
        .all()
    )

    shared_items = []

    for permission in permissions:
        document = Document.query.get(permission.document_id)
        recipient = User.query.get(permission.user_id)

        if document and recipient:
            shared_items.append({
                "permission": permission,
                "document": document,
                "recipient": recipient
            })

    return render_template(
        "owner-shared-documents.html",
        permissions=permissions,
        shared_documents=permissions,
        shared_items=shared_items
    )


# --------------------------------------------------
# 4. OWNER PROFILE
# --------------------------------------------------

@owner_bp.route("/profile")
def profile():
    return render_template(
        "owner-profile.html",
        user=current_user,
        csrf_token=generate_csrf()
    )


@owner_bp.route("/profile/update", methods=["POST"])
def update_profile():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()

    if not name:
        return jsonify({
            "error": "Full name is required."
        }), 400

    if not re.fullmatch(r"[A-Za-z][A-Za-z\s'.-]{1,99}", name):
        return jsonify({
            "error": "Please enter a valid full name."
        }), 400

    current_user.name = name

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Unable to update your profile. Please try again."
        }), 500

    return jsonify({
        "message": "Your profile has been updated successfully.",
        "name": current_user.name
    }), 200


# --------------------------------------------------
# 5. OWNER SETTINGS
# --------------------------------------------------

@owner_bp.route("/settings")
def settings():
    return render_template("owner-settings.html")

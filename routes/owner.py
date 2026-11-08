
import re

from flask import Blueprint, render_template, abort, request, jsonify
from flask_login import login_required, current_user
from security.audit import append_audit

from extensions import db
from models import Document, Permission, AuditLog, Notification, User, StarredDocument
from security.authorization import can_access_document


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
            Document.deleted_at.is_(None),
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

    owned_ids = [document.id for document in documents]

    recent_activities = (
        AuditLog.query
        .filter(AuditLog.document_id.in_(owned_ids))
        .order_by(AuditLog.created_at.desc())
        .limit(5)
        .all()
    ) if owned_ids else []

    return render_template(
        "owner-dashboard.html",
        documents=documents,
        total_documents=len(documents),
        total_shared=total_shared,
        shared_permissions=shared_permissions,
        edit_access_count=edit_access_count,
        recent_activities=recent_activities,
        actor_names={u.id: u.name for u in User.query.all()},
        doc_titles={d.id: d.title for d in documents}
    )


# --------------------------------------------------
# 2. OWNER DOCUMENTS AND ACTIVITY
# --------------------------------------------------

@owner_bp.route("/my-documents")
def my_documents():
    documents = (
        Document.query
        .filter_by(owner_id=current_user.id, deleted_at=None)
        .order_by(Document.created_at.desc())
        .all()
    )

    grants = (
        Permission.query
        .filter(
            Permission.document_id.in_([d.id for d in documents]),
            Permission.revoked_at.is_(None)
        )
        .all()
    ) if documents else []

    shared_counts = {}

    for grant in grants:
        shared_counts[grant.document_id] = (
            shared_counts.get(grant.document_id, 0) + 1
        )

    return render_template(
        "my-documents.html",
        documents=documents,
        shared_counts=shared_counts
    )


@owner_bp.route("/upload-document")
def upload_page():
    return render_template("upload-document.html")


@owner_bp.route("/activity")
def activity():
    owned_ids = [
        row.id
        for row in Document.query.filter_by(
            owner_id=current_user.id
        ).all()
    ]

    activities = (
        AuditLog.query.filter(
            (AuditLog.actor_id == current_user.id)
            | AuditLog.document_id.in_(owned_ids)
        )
        .order_by(AuditLog.created_at.desc())
        .all()
        if owned_ids
        else AuditLog.query.filter_by(
            actor_id=current_user.id
        ).order_by(AuditLog.created_at.desc()).all()
    )

    actor_names = {
        u.id: u.name for u in User.query.all()
    }

    doc_titles = {
        d.id: d.title for d in Document.query.all()
    }

    return render_template(
        "owner-activity.html",
        activities=activities,
        audit_logs=activities,
        actor_names=actor_names,
        doc_titles=doc_titles
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

@owner_bp.route("/invite")
def invite_page():
    documents = (
        Document.query
        .filter_by(owner_id=current_user.id, deleted_at=None)
        .order_by(Document.created_at.desc())
        .all()
    )

    return render_template(
        "owner-invite.html",
        documents=documents
    )
# --------------------------------------------------
# 4. OWNER PROFILE
# --------------------------------------------------

@owner_bp.route("/profile")
def profile():
    return render_template(
        "owner-profile.html",
        user=current_user
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


# --------------------------------------------------
# 6. STARRED DOCUMENTS
# --------------------------------------------------

@owner_bp.route("/starred")
def starred():
    ids = [
        row.document_id
        for row in StarredDocument.query.filter_by(
            user_id=current_user.id
        ).all()
    ]

    documents = (
        Document.query
        .filter(
            Document.id.in_(ids),
            Document.deleted_at.is_(None)
        )
        .all()
        if ids else []
    )

    documents = [
        doc for doc in documents
        if can_access_document(doc, "read")
    ]

    owners = {
        u.id: u.name
        for u in User.query.filter(User.role == "owner").all()
    }

    active_grants = Permission.query.filter_by(
        user_id=current_user.id,
        revoked_at=None
    ).all()

    grants = {
        p.document_id: p.permission_type
        for p in active_grants
    }

    grant_dates = {
        p.document_id: p.granted_at
        for p in active_grants
    }

    return render_template(
        "owner-starred.html",
        documents=documents,
        owners=owners,
        grants=grants,
        grant_dates=grant_dates
    )


# --------------------------------------------------
# 7. ARCHIVED DOCUMENTS
# --------------------------------------------------

@owner_bp.route("/archived")
def archived_documents():
    documents = (
        Document.query
        .filter_by(owner_id=current_user.id)
        .filter(Document.deleted_at.isnot(None))
        .order_by(Document.updated_at.desc())
        .all()
    )

    return render_template(
        "owner-archived.html",
        documents=documents,
        shared_counts={}
    )


# --------------------------------------------------
# 8. RECEIVED DOCUMENTS
# --------------------------------------------------

@owner_bp.route("/received-documents")
def received_documents():
    documents = (
        Document.query
        .join(Permission, Permission.document_id == Document.id)
        .join(User, User.id == Document.owner_id)
        .filter(
            Document.owner_id != current_user.id,
            Document.deleted_at.is_(None),
            User.is_active.is_(True),
            Permission.user_id == current_user.id,
            Permission.revoked_at.is_(None)
        )
        .order_by(Permission.granted_at.desc())
        .all()
    )

    owners = {
        u.id: u.name
        for u in User.query.filter(User.role == "owner").all()
    }

    active_grants = Permission.query.filter_by(
        user_id=current_user.id,
        revoked_at=None
    ).all()

    grants = {
        p.document_id: p.permission_type
        for p in active_grants
    }

    grant_dates = {
        p.document_id: p.granted_at
        for p in active_grants
    }

    return render_template(
        "owner-received-documents.html",
        documents=documents,
        owners=owners,
        grants=grants,
        grant_dates=grant_dates
    )

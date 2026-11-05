from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from models import Document, Permission, AuditLog, Notification


viewer_bp = Blueprint("viewer", __name__, url_prefix="/viewer")


@viewer_bp.before_request
@login_required
def viewer_access_required():
    if getattr(current_user, "role", None) != "viewer":
        abort(403)


def get_accessible_documents():
    return (
        Document.query
        .join(Permission, Permission.document_id == Document.id)
        .filter(
            Permission.user_id == current_user.id,
            Permission.revoked_at.is_(None),
            Document.deleted_at.is_(None)
        )
        .order_by(Document.created_at.desc())
        .all()
    )


@viewer_bp.route("/dashboard")
def dashboard():
    documents = get_accessible_documents()

    return render_template(
        "dashboard.html",
        documents=documents,
        total_documents=len(documents)
    )


@viewer_bp.route("/my-documents")
def my_documents():
    documents = get_accessible_documents()

    return render_template(
        "my-documents.html",
        documents=documents
    )


@viewer_bp.route("/shared-with-me")
def shared_with_me():
    documents = get_accessible_documents()

    return render_template(
        "shared-with-me.html",
        documents=documents
    )


@viewer_bp.route("/activity")
def activity():
    activities = (
        AuditLog.query
        .filter_by(actor_id=current_user.id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    return render_template(
        "activity.html",
        activities=activities,
        audit_logs=activities
    )


@viewer_bp.route("/profile")
def profile():
    return render_template("profile.html")


@viewer_bp.route("/settings")
def settings():
    return render_template("settings.html")



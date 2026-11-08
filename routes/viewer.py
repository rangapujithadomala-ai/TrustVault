from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from models import Document, Permission, AuditLog, Notification, User, StarredDocument
from security.authorization import can_access_document


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
        .join(User, User.id == Document.owner_id)
        .filter(
            User.is_active.is_(True),
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

    edit_count = sum(1 for document in documents if Permission.query.filter_by(document_id=document.id,user_id=current_user.id,permission_type="edit",revoked_at=None).first())
    viewed_ids = {row.document_id for row in AuditLog.query.filter_by(actor_id=current_user.id, outcome="success").filter(AuditLog.action.in_(["document_view", "document_download"])).all() if row.document_id}
    recent_activity = AuditLog.query.filter_by(actor_id=current_user.id).order_by(AuditLog.created_at.desc()).limit(5).all()
    doc_titles = {doc.id: doc.title for doc in Document.query.filter(Document.id.in_([row.document_id for row in recent_activity if row.document_id])).all()}
    owners = {u.id: u.name for u in User.query.filter(User.role == "owner").all()}
    active_grants=Permission.query.filter_by(user_id=current_user.id,revoked_at=None).all()
    grants={p.document_id:p.permission_type for p in active_grants}
    grant_dates={p.document_id:p.granted_at for p in active_grants}
    return render_template("dashboard.html",documents=documents,total_documents=len(documents),edit_count=edit_count,viewed_count=len(viewed_ids),recent_activity=recent_activity,doc_titles=doc_titles,owners=owners,grants=grants,grant_dates=grant_dates)


@viewer_bp.route("/my-documents")
def my_documents():
    docs=get_accessible_documents(); active_grants=Permission.query.filter_by(user_id=current_user.id,revoked_at=None).all()
    return render_template("shared-with-me.html",documents=docs,owners={u.id:u.name for u in User.query.filter(User.role=="owner").all()},grants={p.document_id:p.permission_type for p in active_grants},grant_dates={p.document_id:p.granted_at for p in active_grants})


@viewer_bp.route("/shared-with-me")
def shared_with_me():
    documents = get_accessible_documents()

    owners = {u.id: u.name for u in User.query.filter(User.role == "owner").all()}
    active_grants=Permission.query.filter_by(user_id=current_user.id,revoked_at=None).all()
    grants={p.document_id:p.permission_type for p in active_grants}
    grant_dates={p.document_id:p.granted_at for p in active_grants}
    return render_template("shared-with-me.html",documents=documents,owners=owners,grants=grants,grant_dates=grant_dates)


@viewer_bp.route("/activity")
def activity():
    activities = (
        AuditLog.query
        .filter_by(actor_id=current_user.id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    doc_titles = {d.id:d.title for d in Document.query.filter(Document.id.in_([a.document_id for a in activities if a.document_id])).all()}
    return render_template("activity.html", activities=activities, audit_logs=activities, doc_titles=doc_titles)


@viewer_bp.route("/profile")
def profile():
    return render_template("profile.html", user=current_user)


@viewer_bp.route("/settings")
def settings():
    return render_template("settings.html")




@viewer_bp.route("/starred")
def starred():
    ids=[row.document_id for row in StarredDocument.query.filter_by(user_id=current_user.id).all()]
    documents=Document.query.filter(Document.id.in_(ids),Document.deleted_at.is_(None)).all() if ids else []
    documents=[doc for doc in documents if can_access_document(doc,"read")]
    owners={u.id:u.name for u in User.query.filter(User.role=="owner").all()}
    active_grants=Permission.query.filter_by(user_id=current_user.id,revoked_at=None).all()
    grants={p.document_id:p.permission_type for p in active_grants}
    grant_dates={p.document_id:p.granted_at for p in active_grants}
    return render_template("viewer-starred.html",documents=documents,owners=owners,grants=grants,grant_dates=grant_dates)


"""Document operations. All file bytes remain outside the public frontend directory."""

import hashlib
import uuid
from io import BytesIO
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify, abort, current_app, send_file
from flask_login import current_user
from werkzeug.utils import secure_filename

from models import (
    Document,
    Permission,
    User,
    Notification,
    DocumentVersion,
    StarredDocument,
)
from extensions import db
from security.authorization import can_access_document
from security.audit import append_audit
from storage_service import upload_file, download_file, delete_file


documents_bp = Blueprint("documents", __name__, url_prefix="/documents")

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "ppt", "pptx", "txt",
    "png", "jpg", "jpeg", "xlsx", "csv"
}

MAX_BYTES = 15 * 1024 * 1024


@documents_bp.before_request
def active_login_required():
    if not current_user.is_authenticated:
        append_audit(
            None,
            "anonymous_document_attempt",
            "denied",
            details={"method": request.method, "path": request.path}
        )
        db.session.commit()
        abort(401)

    if not current_user.is_active:
        append_audit(
            current_user.id,
            "inactive_document_attempt",
            "denied",
            details={"method": request.method, "path": request.path}
        )
        db.session.commit()
        abort(403)


def _get_doc(doc_id, include_deleted=False):
    doc = db.session.get(Document, doc_id)

    if not doc or (doc.deleted_at and not include_deleted):
        append_audit(
            current_user.id,
            "document_lookup",
            "denied",
            details={"document_id": doc_id}
        )
        db.session.commit()
        abort(404)

    return doc


def _deny(doc, action):
    append_audit(
        current_user.id,
        action,
        "denied",
        document_id=doc.id
    )
    db.session.commit()
    abort(403)


def _permitted(doc, permission="read"):
    if not can_access_document(doc, permission):
        _deny(doc, "document_" + permission)


def _delete_cloud_file(storage_key):
    """Best-effort cleanup when a database operation fails."""
    try:
        delete_file(storage_key)
    except Exception:
        current_app.logger.exception(
            "Unable to clean up Supabase file: %s",
            storage_key
        )


def _content_error(ext, content):
    if ext == "pdf" and not content.startswith(b"%PDF-"):
        return "Invalid PDF content."

    if ext == "png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "Invalid PNG content."

    if ext in {"jpg", "jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        return "Invalid JPEG content."

    return None


def _notify(user_id, kind, message, doc_id):
    db.session.add(
        Notification(
            recipient_user_id=user_id,
            notification_type=kind,
            message=message,
            related_document_id=doc_id
        )
    )


@documents_bp.route("/", methods=["GET"])
def search_documents():
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    owner_name = (request.args.get("owner") or "").strip()
    start = request.args.get("start")
    end = request.args.get("end")

    query = Document.query.filter(Document.deleted_at.is_(None))

    if current_user.role == "owner":
        query = query.filter(Document.owner_id == current_user.id)

    elif current_user.role == "viewer":
        query = (
            query.join(Permission, Permission.document_id == Document.id)
            .join(User, User.id == Document.owner_id)
            .filter(
                User.is_active.is_(True),
                Permission.user_id == current_user.id,
                Permission.revoked_at.is_(None)
            )
        )

    else:
        append_audit(
            current_user.id,
            "document_search",
            "denied",
            details={"role": current_user.role}
        )
        db.session.commit()
        abort(403)

    if q:
        query = query.filter(Document.title.ilike(f"%{q}%"))

    if category:
        query = query.filter(Document.category.ilike(f"%{category}%"))

    if owner_name:
        if current_user.role == "owner":
            query = query.join(User, User.id == Document.owner_id)

        query = query.filter(User.name.ilike(f"%{owner_name}%"))

    if start:
        try:
            start_dt = datetime.fromisoformat(start)
            start_dt = (
                start_dt.replace(tzinfo=timezone.utc)
                if start_dt.tzinfo is None
                else start_dt.astimezone(timezone.utc)
            )
            query = query.filter(Document.created_at >= start_dt)

        except ValueError:
            return jsonify(error="Invalid start date."), 400

    if end:
        try:
            end_dt = datetime.fromisoformat(end)

            if len(end) == 10:
                end_dt = end_dt + timedelta(days=1) - timedelta(microseconds=1)

            end_dt = (
                end_dt.replace(tzinfo=timezone.utc)
                if end_dt.tzinfo is None
                else end_dt.astimezone(timezone.utc)
            )

            query = query.filter(Document.created_at <= end_dt)

        except ValueError:
            return jsonify(error="Invalid end date."), 400

    docs = query.order_by(
        Document.created_at.desc()
    ).distinct().limit(200).all()

    return jsonify(
        documents=[
            {
                "id": d.id,
                "title": d.title,
                "description": d.description,
                "category": d.category,
                "owner_id": d.owner_id,
                "filename": d.original_filename,
                "size": d.size_bytes,
                "version": d.current_version,
                "created_at": d.created_at.isoformat()
            }
            for d in docs
        ]
    )


@documents_bp.route("/upload", methods=["POST"])
def upload_document():
    if current_user.role != "owner":
        append_audit(
            current_user.id,
            "document_upload",
            "denied",
            details={"role": current_user.role}
        )
        db.session.commit()
        abort(403)

    file = request.files.get("file")
    title = (request.form.get("title") or "").strip()
    category = (request.form.get("category") or "General").strip()
    description = (request.form.get("description") or "").strip()

    if not file or not file.filename or not title:
        return jsonify(
            error="Choose a file and enter a document title."
        ), 400

    safe_name = secure_filename(file.filename)
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""

    if ext not in ALLOWED_EXTENSIONS:
        return jsonify(error="File type is not allowed."), 415

    content = file.read(MAX_BYTES + 1)

    if not content:
        return jsonify(error="The file is empty."), 400

    if len(content) > MAX_BYTES:
        return jsonify(error="Maximum file size is 15 MB."), 413

    mime = (file.mimetype or "application/octet-stream").lower()

    content_error = _content_error(ext, content)

    if content_error:
        return jsonify(error=content_error), 415

    storage_key = uuid.uuid4().hex
    checksum = hashlib.sha256(content).hexdigest()

    # Store file in the private Supabase bucket.
    try:
        upload_file(storage_key, content, mime)

    except Exception:
        current_app.logger.exception("Supabase document upload failed")
        return jsonify(error="Unable to store document."), 500

    doc = Document(
        owner_id=current_user.id,
        title=title[:200],
        description=description[:4000],
        category=category[:100],
        original_filename=safe_name[:255],
        storage_key=storage_key,
        mime_type=mime[:100],
        size_bytes=len(content),
        current_version=1
    )

    try:
        db.session.add(doc)
        db.session.flush()

        db.session.add(
            DocumentVersion(
                document_id=doc.id,
                version_number=1,
                storage_key=storage_key,
                uploaded_by=current_user.id,
                checksum=checksum
            )
        )

        append_audit(
            current_user.id,
            "document_upload",
            "success",
            document_id=doc.id,
            details={
                "filename": safe_name,
                "bytes": len(content),
                "sha256": checksum
            }
        )

        db.session.commit()

    except Exception:
        db.session.rollback()
        _delete_cloud_file(storage_key)

        current_app.logger.exception("Document upload database save failed")

        return jsonify(error="Unable to save document."), 500

    return jsonify(
        message="Document uploaded.",
        document_id=doc.id
    ), 201


@documents_bp.route("/<doc_id>", methods=["GET"])
def document_detail(doc_id):
    doc = _get_doc(doc_id)
    _permitted(doc, "read")

    append_audit(
        current_user.id,
        "document_view",
        "success",
        document_id=doc.id
    )
    db.session.commit()

    return jsonify(
        id=doc.id,
        title=doc.title,
        description=doc.description,
        category=doc.category,
        filename=doc.original_filename,
        version=doc.current_version,
        owner_id=doc.owner_id
    )


@documents_bp.route("/<doc_id>/download", methods=["GET"])
def download_document(doc_id):
    doc = _get_doc(doc_id)

    # Authorization is checked before accessing Supabase.
    _permitted(doc, "read")

    try:
        content = download_file(doc.storage_key)

    except Exception:
        append_audit(
            current_user.id,
            "document_download",
            "error",
            document_id=doc.id,
            details={"reason": "storage_missing"}
        )
        db.session.commit()

        current_app.logger.exception("Supabase document download failed")
        abort(404)

    append_audit(
        current_user.id,
        "document_download",
        "success",
        document_id=doc.id,
        details={"filename": doc.original_filename}
    )
    db.session.commit()

    return send_file(
        BytesIO(content),
        as_attachment=True,
        download_name=doc.original_filename,
        mimetype="application/octet-stream",
        conditional=True
    )


@documents_bp.route("/<doc_id>/metadata", methods=["PATCH"])
def update_metadata(doc_id):
    doc = _get_doc(doc_id)

    if doc.owner_id != current_user.id:
        _deny(doc, "document_metadata_change")

    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    category = (data.get("category") or "").strip()

    if not title or not category:
        return jsonify(error="Title and category are required."), 400

    before = {
        "title": doc.title,
        "category": doc.category
    }

    doc.title = title[:200]
    doc.category = category[:100]

    for grant in Permission.query.filter_by(
        document_id=doc.id,
        revoked_at=None
    ).all():
        _notify(
            grant.user_id,
            "document_metadata_updated",
            f"Details for '{doc.title}' were updated by its Owner.",
            doc.id
        )

    append_audit(
        current_user.id,
        "document_metadata_change",
        "success",
        document_id=doc.id,
        details={
            "before": before,
            "after": {
                "title": doc.title,
                "category": doc.category
            }
        }
    )

    db.session.commit()

    return jsonify(message="Document updated.")


@documents_bp.route("/<doc_id>/share", methods=["POST"])
def share_document(doc_id):
    doc = _get_doc(doc_id)

    if doc.owner_id != current_user.id:
        _deny(doc, "permission_grant")

    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    kind = data.get("permission_type")

    if kind not in ("read", "edit") or not email:
        return jsonify(
            error="Email and read/edit permission are required."
        ), 400

    recipient = User.query.filter(
        db.func.lower(User.email) == email
    ).first()

    if (
        not recipient
        or not recipient.is_active
        or not recipient.email_verified
        or recipient.role not in ("viewer", "owner")
        or recipient.id == current_user.id
    ):
        return jsonify(
            error="Choose an active, verified Viewer or Owner other than yourself."
        ), 400

    existing = Permission.query.filter_by(
        document_id=doc.id,
        user_id=recipient.id,
        revoked_at=None
    ).first()

    if existing:
        existing.permission_type = kind

    else:
        db.session.add(
            Permission(
                document_id=doc.id,
                user_id=recipient.id,
                permission_type=kind,
                granted_by=current_user.id
            )
        )

    _notify(
        recipient.id,
        "document_shared",
        f"{current_user.name} shared '{doc.title}' with you ({kind}).",
        doc.id
    )

    append_audit(
        current_user.id,
        "permission_grant",
        "success",
        document_id=doc.id,
        target_user_id=recipient.id,
        details={
            "permission": kind,
            "recipient_email": email
        }
    )

    db.session.commit()

    return jsonify(message="Permission granted.")


@documents_bp.route("/<doc_id>/permissions", methods=["GET"])
def list_permissions(doc_id):
    doc = _get_doc(doc_id)

    if doc.owner_id != current_user.id:
        _deny(doc, "permission_list")

    rows = Permission.query.filter_by(
        document_id=doc.id,
        revoked_at=None
    ).all()

    return jsonify(
        permissions=[
            {
                "id": p.id,
                "user_id": p.user_id,
                "name": (
                    db.session.get(User, p.user_id).name
                    if db.session.get(User, p.user_id)
                    else "Unknown"
                ),
                "email": (
                    db.session.get(User, p.user_id).email
                    if db.session.get(User, p.user_id)
                    else ""
                ),
                "permission_type": p.permission_type,
                "granted_at": p.granted_at.isoformat()
            }
            for p in rows
        ]
    )


@documents_bp.route("/<doc_id>/revoke/<permission_id>", methods=["POST"])
def revoke_permission(doc_id, permission_id):
    doc = _get_doc(doc_id)

    if doc.owner_id != current_user.id:
        _deny(doc, "permission_revoke")

    p = Permission.query.filter_by(
        id=permission_id,
        document_id=doc.id,
        revoked_at=None
    ).first()

    if not p:
        append_audit(
            current_user.id,
            "permission_revoke",
            "denied",
            document_id=doc.id,
            details={"permission_id": permission_id}
        )
        db.session.commit()
        abort(404)

    p.revoked_at = datetime.now(timezone.utc)

    _notify(
        p.user_id,
        "permission_revoked",
        f"Your access to '{doc.title}' was revoked.",
        doc.id
    )

    append_audit(
        current_user.id,
        "permission_revoke",
        "success",
        document_id=doc.id,
        target_user_id=p.user_id,
        details={"permission": p.permission_type}
    )

    db.session.commit()

    return jsonify(message="Access revoked immediately.")


@documents_bp.route("/<doc_id>/version", methods=["POST"])
def upload_version(doc_id):
    doc = _get_doc(doc_id)
    _permitted(doc, "edit")

    file = request.files.get("file")

    if not file or not file.filename:
        return jsonify(error="Select a revised file."), 400

    safe = secure_filename(file.filename)
    ext = safe.rsplit(".", 1)[-1].lower() if "." in safe else ""

    if ext not in ALLOWED_EXTENSIONS:
        return jsonify(error="File type is not allowed."), 415

    content = file.read(MAX_BYTES + 1)

    if not content:
        return jsonify(error="The revised file is empty."), 400

    if len(content) > MAX_BYTES:
        return jsonify(error="Maximum file size is 15 MB."), 413

    content_error = _content_error(ext, content)

    if content_error:
        return jsonify(error=content_error), 415

    key = uuid.uuid4().hex
    checksum = hashlib.sha256(content).hexdigest()
    mime = (file.mimetype or "application/octet-stream").lower()

    # Upload the revised file to the private Supabase bucket.
    try:
        upload_file(key, content, mime)

    except Exception:
        current_app.logger.exception("Supabase version upload failed")
        return jsonify(error="Unable to store the revised document."), 500

    number = doc.current_version + 1

    try:
        doc.current_version = number
        doc.storage_key = key
        doc.original_filename = safe
        doc.size_bytes = len(content)
        doc.updated_at = datetime.now(timezone.utc)

        db.session.add(
            DocumentVersion(
                document_id=doc.id,
                version_number=number,
                storage_key=key,
                uploaded_by=current_user.id,
                checksum=checksum
            )
        )

        for p in Permission.query.filter_by(
            document_id=doc.id,
            revoked_at=None
        ).all():
            _notify(
                p.user_id,
                "document_updated",
                f"'{doc.title}' was updated to version {number}.",
                doc.id
            )

        append_audit(
            current_user.id,
            "document_version_upload",
            "success",
            document_id=doc.id,
            details={
                "version": number,
                "sha256": checksum
            }
        )

        db.session.commit()

    except Exception:
        db.session.rollback()
        _delete_cloud_file(key)

        current_app.logger.exception("Document version database save failed")

        return jsonify(
            error="Unable to save the revised document."
        ), 500

    return jsonify(
        message="New version uploaded.",
        version=number
    ), 201


@documents_bp.route("/<doc_id>/archive", methods=["POST"])
def archive_document(doc_id):
    doc = _get_doc(doc_id)

    if doc.owner_id != current_user.id:
        _deny(doc, "document_archive")

    doc.deleted_at = datetime.now(timezone.utc)

    for grant in Permission.query.filter_by(
        document_id=doc.id,
        revoked_at=None
    ).all():
        _notify(
            grant.user_id,
            "document_archived",
            f"'{doc.title}' was archived by its Owner.",
            doc.id
        )

    append_audit(
        current_user.id,
        "document_archive",
        "success",
        document_id=doc.id
    )

    db.session.commit()

    return jsonify(message="Document archived.")


@documents_bp.route("/<doc_id>/restore", methods=["POST"])
def restore_document(doc_id):
    doc = _get_doc(doc_id, include_deleted=True)

    if doc.owner_id != current_user.id:
        _deny(doc, "document_restore")

    if doc.deleted_at is None:
        return jsonify(error="Document is not archived."), 409

    doc.deleted_at = None

    for grant in Permission.query.filter_by(
        document_id=doc.id,
        revoked_at=None
    ).all():
        _notify(
            grant.user_id,
            "document_restored",
            f"'{doc.title}' was restored by its Owner.",
            doc.id
        )

    append_audit(
        current_user.id,
        "document_restore",
        "success",
        document_id=doc.id
    )

    db.session.commit()

    return jsonify(message="Document restored.")


@documents_bp.route("/<doc_id>/star", methods=["POST"])
def star_document(doc_id):
    doc = _get_doc(doc_id)
    _permitted(doc, "read")

    star = StarredDocument.query.filter_by(
        user_id=current_user.id,
        document_id=doc.id
    ).first()

    if star:
        db.session.delete(star)
        state = False

    else:
        db.session.add(
            StarredDocument(
                user_id=current_user.id,
                document_id=doc.id
            )
        )
        state = True

    append_audit(
        current_user.id,
        "document_star_toggle",
        "success",
        document_id=doc.id,
        details={"starred": state}
    )

    db.session.commit()

    return jsonify(starred=state)


@documents_bp.route("/starred", methods=["GET"])
def starred_documents():
    if current_user.role not in ("owner", "viewer"):
        append_audit(
            current_user.id,
            "document_starred_list",
            "denied",
            details={"role": current_user.role}
        )
        db.session.commit()
        abort(403)

    rows = StarredDocument.query.filter_by(
        user_id=current_user.id
    ).all()

    ids = [r.document_id for r in rows]

    docs = (
        Document.query.filter(
            Document.id.in_(ids),
            Document.deleted_at.is_(None)
        ).all()
        if ids
        else []
    )

    docs = [
        d for d in docs
        if can_access_document(d, "read")
    ]

    return jsonify(
        documents=[
            {
                "id": d.id,
                "title": d.title,
                "category": d.category
            }
            for d in docs
        ]
    )

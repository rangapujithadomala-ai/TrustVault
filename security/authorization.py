from flask import abort
from flask_login import current_user
from models.permission import Permission
from models.document import Document
from models.user import User
from datetime import datetime, timezone


def require_active_user():
    if not current_user.is_authenticated: abort(401)
    if not current_user.is_active: abort(403)


def can_access_document(document, required_permission="read"):
    require_active_user()
    if required_permission not in ("read", "edit"): return False
    if document is None or document.deleted_at is not None: return False
    owner = User.query.filter_by(id=document.owner_id, is_active=True).first()
    if owner is None: return False
    if document.owner_id == current_user.id: return True
    permission = Permission.query.filter_by(document_id=document.id,user_id=current_user.id,revoked_at=None).first()
    if permission is None: return False
    recipient=User.query.filter_by(id=current_user.id,is_active=True,email_verified=True).first()
    if recipient is None: return False
    if required_permission == "read": return permission.permission_type in ("read", "edit")
    return permission.permission_type == "edit"


def require_document_permission(document, required_permission="read"):
    if not can_access_document(document, required_permission): abort(403)


from flask import abort
from flask_login import current_user

from models.permission import Permission


def require_active_user():
    """Ensure the current user has an active account."""

    if not current_user.is_authenticated:
        abort(401)

    if not current_user.is_active:
        abort(403)


def can_access_document(document, required_permission="read"):
    """Check whether the current user can access a document."""

    require_active_user()

    # Reject invalid permission requests.
    if required_permission not in ("read", "edit"):
        return False

    # The document owner has full access to their document.
    if document.owner_id == current_user.id:
        return True

    # Find the user's currently active permission.
    permission = Permission.query.filter_by(
        document_id=document.id,
        user_id=current_user.id,
        revoked_at=None
    ).first()

    if permission is None:
        return False

    # Edit permission also allows reading.
    if required_permission == "read":
        return permission.permission_type in ("read", "edit")

    return permission.permission_type == "edit"


def require_document_permission(document, required_permission="read"):
    """Stop the request if the user lacks document permission."""

    if not can_access_document(document, required_permission):
        abort(403)


import hashlib
import hmac

from flask import session
from extensions import login_manager
from models.user import User


@login_manager.user_loader
def load_user(user_id):
    """
    Load the user from the database and validate the existing session.

    Inactive accounts and sessions created with an older password hash
    must be rejected.
    """

    # Force SQLAlchemy to refresh the user from the database.
    user = (
        User.query
        .populate_existing()
        .filter_by(id=user_id)
        .first()
    )

    session_password_snapshot = session.get(
        "_trustvault_password_snapshot"
    )

    if not user or not user.is_active:
        session.pop("_user_id", None)
        session.pop("_fresh", None)
        session.pop("_trustvault_password_snapshot", None)
        return None

    if not session_password_snapshot:
        session.pop("_user_id", None)
        session.pop("_fresh", None)
        session.pop("_trustvault_password_snapshot", None)
        return None

    current_password_snapshot = hashlib.sha256(
        user.password_hash.encode("utf-8")
    ).hexdigest()

    if not hmac.compare_digest(
        session_password_snapshot,
        current_password_snapshot
    ):
        session.pop("_user_id", None)
        session.pop("_fresh", None)
        session.pop("_trustvault_password_snapshot", None)
        return None

    return user

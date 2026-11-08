import hashlib
from flask import session
from extensions import login_manager
from models.user import User

@login_manager.user_loader
def load_user(user_id):
    # Disabled accounts and sessions created with an old password hash are invalid.
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return None
    session_password_snapshot = session.get("_trustvault_password_snapshot")
    if not session_password_snapshot or session_password_snapshot != hashlib.sha256(user.password_hash.encode("utf-8")).hexdigest():
        return None
    return user

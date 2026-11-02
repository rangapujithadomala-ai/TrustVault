from extensions import login_manager
from models.user import User


@login_manager.user_loader
def load_user(user_id):
    """Retrieve a user from the database using their ID."""

    return User.query.get(user_id)
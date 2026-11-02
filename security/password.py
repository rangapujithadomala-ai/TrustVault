import re

from werkzeug.security import generate_password_hash, check_password_hash


def validate_password(password):
    """Check whether a password meets TrustVault's requirements."""

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."

    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."

    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "Password must contain at least one special character."

    return True, "Password is valid."


def hash_password(password):
    """Convert a plain password into a secure password hash."""

    return generate_password_hash(
        password,
        method="scrypt"
    )


def verify_password(stored_hash, entered_password):
    """Check an entered password against its stored hash."""

    return check_password_hash(stored_hash, entered_password)
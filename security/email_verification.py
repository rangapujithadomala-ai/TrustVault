
import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from extensions import db
from models.email_verification_token import EmailVerificationToken
from models.user import User


def generate_verification_token():
    """Generate a secure random email verification token."""
    return secrets.token_urlsafe(32)


def hash_verification_token(token):
    """Convert a verification token into a SHA-256 hash."""
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def save_verification_token(user_id, token):
    """Save a hashed verification token with a 24-hour expiry."""

    token_hash = hash_verification_token(token)

    verification_record = EmailVerificationToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )

    db.session.add(verification_record)
    db.session.commit()

    return verification_record


def verify_email_token(token):
    """Verify an email address using its verification token."""

    token_hash = hash_verification_token(token)

    verification_record = EmailVerificationToken.query.filter_by(
        token_hash=token_hash,
        used_at=None
    ).first()

    # Check whether the token exists
    if verification_record is None:
        return False

    # Get the token expiry time
    expiry_time = verification_record.expires_at

    # SQLite may return a datetime without timezone information
    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)

    # Check whether the token has expired
    if datetime.now(timezone.utc) >= expiry_time:
        return False

    # Find the account connected to this token
    user = db.session.get(User, verification_record.user_id)

    if user is None or not user.is_active:
        return False

    # Mark the email as verified
    user.email_verified = True

    # Mark the token as used
    verification_record.used_at = datetime.now(timezone.utc)

    db.session.commit()

    return True

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Index, text
from flask_login import UserMixin

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(255), nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

   

    role = db.Column(
        db.String(20),
        nullable=False,
        default="viewer"
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    email_verified = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'owner', 'viewer')",
            name="check_valid_user_role"
        ),
        Index(
            "uq_users_email_lower",
            text("lower(email)"),
            unique=True
        )
    )

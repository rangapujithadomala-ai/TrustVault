
import uuid
from datetime import datetime, timezone

from extensions import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    owner_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    title = db.Column(db.String(200), nullable=False)

    description = db.Column(db.Text, nullable=True)

    category = db.Column(
        db.String(100),
        nullable=False
    )

    original_filename = db.Column(
        db.String(255),
        nullable=False
    )

    storage_key = db.Column(
        db.String(255),
        unique=True,
        nullable=False
    )

    mime_type = db.Column(db.String(100), nullable=False)

    size_bytes = db.Column(db.BigInteger, nullable=False)

    current_version = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    deleted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

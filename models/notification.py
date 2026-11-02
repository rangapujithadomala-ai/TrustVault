import uuid
from datetime import datetime, timezone

from extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    recipient_user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    notification_type = db.Column(
        db.String(50),
        nullable=False
    )

    message = db.Column(
        db.String(500),
        nullable=False
    )

    related_document_id = db.Column(
        db.String(36),
        db.ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    read_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )
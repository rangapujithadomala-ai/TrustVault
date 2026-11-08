import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Index, text

from extensions import db


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    document_id = db.Column(
        db.String(36),
        db.ForeignKey("documents.id"),
        nullable=False,
        index=True
    )

    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    permission_type = db.Column(
        db.String(10),
        nullable=False
    )

    granted_by = db.Column(
        db.String(36),
        db.ForeignKey("users.id"),
        nullable=False
    )

    granted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    revoked_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "permission_type IN ('read', 'edit')",
            name="check_valid_permission_type"
        ),

        Index(
            "uq_active_document_user_permission",
            "document_id",
            "user_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
            sqlite_where=text("revoked_at IS NULL")
        )
    )
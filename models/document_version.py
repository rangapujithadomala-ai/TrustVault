import uuid
from datetime import datetime, timezone

from extensions import db


class DocumentVersion(db.Model):
    __tablename__ = "document_versions"

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

    version_number = db.Column(
        db.Integer,
        nullable=False
    )

    storage_key = db.Column(
        db.String(255),
        unique=True,
        nullable=False
    )

    uploaded_by = db.Column(
        db.String(36),
        db.ForeignKey("users.id"),
        nullable=False
    )

    checksum = db.Column(
        db.String(64),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.UniqueConstraint(
            "document_id",
            "version_number",
            name="unique_document_version"
        ),
    )
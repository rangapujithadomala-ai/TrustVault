import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint
from extensions import db


class DocumentInvitation(db.Model):
    __tablename__ = "document_invitations"

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

    invited_email = db.Column(db.String(255), nullable=False, index=True)
    permission_type = db.Column(db.String(10), nullable=False)

    token_hash = db.Column(db.String(64), nullable=False, unique=True)

    invited_by = db.Column(
        db.String(36),
        db.ForeignKey("users.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    accepted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    accepted_by = db.Column(
        db.String(36),
        db.ForeignKey("users.id"),
        nullable=True
    )
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "permission_type IN ('read', 'edit')",
            name="check_document_invitation_permission"
        ),
    )
import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, UniqueConstraint

from extensions import db


class DocumentInvitationItem(db.Model):
    __tablename__ = "document_invitation_items"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    invitation_id = db.Column(
        db.String(36),
        db.ForeignKey("document_invitations.id"),
        nullable=False,
        index=True
    )

    document_id = db.Column(
        db.String(36),
        db.ForeignKey("documents.id"),
        nullable=False,
        index=True
    )

    permission_type = db.Column(
        db.String(10),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        CheckConstraint(
            "permission_type IN ('read', 'edit')",
            name="check_invitation_item_permission"
        ),
        UniqueConstraint(
            "invitation_id",
            "document_id",
            name="uq_invitation_item_document"
        )
    )
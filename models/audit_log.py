from datetime import datetime, timezone

from extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(
        db.BigInteger().with_variant(db.Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True
    )

    actor_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    document_id = db.Column(
        db.String(36),
        db.ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    target_user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    action = db.Column(
        db.String(50),
        nullable=False
    )

    outcome = db.Column(
        db.String(20),
        nullable=False
    )

    ip_address = db.Column(
        db.String(45),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    details = db.Column(
        db.JSON,
        nullable=True
    )

    previous_hash = db.Column(
        db.String(64),
        nullable=True
    )

    event_hash = db.Column(
        db.String(64),
        nullable=False,
        unique=True
    )
import uuid
from datetime import datetime, timezone
from extensions import db

class StarredDocument(db.Model):
    __tablename__ = "starred_documents"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = db.Column(db.String(36), db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint("user_id", "document_id", name="uq_user_star_document"),)

import uuid
from datetime import datetime, timezone
from extensions import db

class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    id=db.Column(db.String(36),primary_key=True,default=lambda:str(uuid.uuid4()))
    user_id=db.Column(db.String(36),db.ForeignKey("users.id",ondelete="CASCADE"),nullable=False,index=True)
    token_hash=db.Column(db.String(64),nullable=False,unique=True,index=True)
    expires_at=db.Column(db.DateTime(timezone=True),nullable=False)
    used_at=db.Column(db.DateTime(timezone=True),nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))

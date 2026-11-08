from app import create_app
from extensions import db
from models import AuditLog
from security.audit import append_audit
import models


app = create_app()

with app.app_context():
    db.create_all()
    if AuditLog.query.order_by(AuditLog.id.desc()).first() is None:
        append_audit(None, "audit_chain_genesis", "success", details={"source":"database_setup"})
        db.session.commit()
    print("TrustVault database tables created successfully!")
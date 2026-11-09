"""Provision explicitly configured demo accounts in an isolated non-production DB."""
import os, uuid, hashlib
from config import require_nonproduction_demo_mode

try:
    require_nonproduction_demo_mode()
except RuntimeError as error:
    raise SystemExit(str(error)) from None

from app import create_app
from extensions import db
from models import User, Document, Permission, DocumentVersion, Notification
from security.password import hash_password, validate_password
from security.audit import append_audit

app=create_app()

with app.app_context():
    def configured(name):
        value=os.getenv(name)
        if not value: raise SystemExit(f"Missing required environment variable: {name}")
        return value.strip()
    accounts=[]
    created_admin=False
    for prefix, role in (("ADMIN","admin"),("DEMO_OWNER","owner"),("DEMO_VIEWER","viewer")):
        name=configured(prefix+"_NAME")
        email=configured(prefix+"_EMAIL").lower()
        password=configured(prefix+"_PASSWORD")
        ok,message=validate_password(password)
        if not ok: raise SystemExit(f"{prefix}_PASSWORD: {message}")
        user=User.query.filter_by(email=email).first()
        if user:
            raise SystemExit(
                "A configured demo account already exists; no existing account was changed."
            )
        user=User(name=name,email=email,password_hash=hash_password(password),role=role,is_active=True,email_verified=True)
        db.session.add(user)
        if role=="admin": created_admin=True
        accounts.append(user)
    db.session.flush()
    admin,owner,viewer=accounts
    if created_admin:
        append_audit(admin.id,"demo_admin_seed","success",details={"email":admin.email,"demo_account":True})
    storage=app.config.get("TRUSTVAULT_STORAGE") or os.path.join(app.instance_path,"private_documents")
    os.makedirs(storage,mode=0o700,exist_ok=True)
    sample=b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF\n"
    doc=Document.query.filter_by(owner_id=owner.id,title="TrustVault Evaluation Sample").first()
    if not doc:
        key=uuid.uuid4().hex
        with open(os.path.join(storage,key),"xb") as handle: handle.write(sample)
        doc=Document(owner_id=owner.id,title="TrustVault Evaluation Sample",description="Seeded sample PDF used to test protected access.",category="Demo",original_filename="trustvault-evaluation-sample.pdf",storage_key=key,mime_type="application/pdf",size_bytes=len(sample),current_version=1)
        db.session.add(doc); db.session.flush()
        db.session.add(DocumentVersion(document_id=doc.id,version_number=1,storage_key=key,uploaded_by=owner.id,checksum=hashlib.sha256(sample).hexdigest()))
        db.session.add(Permission(document_id=doc.id,user_id=viewer.id,permission_type="read",granted_by=owner.id))
        db.session.add(Notification(recipient_user_id=viewer.id,notification_type="document_shared",message="A demo document was shared with you.",related_document_id=doc.id))
        append_audit(owner.id,"demo_seed_upload","success",document_id=doc.id,details={"sample":True,"sha256":hashlib.sha256(sample).hexdigest()})
    db.session.commit()
    print("Explicitly configured demo accounts are provisioned in the non-production database.")

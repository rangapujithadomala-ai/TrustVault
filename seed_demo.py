"""Provision the dedicated demo Owner/Viewer accounts and a private sample PDF.
Published demo credentials are intended only for evaluator access; never reuse
these passwords for production accounts. Environment variables may override them.
"""
import os, uuid, hashlib
from app import create_app
from extensions import db
from models import User, Document, Permission, DocumentVersion, Notification
from security.password import hash_password, validate_password
from security.audit import append_audit

app=create_app()

with app.app_context():
    defaults={
        "ADMIN_NAME":"Demo Administrator",
        "ADMIN_EMAIL":"demo-admin@example.com",
        "ADMIN_PASSWORD":"TrustVaultDemoAdmin@2026",
        "DEMO_OWNER_NAME":"Demo Owner",
        "DEMO_OWNER_EMAIL":"demo-owner@example.com",
        "DEMO_OWNER_PASSWORD":"TrustVaultDemoOwner@2026",
        "DEMO_VIEWER_NAME":"Demo Viewer",
        "DEMO_VIEWER_EMAIL":"demo-viewer@example.com",
        "DEMO_VIEWER_PASSWORD":"TrustVaultDemoViewer@2026",
    }
    def configured(name):
        value=os.getenv(name) or defaults.get(name)
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
            if user.role != role: raise SystemExit(f"{email} already exists with a different role.")
            user.name=name; user.password_hash=hash_password(password); user.is_active=True; user.email_verified=True
        else:
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
    else:
        if doc.deleted_at is not None:
            doc.deleted_at=None
            append_audit(owner.id,"demo_seed_restore","success",document_id=doc.id,details={"sample":True})
        if not os.path.isfile(os.path.join(storage,doc.storage_key)):
            key=uuid.uuid4().hex
            with open(os.path.join(storage,key),"xb") as handle: handle.write(sample)
            next_version=doc.current_version+1
            doc.storage_key=key;doc.current_version=next_version;doc.size_bytes=len(sample);doc.original_filename="trustvault-evaluation-sample.pdf"
            db.session.add(DocumentVersion(document_id=doc.id,version_number=next_version,storage_key=key,uploaded_by=owner.id,checksum=hashlib.sha256(sample).hexdigest()))
            append_audit(owner.id,"demo_seed_storage_repair","success",document_id=doc.id,details={"version":next_version,"sha256":hashlib.sha256(sample).hexdigest()})
        active_grant=Permission.query.filter_by(document_id=doc.id,user_id=viewer.id,revoked_at=None).first()
        if active_grant is None:
            db.session.add(Permission(document_id=doc.id,user_id=viewer.id,permission_type="read",granted_by=owner.id))
            db.session.add(Notification(recipient_user_id=viewer.id,notification_type="document_shared",message="A demo document was shared with you.",related_document_id=doc.id))
            append_audit(owner.id,"demo_seed_permission_grant","success",document_id=doc.id,target_user_id=viewer.id,details={"permission":"read"})
    db.session.commit()
    print("Demo Owner and Viewer accounts are provisioned; sample document is private and shared with the demo Viewer.")

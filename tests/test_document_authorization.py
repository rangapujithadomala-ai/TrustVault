from io import BytesIO
from models import User, Document, Permission, AuditLog
from extensions import db
from security.password import hash_password
from security.audit import verify_audit_chain


def make_user(name, email, role):
    user = User(name=name, email=email, password_hash=hash_password("TrustVault@123"), role=role, is_active=True, email_verified=True)
    db.session.add(user); db.session.commit()
    return user


def login(client, email):
    return client.post("/auth/login", json={"email": email, "password": "TrustVault@123"})


def upload_pdf(client):
    pdf = b"%PDF-1.4\n% minimal test pdf\n%%EOF"
    response = client.post("/documents/upload", data={
        "title": "Private Salary Letter", "category": "HR",
        "file": (BytesIO(pdf), "salary.pdf", "application/pdf")
    }, content_type="multipart/form-data")
    assert response.status_code == 201, response.get_json()
    return response.get_json()["document_id"]


def test_non_grantee_cannot_read_or_download_and_denial_is_audited(client):
    owner = make_user("Owner One", "owner1@example.com", "owner")
    viewer = make_user("Viewer One", "viewer1@example.com", "viewer")
    login(client, owner.email)
    doc_id = upload_pdf(client)
    client.post("/auth/logout")
    login(client, viewer.email)

    detail = client.get(f"/documents/{doc_id}")
    download = client.get(f"/documents/{doc_id}/download")
    assert detail.status_code == 403
    assert download.status_code == 403

    rows = AuditLog.query.filter_by(actor_id=viewer.id, document_id=doc_id, outcome="denied").all()
    assert len(rows) >= 2
    assert verify_audit_chain()[0] is True


def test_read_grant_downloads_but_does_not_edit_then_revoke_is_immediate(client):
    owner = make_user("Owner Two", "owner2@example.com", "owner")
    viewer = make_user("Viewer Two", "viewer2@example.com", "viewer")
    login(client, owner.email)
    doc_id = upload_pdf(client)
    client.post("/documents/%s/share" % doc_id, json={"email": viewer.email, "permission_type": "read"})
    permission = Permission.query.filter_by(document_id=doc_id, user_id=viewer.id, revoked_at=None).first()
    assert permission is not None

    client.post("/auth/logout")
    login(client, viewer.email)
    assert client.get(f"/documents/{doc_id}").status_code == 200
    file_response = client.get(f"/documents/{doc_id}/download")
    assert file_response.status_code == 200
    assert file_response.data.startswith(b"%PDF-")
    assert client.patch(f"/documents/{doc_id}/metadata", json={"title":"Intruded", "category":"HR"}).status_code == 403

    client.post("/auth/logout")
    login(client, owner.email)
    revoke = client.post(f"/documents/{doc_id}/revoke/{permission.id}")
    assert revoke.status_code == 200
    client.post("/auth/logout")
    login(client, viewer.email)
    assert client.get(f"/documents/{doc_id}").status_code == 403
    assert client.get(f"/documents/{doc_id}/download").status_code == 403
    assert verify_audit_chain()[0] is True

def test_edit_grant_allows_revision_upload(client):
    owner=make_user("Owner Edit", "owner-edit@example.com", "owner")
    viewer=make_user("Editor User", "editor@example.com", "viewer")
    login(client,owner.email)
    doc_id=upload_pdf(client)
    share=client.post(f"/documents/{doc_id}/share",json={"email":viewer.email,"permission_type":"edit"})
    assert share.status_code==200
    client.post("/auth/logout")
    login(client,viewer.email)
    revised=b"%PDF-1.4\n% revised document\n%%EOF"
    response=client.post(f"/documents/{doc_id}/version",data={"file":(BytesIO(revised),"salary-revised.pdf","application/pdf")},content_type="multipart/form-data")
    assert response.status_code==201,response.get_json()
    document=db.session.get(Document,doc_id)
    assert document.current_version==2
    assert AuditLog.query.filter_by(actor_id=viewer.id,document_id=doc_id,action="document_version_upload",outcome="success").count()==1


def test_upload_validation_rejects_bad_extension_and_fake_pdf(client):
    owner=make_user("Owner Validate", "owner-validate@example.com", "owner")
    login(client,owner.email)
    bad_extension=client.post("/documents/upload",data={"title":"Bad","file":(BytesIO(b"some bytes"),"payload.exe","application/octet-stream")},content_type="multipart/form-data")
    assert bad_extension.status_code==415
    fake_pdf=client.post("/documents/upload",data={"title":"Fake PDF","file":(BytesIO(b"not a pdf"),"fake.pdf","application/pdf")},content_type="multipart/form-data")
    assert fake_pdf.status_code==415

def test_admin_offboarding_revokes_viewer_grants_and_old_session(client):
    admin=make_user("Admin Offboard", "admin-offboard@example.com", "admin")
    owner=make_user("Owner Offboard", "owner-offboard@example.com", "owner")
    viewer=make_user("Viewer Offboard", "viewer-offboard@example.com", "viewer")
    owner_client=client.application.test_client()
    viewer_client=client.application.test_client()
    admin_client=client.application.test_client()
    login(owner_client,owner.email)
    doc_id=upload_pdf(owner_client)
    owner_client.post(f"/documents/{doc_id}/share",json={"email":viewer.email,"permission_type":"read"})
    login(viewer_client,viewer.email)
    assert viewer_client.get(f"/documents/{doc_id}").status_code==200
    login(admin_client,admin.email)

    deactivated=admin_client.post(f"/admin/users/{viewer.id}/deactivate",json={})
    assert deactivated.status_code==200
    grant=Permission.query.filter_by(document_id=doc_id,user_id=viewer.id).first()
    assert grant.revoked_at is not None
    # Existing browser session is rejected on its next request after the account/hash change.
    assert viewer_client.get(f"/documents/{doc_id}/download").status_code==401
    assert login(viewer_client,viewer.email).status_code==401


def test_owner_offboarding_transfers_owned_documents_before_deactivation(client):
    admin=make_user("Admin Transfer", "admin-transfer@example.com", "admin")
    former_owner=make_user("Former Owner", "former-owner@example.com", "owner")
    new_owner=make_user("New Owner", "new-owner@example.com", "owner")
    viewer=make_user("Retained Viewer", "retained-viewer@example.com", "viewer")
    owner_client=client.application.test_client()
    admin_client=client.application.test_client()
    viewer_client=client.application.test_client()
    login(owner_client,former_owner.email)
    doc_id=upload_pdf(owner_client)
    owner_client.post(f"/documents/{doc_id}/share",json={"email":viewer.email,"permission_type":"read"})
    login(admin_client,admin.email)

    transfer=admin_client.post(f"/admin/users/{former_owner.id}/transfer-documents",json={"new_owner_id":new_owner.id})
    assert transfer.status_code==200
    deactivation=admin_client.post(f"/admin/users/{former_owner.id}/deactivate",json={})
    assert deactivation.status_code==200
    document=db.session.get(Document,doc_id)
    assert document.owner_id==new_owner.id
    login(viewer_client,viewer.email)
    assert viewer_client.get(f"/documents/{doc_id}/download").status_code==200

def test_audit_chain_detects_event_details_tampering(client):
    from security.audit import append_audit, verify_audit_chain
    append_audit(None,"tamper_test_event","success",details={"original":"value"})
    db.session.commit()
    assert verify_audit_chain()[0] is True
    row=AuditLog.query.filter_by(action="tamper_test_event").first()
    row.details={"original":"changed"}
    db.session.commit()
    valid,failed_id=verify_audit_chain()
    assert valid is False
    assert failed_id==row.id

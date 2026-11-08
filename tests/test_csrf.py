import re
from app import create_app
from extensions import db


def test_csrf_rejects_mutation_without_token():
    app=create_app({"TESTING":True,"SECRET_KEY":"csrf-test-secret","SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","WTF_CSRF_ENABLED":True})
    with app.app_context():
        db.create_all()
    client=app.test_client()
    blocked=client.post("/auth/login",json={"email":"nobody@example.com","password":"TrustVault@123"})
    assert blocked.status_code==400
    page=client.get("/login.html")
    match=re.search(r'<meta name="csrf-token" content="([^"]+)"',page.data.decode())
    assert match is not None
    token=match.group(1)
    allowed_by_csrf=client.post("/auth/login",json={"email":"nobody@example.com","password":"TrustVault@123"},headers={"X-CSRFToken":token})
    assert allowed_by_csrf.status_code==401
    with app.app_context():
        db.session.remove()
        db.drop_all()

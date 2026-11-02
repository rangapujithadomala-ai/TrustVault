from datetime import datetime, timedelta, timezone

def test_registration_sends_verification_email(
    client, monkeypatch
):
    """Check that registration triggers a verification email."""

    sent_emails = []

    def fake_send_email(recipient, subject, body):
        sent_emails.append({
            "recipient": recipient,
            "subject": subject,
            "body": body
        })

    # Replace the real email sender during this test
    monkeypatch.setattr(
        "routes.auth.send_email",
        fake_send_email
    )

    response = client.post(
        "/auth/register",
        json={
            "name": "Test Student",
            "email": "student@example.com",
            "password": "TrustVault@123",
            "confirm_password": "TrustVault@123"
        }
    )

    assert response.status_code == 201
    assert len(sent_emails) == 1
    assert sent_emails[0]["recipient"] == "student@example.com"
    assert "Verify your TrustVault account" in sent_emails[0]["subject"]
    assert "/auth/verify-email/" in sent_emails[0]["body"]

    import re

    # Extract the verification token from the email
    match = re.search(
        r"/auth/verify-email/(\S+)",
        sent_emails[0]["body"]
    )

    assert match is not None

    token = match.group(1)

    # Open the verification link
    verification_response = client.get(
        f"/auth/verify-email/{token}"
    )

    assert verification_response.status_code == 200

def test_invalid_verification_token(client):
    response = client.get(
        "/auth/verify-email/invalid-random-token"
    )

    assert response.status_code == 400

def test_expired_verification_token(client, monkeypatch):
    from models.user import User
    from models.email_verification_token import EmailVerificationToken
    from security.email_verification import hash_verification_token
    from extensions import db

    user = User(
        name="Expired Student",
        email="expired@example.com",
        password_hash="temporary_hash",
        role="viewer",
        is_active=True,
        email_verified=False
    )

    db.session.add(user)
    db.session.commit()

    token = "expired-test-token"

    expired_record = EmailVerificationToken(
        user_id=user.id,
        token_hash=hash_verification_token(token),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )

    db.session.add(expired_record)
    db.session.commit()

    response = client.get(
        f"/auth/verify-email/{token}"
    )

    assert response.status_code == 400
    assert user.email_verified is False

def test_reused_verification_token(client, monkeypatch):
    from routes.auth import send_email
    from models.user import User
    from models.email_verification_token import EmailVerificationToken
    from security.email_verification import hash_verification_token
    from extensions import db

    user = User(
        name="Reuse Student",
        email="reuse@example.com",
        password_hash="temporary_hash",
        role="viewer",
        is_active=True,
        email_verified=False
    )

    db.session.add(user)
    db.session.commit()

    token = "reuse-test-token"

    record = EmailVerificationToken(
        user_id=user.id,
        token_hash=hash_verification_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )

    db.session.add(record)
    db.session.commit()

    # First attempt should succeed
    first_response = client.get(
        f"/auth/verify-email/{token}"
    )

    assert first_response.status_code == 200

    # Second attempt should fail
    second_response = client.get(
        f"/auth/verify-email/{token}"
    )

    assert second_response.status_code == 400

def test_unverified_user_cannot_login(client):
    from models.user import User
    from security.password import hash_password
    from extensions import db

    user = User(
        name="Unverified Student",
        email="unverified@example.com",
        password_hash=hash_password("TrustVault@123"),
        role="viewer",
        is_active=True,
        email_verified=False
    )

    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "unverified@example.com",
            "password": "TrustVault@123"
        }
    )

    assert response.status_code == 403
    assert b"verify your email" in response.data.lower()

def test_incorrect_password_cannot_login(client):
    from models.user import User
    from security.password import hash_password
    from extensions import db

    user = User(
        name="Verified Student",
        email="verified@example.com",
        password_hash=hash_password("TrustVault@123"),
        role="viewer",
        is_active=True,
        email_verified=True
    )

    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "verified@example.com",
            "password": "WrongPassword@123"
        }
    )

    assert response.status_code == 401
    assert b"Invalid email or password." in response.data

def test_inactive_user_cannot_login(client):
    from models.user import User
    from security.password import hash_password
    from extensions import db

    user = User(
        name="Inactive Student",
        email="inactive@example.com",
        password_hash=hash_password("TrustVault@123"),
        role="viewer",
        is_active=False,
        email_verified=True
    )

    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "TrustVault@123"
        }
    )

    assert response.status_code == 403
    assert b"inactive" in response.data.lower()

def test_verified_user_can_login(client):
    from models.user import User
    from security.password import hash_password
    from extensions import db

    user = User(
        name="Active Student",
        email="active@example.com",
        password_hash=hash_password("TrustVault@123"),
        role="viewer",
        is_active=True,
        email_verified=True
    )

    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "active@example.com",
            "password": "TrustVault@123"
        }
    )

    assert response.status_code == 200
    assert response.json["message"] == "Login successful."
    assert response.json["redirect"] == "/viewer/dashboard"

    with client.session_transaction() as session:
        assert "_user_id" in session

def test_user_can_logout(client):
    from models.user import User
    from security.password import hash_password
    from extensions import db

    user = User(
        name="Logout Student",
        email="logout@example.com",
        password_hash=hash_password("TrustVault@123"),
        role="viewer",
        is_active=True,
        email_verified=True
    )

    db.session.add(user)
    db.session.commit()

    # First, log in
    login_response = client.post(
        "/auth/login",
        json={
            "email": "logout@example.com",
            "password": "TrustVault@123"
        }
    )

    assert login_response.status_code == 200

    # Confirm that the user is logged in
    with client.session_transaction() as session:
        assert "_user_id" in session

    # Now log out
    logout_response = client.post("/auth/logout")

    assert logout_response.status_code == 200

    # Confirm that the session has been cleared
    with client.session_transaction() as session:
        assert "_user_id" not in session

from datetime import datetime, timedelta, timezone


def test_public_registration_is_disabled(client):
    """Public registration is disabled because accounts are invitation-only."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Test Student",
            "email": "student@example.com",
            "password": "TrustVault@123",
            "confirm_password": "TrustVault@123"
        }
    )

    assert response.status_code == 403
    assert b"invitation" in response.data.lower()


def test_invalid_verification_token(client):
    response = client.get(
        "/auth/verify-email/invalid-random-token"
    )

    assert response.status_code == 400
    assert b'data-status="invalid"' in response.data


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
        f"/auth/verify-email/{token}",
        follow_redirects=True
    )

    assert first_response.status_code == 200

    # Second attempt should fail
    second_response = client.get(
        f"/auth/verify-email/{token}",
        follow_redirects=True
    )

    assert second_response.status_code == 400
    assert b'data-status="invalid"' in second_response.data


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


def test_password_reset_token_is_single_use(client, monkeypatch):
    from models.user import User
    from models.password_reset_token import PasswordResetToken
    from security.password import hash_password, verify_password
    from extensions import db
    import re

    user = User(
        name="Reset Student",
        email="reset@example.com",
        password_hash=hash_password("TrustVault@123"),
        role="viewer",
        is_active=True,
        email_verified=True
    )

    db.session.add(user)
    db.session.commit()

    sent = []

    monkeypatch.setattr(
        "routes.auth.send_email",
        lambda recipient, subject, body: sent.append(body)
    )

    response = client.post(
        "/auth/forgot-password",
        json={"email": user.email}
    )

    assert response.status_code == 200
    assert len(sent) == 1

    match = re.search(
        r"token=([A-Za-z0-9_\-]+)",
        sent[0]
    )

    assert match is not None
    token = match.group(1)

    reset = client.post(
        "/auth/reset-password",
        json={
            "token": token,
            "password": "ChangedTrust@123",
            "confirm_password": "ChangedTrust@123"
        }
    )

    assert reset.status_code == 200

    user = db.session.get(User, user.id)
    assert verify_password(user.password_hash, "ChangedTrust@123")

    again = client.post(
        "/auth/reset-password",
        json={
            "token": token,
            "password": "AnotherTrust@123",
            "confirm_password": "AnotherTrust@123"
        }
    )

    assert again.status_code == 400


def test_resend_verification_sends_fresh_token(client, monkeypatch):
    from models.user import User
    from models.email_verification_token import EmailVerificationToken
    from security.email_verification import hash_verification_token
    from security.password import hash_password
    from extensions import db
    import re

    user = User(
        name="Resend Student",
        email="resend@example.com",
        password_hash=hash_password("TrustVault@123"),
        role="viewer",
        is_active=True,
        email_verified=False
    )

    db.session.add(user)
    db.session.commit()

    old = EmailVerificationToken(
        user_id=user.id,
        token_hash=hash_verification_token("old-resend-token"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )

    db.session.add(old)
    db.session.commit()

    sent = []

    monkeypatch.setattr(
        "routes.auth.send_email",
        lambda recipient, subject, body: sent.append(body)
    )

    response = client.post(
        "/auth/resend-verification",
        json={"email": user.email}
    )

    assert response.status_code == 200
    assert len(sent) == 1

    db.session.refresh(old)
    assert old.used_at is not None

    match = re.search(
        r"/auth/verify-email/([A-Za-z0-9_\-]+)",
        sent[0]
    )

    assert match is not None

    verification = client.get(
        f"/auth/verify-email/{match.group(1)}"
    )

    assert verification.status_code == 302

    db.session.refresh(user)
    assert user.email_verified is True


def test_owner_invitation_token_cannot_be_consumed_as_viewer_verification(client):
    from models.user import User
    from models.email_verification_token import EmailVerificationToken
    from security.email_verification import hash_verification_token
    from security.password import hash_password, verify_password
    from extensions import db

    owner = User(
        name="Invited Owner",
        email="invite-owner@example.com",
        password_hash=hash_password("TemporaryTrust@123"),
        role="owner",
        is_active=True,
        email_verified=False
    )

    db.session.add(owner)
    db.session.commit()

    token = "owner-invite-token-xyz"

    record = EmailVerificationToken(
        user_id=owner.id,
        token_hash=hash_verification_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )

    db.session.add(record)
    db.session.commit()

    wrong_flow = client.get(
        f"/auth/verify-email/{token}"
    )

    assert wrong_flow.status_code == 400
    assert owner.email_verified is False

    db.session.refresh(record)
    assert record.used_at is None

    accepted = client.post(
        f"/auth/accept-owner-invitation/{token}",
        json={
            "password": "OwnerChosenTrust@123",
            "confirm_password": "OwnerChosenTrust@123"
        }
    )

    assert accepted.status_code == 200

    db.session.refresh(owner)
    assert owner.email_verified is True
    assert verify_password(owner.password_hash, "OwnerChosenTrust@123")

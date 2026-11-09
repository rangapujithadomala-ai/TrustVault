import pytest

from app import create_app, _initialize_database
from config import (
    is_production_environment,
    require_nonproduction_demo_mode,
    validate_production_database,
)
from extensions import db
from models import User
from security.password import hash_password


def test_production_database_requires_remote_postgresql():
    for uri in (
        None,
        "not a database URL",
        "sqlite:///local.db",
        "postgresql://user:password@localhost/trustvault",
    ):
        with pytest.raises(RuntimeError, match="remote PostgreSQL"):
            validate_production_database(uri)

    validate_production_database(
        "postgresql+psycopg2://user:password@db.example:5432/trustvault"
    )


def test_production_detection_and_demo_seed_gate():
    assert is_production_environment({"APP_ENV": "production"})
    assert is_production_environment({"RAILWAY_PROJECT_ID": "project"})
    assert not is_production_environment({"APP_ENV": "development"})

    require_nonproduction_demo_mode({
        "APP_ENV": "development",
        "TRUSTVAULT_DEMO_MODE": "true",
    })
    with pytest.raises(RuntimeError, match="TRUSTVAULT_DEMO_MODE"):
        require_nonproduction_demo_mode({"APP_ENV": "development"})
    with pytest.raises(RuntimeError, match="not allowed in production"):
        require_nonproduction_demo_mode({
            "APP_ENV": "production",
            "TRUSTVAULT_DEMO_MODE": "true",
        })


def test_cookie_configuration_is_secure_in_production_and_local_safe():
    production_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "IS_PRODUCTION": True,
        "SQLALCHEMY_DATABASE_URI": (
            "postgresql+psycopg2://user:password@db.example:5432/trustvault"
        ),
    })
    assert production_app.config["SESSION_COOKIE_SECURE"] is True
    assert production_app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert production_app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    response = production_app.test_client().get("/login.html")
    cookie_headers = response.headers.getlist("Set-Cookie")
    assert any("Secure" in cookie for cookie in cookie_headers)
    assert any("HttpOnly" in cookie for cookie in cookie_headers)
    assert any("SameSite=Lax" in cookie for cookie in cookie_headers)

    local_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "IS_PRODUCTION": False,
        "SESSION_COOKIE_SECURE": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    assert local_app.config["SESSION_COOKIE_SECURE"] is False
    assert local_app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert local_app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_database_initialization_does_not_seed_or_change_users(app):
    with app.app_context():
        existing = User(
            name="Inactive account",
            email="inactive-existing@example.com",
            password_hash=hash_password("ExistingPassword@123"),
            role="admin",
            is_active=False,
            email_verified=False,
        )
        db.session.add(existing)
        db.session.commit()
        user_id = existing.id
        password_hash = existing.password_hash

    _initialize_database(app)

    with app.app_context():
        existing = db.session.get(User, user_id)
        assert existing is not None
        assert existing.is_active is False
        assert existing.email_verified is False
        assert existing.password_hash == password_hash
        assert User.query.filter(
            User.email.in_(
                [
                    "demo-admin@example.com",
                    "demo-owner@example.com",
                    "demo-viewer@example.com",
                ]
            )
        ).count() == 0


def test_production_app_fails_before_initialization_without_database_url():
    with pytest.raises(RuntimeError, match="remote PostgreSQL"):
        create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "IS_PRODUCTION": True,
            "SQLALCHEMY_DATABASE_URI": None,
        })

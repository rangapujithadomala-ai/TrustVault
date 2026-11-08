
import pytest
from flask import g

from app import create_app
from extensions import db


@pytest.fixture
def app():
    """Create a separate Flask application for testing."""

    test_app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key"
    })

    # The test fixture keeps an application context open so tests can
    # access db.session directly. Clear Flask-Login's cached user before
    # every request to simulate production's request-scoped context.
    @test_app.before_request
    def reset_test_login_cache():
        g.pop("_login_user", None)

    with test_app.app_context():
        db.create_all()

        yield test_app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app, monkeypatch):
    """Create a test client with isolated in-memory document storage."""

    storage = {}

    def fake_upload(storage_key, file_data, content_type):
        storage[storage_key] = bytes(file_data)
        return {"path": storage_key}

    def fake_download(storage_key):
        if storage_key not in storage:
            raise FileNotFoundError("Test document not found.")
        return storage[storage_key]

    def fake_delete(storage_key):
        storage.pop(storage_key, None)
        return {"message": "Deleted"}

    # Patch the functions imported by routes.documents.
    monkeypatch.setattr(
        "routes.documents.upload_file",
        fake_upload
    )
    monkeypatch.setattr(
        "routes.documents.download_file",
        fake_download
    )
    monkeypatch.setattr(
        "routes.documents.delete_file",
        fake_delete
    )

    return app.test_client()

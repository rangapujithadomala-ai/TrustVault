import pytest

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

    with test_app.app_context():
        db.create_all()

        yield test_app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client to send requests to the application."""

    return app.test_client()
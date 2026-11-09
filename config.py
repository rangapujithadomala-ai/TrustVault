import os
from datetime import timedelta

from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

load_dotenv()


def is_production_environment(environ=None):
    environ = os.environ if environ is None else environ
    app_environment = (
        environ.get("APP_ENV")
        or environ.get("FLASK_ENV")
        or environ.get("ENVIRONMENT")
        or ""
    ).strip().lower()
    return (
        app_environment in {"production", "prod"}
        or bool(
            environ.get("RAILWAY_ENVIRONMENT")
            or environ.get("RAILWAY_PROJECT_ID")
            or environ.get("RENDER")
        )
    )


def validate_production_database(database_uri):
    message = (
        "Production requires DATABASE_URL to reference a remote "
        "PostgreSQL database."
    )
    if not database_uri:
        raise RuntimeError(message)

    try:
        parsed = make_url(database_uri)
    except (ArgumentError, TypeError, ValueError):
        raise RuntimeError(message) from None

    if (
        parsed.get_backend_name() != "postgresql"
        or not parsed.host
        or parsed.host.lower() in {"localhost", "127.0.0.1", "::1"}
    ):
        raise RuntimeError(message)


def require_nonproduction_demo_mode(environ=None):
    environ = os.environ if environ is None else environ
    if (environ.get("TRUSTVAULT_DEMO_MODE") or "").strip().lower() != "true":
        raise RuntimeError(
            "Demo seeding is disabled. Set TRUSTVAULT_DEMO_MODE=true "
            "only in an isolated non-production environment."
        )
    if is_production_environment(environ):
        raise RuntimeError("Demo seeding is not allowed in production.")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    IS_PRODUCTION = is_production_environment()
    TRUSTVAULT_DEMO_MODE = (
        os.getenv("TRUSTVAULT_DEMO_MODE", "False").lower() == "true"
    )

    # Trusted public origin used when generating links sent by email.
    APP_BASE_URL = os.getenv(
        "APP_BASE_URL",
        "https://trustvault-production-e0fd.up.railway.app"
    ).rstrip("/")

    _db_url = os.getenv("DATABASE_URL")

    if _db_url and IS_PRODUCTION:
        try:
            _parsed_db_url = make_url(_db_url)
        except (ArgumentError, TypeError, ValueError):
            _parsed_db_url = None
        if (
            _parsed_db_url is None
            or not _parsed_db_url.host
            or _parsed_db_url.host.lower()
            in {"localhost", "127.0.0.1", "::1"}
        ):
            _db_url = None

    if _db_url:
        if _db_url.startswith("postgres://"):
            SQLALCHEMY_DATABASE_URI = _db_url.replace(
                "postgres://",
                "postgresql+psycopg2://",
                1
            )
        elif _db_url.startswith("postgresql://"):
            SQLALCHEMY_DATABASE_URI = _db_url.replace(
                "postgresql://",
                "postgresql+psycopg2://",
                1
            )
        else:
            SQLALCHEMY_DATABASE_URI = _db_url
    elif IS_PRODUCTION:
        SQLALCHEMY_DATABASE_URI = None
    else:
        _base_dir = os.path.abspath(os.path.dirname(__file__))
        _instance_dir = os.path.join(_base_dir, "instance")
        os.makedirs(_instance_dir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(_instance_dir, 'trustvault.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        True
        if IS_PRODUCTION
        else os.getenv("COOKIE_SECURE", "False").lower() == "true"
    )

    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    )

    TRUSTVAULT_STORAGE = os.getenv("TRUSTVAULT_STORAGE")

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
    SUPABASE_BUCKET = os.getenv(
        "SUPABASE_BUCKET",
        "trustvault-documents"
    )

    TRUST_PROXY = (
        os.getenv("TRUST_PROXY", "False").lower() == "true"
    )

    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = (
        os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    )
    MAIL_USE_SSL = (
        os.getenv("MAIL_USE_SSL", "False").lower() == "true"
    )
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = (
        os.getenv("MAIL_DEFAULT_SENDER") or MAIL_USERNAME
    )
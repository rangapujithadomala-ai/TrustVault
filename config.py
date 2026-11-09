import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Trusted public origin used when generating links sent by email.
    APP_BASE_URL = os.getenv(
        "APP_BASE_URL",
        "https://trustvault-production-e0fd.up.railway.app"
    ).rstrip("/")

    _db_url = os.getenv("DATABASE_URL")

    # If running in cloud deployment (such as Railway or Render) but DATABASE_URL points to localhost,
    # localhost is unreachable inside the container; fall back to SQLite unless remote DB is supplied.
    is_cloud_deploy = bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_PROJECT_ID")
        or os.getenv("RENDER")
    )

    if _db_url and is_cloud_deploy and ("@localhost" in _db_url or "@127.0.0.1" in _db_url):
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
    else:
        # Fallback to local instance database when DATABASE_URL is not set or unreachable in container
        _base_dir = os.path.abspath(os.path.dirname(__file__))
        _instance_dir = os.path.join(_base_dir, "instance")
        os.makedirs(_instance_dir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(_instance_dir, 'trustvault.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        os.getenv("COOKIE_SECURE", "False").lower() == "true"
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
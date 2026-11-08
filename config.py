
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    if SQLALCHEMY_DATABASE_URI:
        if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
            SQLALCHEMY_DATABASE_URI = (
                SQLALCHEMY_DATABASE_URI.replace(
                    "postgres://",
                    "postgresql+psycopg2://",
                    1
                )
            )
        elif SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
            SQLALCHEMY_DATABASE_URI = (
                SQLALCHEMY_DATABASE_URI.replace(
                    "postgresql://",
                    "postgresql+psycopg2://",
                    1
                )
            )

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

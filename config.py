
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:

    # Flask security
    SECRET_KEY = os.getenv("SECRET_KEY")

    # PostgreSQL database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set COOKIE_SECURE=true on HTTPS deployment.
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "False").lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "30")))
    TRUSTVAULT_STORAGE = os.getenv("TRUSTVAULT_STORAGE")
    TRUST_PROXY = os.getenv("TRUST_PROXY", "False").lower() == "true"

    # Gmail SMTP configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False").lower() == "true"

    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

    MAIL_DEFAULT_SENDER = (
        os.getenv("MAIL_DEFAULT_SENDER")
        or MAIL_USERNAME
    )

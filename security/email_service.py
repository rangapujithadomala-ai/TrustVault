
from flask import current_app
from flask_mail import Message

from extensions import mail


def send_email(recipient, subject, body):
    """Send an email using the configured mail service."""

    current_app.logger.warning(
        "SMTP DIAGNOSTIC: username_present=%s, password_present=%s, "
        "sender_present=%s, server=%s, port=%s, tls=%s, ssl=%s",
        bool(current_app.config.get("MAIL_USERNAME")),
        bool(current_app.config.get("MAIL_PASSWORD")),
        bool(current_app.config.get("MAIL_DEFAULT_SENDER")),
        current_app.config.get("MAIL_SERVER"),
        current_app.config.get("MAIL_PORT"),
        current_app.config.get("MAIL_USE_TLS"),
        current_app.config.get("MAIL_USE_SSL")
    )

    message = Message(
        subject=subject,
        recipients=[recipient],
        body=body
    )

    mail.send(message)

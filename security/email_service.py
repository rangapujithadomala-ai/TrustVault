
from flask import current_app
from flask_mail import Message

from extensions import mail


def send_email(recipient, subject, body):
    """Send an email using the configured mail service."""

    print(
    "SMTP DIAGNOSTIC:",
    {
        "username_present": bool(current_app.config.get("MAIL_USERNAME")),
        "password_present": bool(current_app.config.get("MAIL_PASSWORD")),
        "sender_present": bool(current_app.config.get("MAIL_DEFAULT_SENDER")),
        "server": current_app.config.get("MAIL_SERVER"),
        "port": current_app.config.get("MAIL_PORT"),
        "tls": current_app.config.get("MAIL_USE_TLS"),
        "ssl": current_app.config.get("MAIL_USE_SSL"),
    },
    flush=True
)

    message = Message(
        subject=subject,
        recipients=[recipient],
        body=body
    )

    mail.send(message)

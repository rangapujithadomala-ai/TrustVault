from flask_mail import Message

from extensions import mail


def send_email(recipient, subject, body):
    """Send an email using the configured mail service."""

    message = Message(
        subject=subject,
        recipients=[recipient],
        body=body
    )

    mail.send(message)
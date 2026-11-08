from extensions import db
from models import User, Notification


def notify_admins(
    notification_type,
    message,
    related_document_id=None
):
    """
    Create a notification for every active Admin.

    The caller is responsible for committing the transaction.
    """

    admins = User.query.filter_by(
        role="admin",
        is_active=True
    ).all()

    for admin in admins:
        notification = Notification(
            recipient_user_id=admin.id,
            notification_type=notification_type,
            message=message,
            related_document_id=related_document_id
        )

        db.session.add(notification)

    return len(admins)


def notify_user(
    user_id,
    notification_type,
    message,
    related_document_id=None
):
    """
    Create a notification for one specific user.

    The caller is responsible for committing the transaction.
    """

    notification = Notification(
        recipient_user_id=user_id,
        notification_type=notification_type,
        message=message,
        related_document_id=related_document_id
    )

    db.session.add(notification)
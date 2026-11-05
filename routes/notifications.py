from datetime import datetime, timezone

from flask import Blueprint, jsonify, abort
from flask_login import login_required, current_user

from extensions import db
from models import Notification


notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/notifications"
)


@notifications_bp.route("/", methods=["GET"])
@login_required
def get_notifications():
    items = (
        Notification.query
        .filter_by(recipient_user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    unread_count = sum(
        1 for item in items if item.read_at is None
    )

    return jsonify({
        "notifications": [
            {
                "id": item.id,
                "type": item.notification_type,
                "message": item.message,
                "created_at": (
                    item.created_at.isoformat()
                    if item.created_at else None
                ),
                "read": item.read_at is not None,
                "related_document_id": item.related_document_id
            }
            for item in items
        ],
        "unread_count": unread_count
    })


@notifications_bp.route("/<notification_id>/read", methods=["POST"])
@login_required
def mark_as_read(notification_id):
    item = Notification.query.filter_by(
        id=notification_id,
        recipient_user_id=current_user.id
    ).first()

    if item is None:
        abort(404)

    if item.read_at is None:
        item.read_at = datetime.now(timezone.utc)
        db.session.commit()

    return jsonify({
        "message": "Notification marked as read.",
        "id": item.id
    })


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_as_read():
    now = datetime.now(timezone.utc)

    (
        Notification.query
        .filter_by(
            recipient_user_id=current_user.id,
            read_at=None
        )
        .update(
            {"read_at": now},
            synchronize_session=False
        )
    )

    db.session.commit()

    return jsonify({
        "message": "All notifications marked as read."
    })
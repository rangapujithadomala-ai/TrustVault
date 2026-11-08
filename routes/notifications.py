
from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, jsonify, abort
from flask_login import current_user

from extensions import db
from models import Notification


notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/notifications"
)


# ---------------------------------------------------------
# API AUTHENTICATION
# Return JSON 401 instead of redirecting to login and
# generating a Flask flash message.
# ---------------------------------------------------------

def api_login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                "error": "Authentication required."
            }), 401

        return view(*args, **kwargs)

    return wrapped_view


# ---------------------------------------------------------
# GET NOTIFICATIONS
# ---------------------------------------------------------

@notifications_bp.route("/", methods=["GET"])
@api_login_required
def get_notifications():

    items = (
        Notification.query
        .filter_by(recipient_user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    unread_count = sum(
        1 for item in items
        if item.read_at is None
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


# ---------------------------------------------------------
# MARK ONE NOTIFICATION AS READ
# ---------------------------------------------------------

@notifications_bp.route(
    "/<notification_id>/read",
    methods=["POST"]
)
@api_login_required
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


# ---------------------------------------------------------
# MARK ALL NOTIFICATIONS AS READ
# ---------------------------------------------------------

@notifications_bp.route("/read-all", methods=["POST"])
@api_login_required
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


# ---------------------------------------------------------
# DELETE ONE NOTIFICATION
# ---------------------------------------------------------

@notifications_bp.route(
    "/<notification_id>",
    methods=["DELETE"]
)
@api_login_required
def delete_notification(notification_id):

    item = Notification.query.filter_by(
        id=notification_id,
        recipient_user_id=current_user.id
    ).first()

    if item is None:
        abort(404)

    db.session.delete(item)
    db.session.commit()

    return jsonify({
        "message": "Notification deleted."
    })


# ---------------------------------------------------------
# CLEAR READ NOTIFICATIONS
# ---------------------------------------------------------

@notifications_bp.route("/clear-read", methods=["POST"])
@api_login_required
def clear_read_notifications():

    (
        Notification.query
        .filter_by(recipient_user_id=current_user.id)
        .filter(Notification.read_at.isnot(None))
        .delete(synchronize_session=False)
    )

    db.session.commit()

    return jsonify({
        "message": "Read notifications cleared."
    })


# ---------------------------------------------------------
# CLEAR ALL NOTIFICATIONS
# ---------------------------------------------------------

@notifications_bp.route("/clear-all", methods=["POST"])
@api_login_required
def clear_all_notifications():

    Notification.query.filter_by(
        recipient_user_id=current_user.id
    ).delete(synchronize_session=False)

    db.session.commit()

    return jsonify({
        "message": "Notifications cleared."
    })

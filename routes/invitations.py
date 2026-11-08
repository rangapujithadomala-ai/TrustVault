
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint,
    request,
    jsonify,
    redirect,
    render_template_string,
    session,
    current_app,
)

from flask_login import (
    current_user,
    login_required,
    login_user,
)

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from extensions import db

from models import (
    Document,
    DocumentInvitation,
    DocumentInvitationItem,
    Permission,
    User,
    Notification,
)

from security.audit import append_audit
from security.email_service import send_email
from security.password import validate_password, hash_password


invitations_bp = Blueprint(
    "invitations",
    __name__,
    url_prefix="/invitations"
)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc(value):
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _invitation_is_valid(invitation):
    if invitation is None:
        return False

    expires_at = _utc(invitation.expires_at)

    return (
        invitation.accepted_at is None
        and invitation.revoked_at is None
        and expires_at is not None
        and expires_at > datetime.now(timezone.utc)
    )


def _get_invitation_documents(invitation):
    """
    New invitations use child items.
    Older invitations use document_id and permission_type.
    """

    items = (
        DocumentInvitationItem.query
        .filter_by(invitation_id=invitation.id)
        .all()
    )

    if items:
        result = []

        for item in items:
            document = Document.query.get(item.document_id)

            if document:
                result.append({
                    "document": document,
                    "permission_type": item.permission_type,
                })

        return result

    # Backwards compatibility for old single-document invitations.
    document = Document.query.get(invitation.document_id)

    if not document:
        return []

    return [{
        "document": document,
        "permission_type": invitation.permission_type,
    }]


def _revoke_overlapping_invitations(owner_id, email, document_ids):
    """
    Revoke previous pending invitations when they overlap
    with newly selected documents for the same recipient.
    """

    now = datetime.now(timezone.utc)

    previous_invitations = (
        DocumentInvitation.query
        .filter_by(
            invited_by=owner_id,
            invited_email=email,
            accepted_at=None,
            revoked_at=None,
        )
        .all()
    )

    selected_ids = set(document_ids)

    for old_invitation in previous_invitations:

        old_items = (
            DocumentInvitationItem.query
            .filter_by(invitation_id=old_invitation.id)
            .all()
        )

        if old_items:
            old_document_ids = {
                item.document_id for item in old_items
            }
        else:
            old_document_ids = {
                old_invitation.document_id
            }

        if selected_ids.intersection(old_document_ids):
            old_invitation.revoked_at = now


def _validate_owner():
    if not current_user.is_authenticated:
        return False

    return (
        getattr(current_user, "role", None) == "owner"
        and getattr(current_user, "is_active", False)
    )


def _existing_owner_error(email):
    """
    Return an error response if the email belongs to an Owner.
    Otherwise, return None.
    """

    existing_user = User.query.filter(
        func.lower(User.email) == email
    ).first()

    if existing_user and existing_user.role == "owner":
        return jsonify({
            "error": (
                "This email address already belongs to an Owner. "
                "You cannot send a Viewer invitation to an Owner account."
            )
        }), 409

    return None


def _send_invitation_email(email, invitation_url, documents):

    document_lines = []

    for item in documents:
        document_lines.append(
            f"- {item['document_title']} "
            f"(Permission: {item['permission_type'].upper()})"
        )

    document_list = "\n".join(document_lines)

    body = f"""
Hello,

You have been invited to access documents on TrustVault.

Documents shared with you:

{document_list}

Open the following invitation link:

{invitation_url}

If you do not have a TrustVault account, use this link
to create your Viewer account and set your password.

If you already have an account, log in using the invited
email address and open this invitation link again.

Invited email: {email}

This invitation expires in 48 hours.

If you were not expecting this invitation, you can ignore
this email.

TrustVault
"""

    send_email(
        email,
        "TrustVault - Document Sharing Invitation",
        body
    )


def _render_invitation_page(
    invitation,
    inviter,
    invitation_documents,
    existing_user=None,
    error=None,
):
    """
    Displays the invitation details and either:
    - Viewer account creation form, or
    - Login instructions for an existing account.
    """

    return render_template_string(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1">

            <title>Accept Invitation | TrustVault</title>

            <style>
                * {
                    box-sizing: border-box;
                }

                body {
                    margin: 0;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 24px;
                    background: #f4f7fb;
                    color: #1e293b;
                    font-family: "Segoe UI", Arial, sans-serif;
                }

                .card {
                    width: 100%;
                    max-width: 490px;
                    padding: 36px;
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 18px;
                    box-shadow: 0 12px 35px rgba(15, 23, 42, 0.08);
                }

                .brand {
                    margin-bottom: 24px;
                    color: #1e3a8a;
                    font-size: 14px;
                    font-weight: 700;
                    letter-spacing: 2px;
                }

                h1 {
                    margin: 0 0 12px;
                    font-size: 25px;
                    color: #17365d;
                }

                p {
                    color: #64748b;
                    line-height: 1.65;
                    font-size: 14px;
                }

                .email {
                    padding: 12px;
                    background: #f1f5f9;
                    border-radius: 8px;
                    color: #17365d;
                    font-weight: 600;
                    overflow-wrap: anywhere;
                }

                .documents {
                    margin: 20px 0;
                    padding: 16px;
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 10px;
                }

                .documents h3 {
                    margin: 0 0 12px;
                    font-size: 15px;
                }

                .documents ul {
                    margin: 0;
                    padding-left: 20px;
                }

                .documents li {
                    margin: 9px 0;
                    color: #475569;
                    font-size: 14px;
                    overflow-wrap: anywhere;
                }

                label {
                    display: block;
                    margin: 16px 0 7px;
                    color: #334155;
                    font-size: 14px;
                    font-weight: 600;
                }

                input {
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    font-size: 15px;
                    outline: none;
                }

                input:focus {
                    border-color: #2563eb;
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
                }

                button,
                .button {
                    display: block;
                    width: 100%;
                    margin-top: 22px;
                    padding: 13px;
                    border: none;
                    border-radius: 8px;
                    background: #173f70;
                    color: white;
                    text-align: center;
                    text-decoration: none;
                    font-size: 15px;
                    font-weight: 600;
                    cursor: pointer;
                }

                button:hover,
                .button:hover {
                    background: #1d4ed8;
                }

                .error {
                    padding: 12px;
                    margin: 15px 0;
                    border-radius: 8px;
                    background: #fff1f2;
                    color: #be123c;
                    font-size: 14px;
                }

                .footer {
                    margin-top: 22px;
                    text-align: center;
                    font-size: 13px;
                }

                .footer a {
                    color: #245b9e;
                    font-weight: 600;
                    text-decoration: none;
                }

                .note {
                    margin-top: 16px;
                    font-size: 12px;
                    color: #94a3b8;
                }

                @media (max-width: 480px) {
                    .card {
                        padding: 25px 20px;
                    }
                }
            </style>
        </head>

        <body>
            <main class="card">

                <div class="brand">TRUSTVAULT</div>

                <h1>You've received an invitation</h1>

                <p>
                    <strong>{{ inviter.name }}</strong>
                    invited you to access documents on TrustVault.
                </p>

                <p class="email">{{ invitation.invited_email }}</p>

                <div class="documents">
                    <h3>Documents included</h3>

                    <ul>
                        {% for item in invitation_documents %}
                            <li>
                                {{ item.document.title }}
                                — {{ item.permission_type.upper() }} access
                            </li>
                        {% endfor %}
                    </ul>
                </div>

                {% if error %}
                    <div class="error">{{ error }}</div>
                {% endif %}

                {% if existing_user %}

                    <h3>Account already exists</h3>

                    <p>
                        An account is already registered with this
                        invited email address.
                    </p>

                    {% if not existing_user.email_verified %}
                        <p>
                            Please complete your email verification
                            before accepting this invitation.
                        </p>
                    {% else %}
                        <p>
                            Log in using the invited email address.
                            You will be returned to this invitation
                            after login.
                        </p>
                    {% endif %}

                    <a class="button" href="/login.html">
                        Go to Login
                    </a>

                {% else %}

                    <p>
                        Create your Viewer account to securely
                        accept this document invitation.
                    </p>

                    <form method="POST">

                        <input type="hidden"
                               name="csrf_token"
                               value="{{ csrf_token() }}">

                        <label for="name">Your name</label>

                        <input
                            type="text"
                            id="name"
                            name="name"
                            minlength="2"
                            maxlength="100"
                            required
                            autocomplete="name"
                        >

                        <label for="password">Create password</label>

                        <input
                            type="password"
                            id="password"
                            name="password"
                            required
                            autocomplete="new-password"
                        >

                        <label for="confirm_password">
                            Confirm password
                        </label>

                        <input
                            type="password"
                            id="confirm_password"
                            name="confirm_password"
                            required
                            autocomplete="new-password"
                        >

                        <button type="submit">
                            Create Account & Accept Invitation
                        </button>

                    </form>

                    <p class="footer">
                        Already have an account?
                        <a href="/login.html">Log in</a>
                    </p>

                    <p class="note">
                        Your invitation is valid for 48 hours.
                    </p>

                {% endif %}

            </main>
        </body>
        </html>
        """,
        invitation=invitation,
        inviter=inviter,
        invitation_documents=invitation_documents,
        existing_user=existing_user,
        error=error,
    )


# ---------------------------------------------------------
# LEGACY SINGLE-DOCUMENT INVITATION
# ---------------------------------------------------------

@invitations_bp.route(
    "/documents/<doc_id>",
    methods=["POST"]
)
@login_required
def create_invitation(doc_id):

    if not _validate_owner():
        return jsonify({
            "error": "Only active document owners can invite users."
        }), 403

    data = request.get_json(silent=True) or {}

    email = str(data.get("email", "")).strip().lower()

    permission_type = str(
        data.get("permission_type", "read")
    ).strip().lower()

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({
            "error": "Enter a valid email address."
        }), 400

    if email == current_user.email.lower():
        return jsonify({
            "error": "You cannot invite yourself."
        }), 400

    owner_error = _existing_owner_error(email)

    if owner_error:
        return owner_error

    if permission_type not in ("read", "edit"):
        return jsonify({
            "error": "Permission must be read or edit."
        }), 400

    document = Document.query.filter_by(
        id=doc_id,
        owner_id=current_user.id
    ).filter(
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        return jsonify({
            "error": "Document not found or you do not own it."
        }), 404

    try:
        _revoke_overlapping_invitations(
            current_user.id,
            email,
            [document.id]
        )

        raw_token = secrets.token_urlsafe(32)

        invitation = DocumentInvitation(
            document_id=document.id,
            invited_email=email,
            permission_type=permission_type,
            token_hash=_hash_token(raw_token),
            invited_by=current_user.id,
            expires_at=(
                datetime.now(timezone.utc)
                + timedelta(hours=48)
            ),
        )

        db.session.add(invitation)

        append_audit(
            current_user.id,
            "document_invitation_created",
            "success",
            document_id=document.id,
            details={
                "invited_email": email,
                "permission_type": permission_type,
            }
        )

        db.session.commit()

        invitation_url = (
            current_app.config["APP_BASE_URL"]
            + "/invitations/accept/"
            + raw_token
        )

        email_sent = True

        try:
            _send_invitation_email(
                email,
                invitation_url,
                [{
                    "document_title": document.title,
                    "permission_type": permission_type,
                }]
            )

        except Exception:
            email_sent = False

            current_app.logger.exception(
                "TrustVault invitation email could not be sent."
            )

        return jsonify({
            "message": (
                "Invitation created successfully."
                if email_sent
                else "Invitation created. Email delivery failed; copy the link."
            ),
            "invitation_url": invitation_url,
            "email_sent": email_sent,
            "expires_in_hours": 48,
        }), 201

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Single-document invitation creation failed."
        )

        return jsonify({
            "error": "Could not create the invitation."
        }), 500


# ---------------------------------------------------------
# MULTI-DOCUMENT INVITATION - ONE LINK
# ---------------------------------------------------------

@invitations_bp.route("/bulk", methods=["POST"])
@login_required
def create_bulk_invitation():

    if not _validate_owner():
        return jsonify({
            "error": "Only active document owners can invite users."
        }), 403

    data = request.get_json(silent=True) or {}

    email = str(data.get("email", "")).strip().lower()

    selected_documents = data.get("documents")

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({
            "error": "Enter a valid email address."
        }), 400

    if email == current_user.email.lower():
        return jsonify({
            "error": "You cannot invite yourself."
        }), 400

    owner_error = _existing_owner_error(email)

    if owner_error:
        return owner_error

    if (
        not isinstance(selected_documents, list)
        or not selected_documents
        or len(selected_documents) > 50
    ):
        return jsonify({
            "error": "Select between 1 and 50 documents."
        }), 400

    validated_documents = []
    seen_ids = set()

    # Validate every selected document before creating anything.
    for selected in selected_documents:

        if not isinstance(selected, dict):
            return jsonify({
                "error": "Invalid document selection."
            }), 400

        document_id = str(
            selected.get("document_id", "")
        ).strip()

        permission_type = str(
            selected.get("permission_type", "read")
        ).strip().lower()

        if not document_id:
            return jsonify({
                "error": "A selected document is missing its ID."
            }), 400

        if document_id in seen_ids:
            return jsonify({
                "error": "A document was selected more than once."
            }), 400

        if permission_type not in ("read", "edit"):
            return jsonify({
                "error": "Permission must be read or edit."
            }), 400

        document = Document.query.filter_by(
            id=document_id,
            owner_id=current_user.id
        ).filter(
            Document.deleted_at.is_(None)
        ).first()

        if not document:
            return jsonify({
                "error": "One or more selected documents are unavailable."
            }), 400

        seen_ids.add(document_id)

        validated_documents.append({
            "document": document,
            "permission_type": permission_type,
        })

    try:
        document_ids = [
            item["document"].id
            for item in validated_documents
        ]

        _revoke_overlapping_invitations(
            current_user.id,
            email,
            document_ids
        )

        # Generate ONE token for the complete selection.
        raw_token = secrets.token_urlsafe(32)

        first_item = validated_documents[0]

        invitation = DocumentInvitation(
            # Keep original columns populated for compatibility.
            document_id=first_item["document"].id,
            invited_email=email,
            permission_type=first_item["permission_type"],
            token_hash=_hash_token(raw_token),
            invited_by=current_user.id,
            expires_at=(
                datetime.now(timezone.utc)
                + timedelta(hours=48)
            ),
        )

        db.session.add(invitation)
        db.session.flush()

        response_documents = []

        # Store every selected document under the same invitation.
        for item in validated_documents:

            document = item["document"]
            permission_type = item["permission_type"]

            invitation_item = DocumentInvitationItem(
                invitation_id=invitation.id,
                document_id=document.id,
                permission_type=permission_type,
            )

            db.session.add(invitation_item)

            response_documents.append({
                "document_title": document.title,
                "permission_type": permission_type,
            })

            append_audit(
                current_user.id,
                "document_invitation_created",
                "success",
                document_id=document.id,
                details={
                    "invited_email": email,
                    "permission_type": permission_type,
                    "bulk_invitation": True,
                    "invitation_id": invitation.id,
                }
            )

        db.session.commit()

        # All selected documents share this ONE invitation URL.
        invitation_url = (
            current_app.config["APP_BASE_URL"]
            + "/invitations/accept/"
            + raw_token
        )

        email_sent = True

        try:
            _send_invitation_email(
                email,
                invitation_url,
                response_documents
            )

        except Exception:
            email_sent = False

            current_app.logger.exception(
                "Bulk invitation email could not be sent."
            )

        return jsonify({
            "message": (
                "Invitation created successfully for all selected documents."
                if email_sent
                else "Invitation created. Email delivery failed; copy the invitation link."
            ),
            "email_sent": email_sent,
            "invitation_url": invitation_url,
            "documents": response_documents,
            "expires_in_hours": 48,
        }), 201

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Bulk invitation creation failed."
        )

        return jsonify({
            "error": "Could not create the document invitation."
        }), 500


# ---------------------------------------------------------
# ACCEPT INVITATION
# Supports:
# - Old single-document invitations
# - New multi-document invitations
# - New Viewer account creation
# - Existing Viewer login and acceptance
# ---------------------------------------------------------

@invitations_bp.route(
    "/accept/<token>",
    methods=["GET", "POST"]
)
def accept_invitation(token):

    token_hash = _hash_token(token)

    invitation = DocumentInvitation.query.filter_by(
        token_hash=token_hash
    ).first()

    # -----------------------------------------------------
    # INVALID / EXPIRED / REVOKED / ALREADY USED INVITATION
    # -----------------------------------------------------

    if not _invitation_is_valid(invitation):

        dashboard_url = None

        if current_user.is_authenticated:

            if current_user.role == "owner":
                dashboard_url = "/owner/dashboard"

            elif current_user.role == "viewer":
                dashboard_url = "/viewer/dashboard"

            elif current_user.role == "admin":
                dashboard_url = "/admin/dashboard"

        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1">

            <title>Invitation Unavailable | TrustVault</title>

            <style>
                * {
                    box-sizing: border-box;
                }

                body {
                    margin: 0;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 24px;
                    background: #f4f7fb;
                    color: #1e293b;
                    font-family: "Segoe UI", Arial, sans-serif;
                }

                .card {
                    width: 100%;
                    max-width: 480px;
                    padding: 40px 32px;
                    text-align: center;
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 18px;
                    box-shadow: 0 12px 35px rgba(15, 23, 42, 0.08);
                }

                .icon {
                    width: 64px;
                    height: 64px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 22px;
                    border-radius: 50%;
                    background: #fff1f2;
                    color: #be123c;
                    font-size: 30px;
                }

                h1 {
                    margin: 0 0 14px;
                    font-size: 25px;
                }

                p {
                    color: #64748b;
                    line-height: 1.7;
                    font-size: 15px;
                }

                .button {
                    display: inline-block;
                    margin-top: 12px;
                    padding: 12px 22px;
                    border-radius: 9px;
                    background: #1e3a8a;
                    color: white;
                    text-decoration: none;
                    font-weight: 600;
                }

                .brand {
                    margin-top: 28px;
                    color: #94a3b8;
                    font-size: 13px;
                    letter-spacing: 1px;
                }
            </style>
        </head>

        <body>
            <main class="card">

                <div class="icon">!</div>

                <h1>Invitation Link Unavailable</h1>

                <p>
                    This invitation is no longer available.
                    It may have expired, been revoked, or already
                    been used.
                </p>

                <p>
                    For security reasons, access cannot be granted
                    through this link. Please contact the document
                    owner and request a new invitation.
                </p>

                {% if dashboard_url %}
                    <a class="button" href="{{ dashboard_url }}">
                        Back to Dashboard
                    </a>
                {% else %}
                    <a class="button" href="/login.html">
                        Go to Login
                    </a>
                {% endif %}

                <div class="brand">TRUSTVAULT</div>

            </main>
        </body>
        </html>
        """

        return render_template_string(
            html,
            dashboard_url=dashboard_url
        ), 410

    # -----------------------------------------------------
    # VALIDATE INVITER
    # -----------------------------------------------------

    inviter = User.query.get(invitation.invited_by)

    if not inviter or not inviter.is_active:
        return "The inviting account is no longer active.", 400

    invitation_documents = _get_invitation_documents(invitation)

    if not invitation_documents:
        return "The documents in this invitation are unavailable.", 400

    # Every document must still belong to the original inviter.
    for item in invitation_documents:

        document = item["document"]

        if (
            document.owner_id != invitation.invited_by
            or document.deleted_at is not None
        ):
            return (
                "One or more documents in this invitation are unavailable.",
                400
            )

    # -----------------------------------------------------
    # NEW VIEWER ACCOUNT CREATION THROUGH INVITATION
    # -----------------------------------------------------

    if not current_user.is_authenticated:

        session["_trustvault_invitation_next"] = request.path

        existing_user = User.query.filter(
            func.lower(User.email)
            == invitation.invited_email.lower()
        ).first()

        # -------------------------------------------------
        # EXISTING ACCOUNT
        # -------------------------------------------------

        if existing_user:

            # An Owner account cannot accept a Viewer invitation.
            if existing_user.role == "owner":
                return _render_invitation_page(
                    invitation,
                    inviter,
                    invitation_documents,
                    existing_user=existing_user,
                    error=(
                        "This invitation is for Viewer access. "
                        "This email already belongs to an Owner account, "
                        "so it cannot accept this invitation."
                    )
                ), 409

            if request.method == "POST":
                return _render_invitation_page(
                    invitation,
                    inviter,
                    invitation_documents,
                    existing_user=existing_user,
                    error="This email already has an account. Please log in."
                ), 409

            return _render_invitation_page(
                invitation,
                inviter,
                invitation_documents,
                existing_user=existing_user,
            )

        # -------------------------------------------------
        # CREATE NEW VIEWER ACCOUNT
        # -------------------------------------------------

        if request.method == "POST":

            name = (request.form.get("name") or "").strip()

            password = request.form.get("password") or ""

            confirm_password = (
                request.form.get("confirm_password") or ""
            )

            if len(name) < 2 or len(name) > 100:

                return _render_invitation_page(
                    invitation,
                    inviter,
                    invitation_documents,
                    error="Please enter a name between 2 and 100 characters."
                ), 400

            if password != confirm_password:

                return _render_invitation_page(
                    invitation,
                    inviter,
                    invitation_documents,
                    error="Passwords do not match."
                ), 400

            is_valid, message = validate_password(password)

            if not is_valid:

                return _render_invitation_page(
                    invitation,
                    inviter,
                    invitation_documents,
                    error=message
                ), 400

            new_user = User(
                name=name,
                email=invitation.invited_email.lower(),
                password_hash=hash_password(password),
                role="viewer",
                is_active=True,
                email_verified=True,
            )

            try:
                db.session.add(new_user)
                db.session.flush()

                append_audit(
                    new_user.id,
                    "viewer_account_created_via_invitation",
                    "success",
                    details={
                        "invitation_id": invitation.id,
                        "invited_by": invitation.invited_by,
                    }
                )

                db.session.commit()

            except IntegrityError:
                db.session.rollback()

                existing_user = User.query.filter(
                    func.lower(User.email)
                    == invitation.invited_email.lower()
                ).first()

                return _render_invitation_page(
                    invitation,
                    inviter,
                    invitation_documents,
                    existing_user=existing_user,
                    error="An account already exists for this email. Please log in."
                ), 409

            except Exception:
                db.session.rollback()

                current_app.logger.exception(
                    "Viewer account creation through invitation failed."
                )

                return (
                    "Could not create your account. Please try again.",
                    500
                )

            # Log in the newly created Viewer.
            login_user(
                new_user,
                remember=False,
                fresh=True
            )

            session.permanent = True

            session["_trustvault_password_snapshot"] = (
                hashlib.sha256(
                    new_user.password_hash.encode("utf-8")
                ).hexdigest()
            )

            # Reopen the same invitation URL.
            # The authenticated acceptance logic below will grant
            # the document permissions.
            return redirect(request.path)

        # Show the new Viewer account creation form.
        return _render_invitation_page(
            invitation,
            inviter,
            invitation_documents,
        )

    # -----------------------------------------------------
    # AUTHENTICATED USER VALIDATION
    # -----------------------------------------------------

    if not current_user.is_active:
        return "Your account is inactive.", 403

    if not current_user.email_verified:
        return (
            "Please verify your email address before accepting this invitation.",
            403
        )

    # Only Viewer accounts can accept document-sharing invitations.
    if current_user.role == "owner":
        return (
            "This invitation is for Viewer access. "
            "Your account already has the Owner role, so you cannot accept it.",
            403
        )

    if current_user.role != "viewer":
        return "Your account role cannot accept this invitation.", 403

    if current_user.email.lower() != invitation.invited_email.lower():
        return (
            "This invitation was sent to a different email address. "
            "Please log in using the invited email address.",
            403
        )

    # -----------------------------------------------------
    # ACCEPT INVITATION AND GRANT ALL DOCUMENT PERMISSIONS
    # -----------------------------------------------------

    try:
        # Lock the invitation to prevent simultaneous acceptance.
        locked_invitation = (
            DocumentInvitation.query
            .filter_by(id=invitation.id)
            .with_for_update()
            .first()
        )

        if not _invitation_is_valid(locked_invitation):

            db.session.rollback()

            return (
                "This invitation is no longer available.",
                400
            )

        locked_inviter = User.query.get(
            locked_invitation.invited_by
        )

        if not locked_inviter or not locked_inviter.is_active:

            db.session.rollback()

            return "The inviting account is no longer active.", 400

        documents_to_grant = _get_invitation_documents(
            locked_invitation
        )

        if not documents_to_grant:

            db.session.rollback()

            return "The invited documents are unavailable.", 400

        now = datetime.now(timezone.utc)

        # Validate all documents before granting any permissions.
        for item in documents_to_grant:

            document = item["document"]

            if (
                document.owner_id != locked_invitation.invited_by
                or document.deleted_at is not None
            ):
                db.session.rollback()

                return (
                    "One or more documents are no longer available.",
                    400
                )

        # Grant or update permission for EVERY document.
        for item in documents_to_grant:

            document = item["document"]

            permission_type = item["permission_type"]

            active_permission = Permission.query.filter_by(
                document_id=document.id,
                user_id=current_user.id,
                revoked_at=None,
            ).first()

            if active_permission:

                active_permission.permission_type = permission_type

                active_permission.granted_by = (
                    locked_invitation.invited_by
                )

                active_permission.granted_at = now

            else:

                permission = Permission(
                    document_id=document.id,
                    user_id=current_user.id,
                    permission_type=permission_type,
                    granted_by=locked_invitation.invited_by,
                    granted_at=now,
                )

                db.session.add(permission)

            # Create notification for the recipient.
            db.session.add(
                Notification(
                    recipient_user_id=current_user.id,
                    notification_type="document_shared",
                    message=(
                        f"{locked_inviter.name} shared "
                        f"'{document.title}' with you "
                        f"({permission_type.upper()} access)."
                    ),
                    related_document_id=document.id,
                )
            )

            # Record invitation acceptance.
            append_audit(
                current_user.id,
                "document_invitation_accepted",
                "success",
                document_id=document.id,
                target_user_id=current_user.id,
                details={
                    "invitation_id": locked_invitation.id,
                    "invited_by": locked_invitation.invited_by,
                }
            )

            # Record permission grant.
            append_audit(
                locked_invitation.invited_by,
                "permission_grant",
                "success",
                document_id=document.id,
                target_user_id=current_user.id,
                details={
                    "permission_type": permission_type,
                    "invitation_id": locked_invitation.id,
                }
            )

        # Mark the shared invitation as accepted only once.
        locked_invitation.accepted_at = now

        locked_invitation.accepted_by = current_user.id

        db.session.commit()

        # Redirect the Viewer to their shared documents.
        return redirect("/viewer/shared-with-me")

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Invitation acceptance failed."
        )

        return (
            "Could not accept this invitation. Please try again.",
            500
        )

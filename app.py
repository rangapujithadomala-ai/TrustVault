import os
import uuid
import hashlib
from dotenv import load_dotenv

# Load environment variables before loading Config
load_dotenv()

from werkzeug.middleware.proxy_fix import ProxyFix

from flask import (
    Flask,
    render_template,
    send_from_directory,
    abort,
    redirect,
    url_for,
    Response
)

from config import Config
from extensions import db, csrf, login_manager, mail

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.owner import owner_bp
from routes.viewer import viewer_bp
from routes.notifications import notifications_bp
from routes.documents import documents_bp
from routes.invitations import invitations_bp
import models
import security.user_loader


def _init_db_and_seed(app):
    with app.app_context():
        try:
            db.create_all()
            from models import AuditLog
            from security.audit import append_audit
            if AuditLog.query.order_by(AuditLog.id.desc()).first() is None:
                append_audit(None, "audit_chain_genesis", "success", details={"source": "system_initialization"})
                db.session.commit()

            from models import User
            if User.query.filter_by(role="admin").first() is None:
                from models import Document, DocumentVersion, Permission
                from security.password import hash_password

                admin_email = (os.getenv("ADMIN_EMAIL") or "demo-admin@example.com").strip().lower()
                admin_pass = os.getenv("ADMIN_PASSWORD") or "TrustVaultDemoAdmin@2026"
                admin = User(
                    name=os.getenv("ADMIN_NAME") or "Demo Administrator",
                    email=admin_email,
                    password_hash=hash_password(admin_pass),
                    role="admin",
                    is_active=True,
                    email_verified=True
                )

                owner_email = (os.getenv("DEMO_OWNER_EMAIL") or "demo-owner@example.com").strip().lower()
                owner_pass = os.getenv("DEMO_OWNER_PASSWORD") or "TrustVaultDemoOwner@2026"
                owner = User(
                    name=os.getenv("DEMO_OWNER_NAME") or "Demo Owner",
                    email=owner_email,
                    password_hash=hash_password(owner_pass),
                    role="owner",
                    is_active=True,
                    email_verified=True
                )

                viewer_email = (os.getenv("DEMO_VIEWER_EMAIL") or "demo-viewer@example.com").strip().lower()
                viewer_pass = os.getenv("DEMO_VIEWER_PASSWORD") or "TrustVaultDemoViewer@2026"
                viewer = User(
                    name=os.getenv("DEMO_VIEWER_NAME") or "Demo Viewer",
                    email=viewer_email,
                    password_hash=hash_password(viewer_pass),
                    role="viewer",
                    is_active=True,
                    email_verified=True
                )

                db.session.add_all([admin, owner, viewer])
                db.session.flush()

                append_audit(admin.id, "demo_admin_seed", "success", details={"email": admin.email, "demo_account": True})

                storage = app.config.get("TRUSTVAULT_STORAGE") or os.path.join(app.instance_path, "private_documents")
                os.makedirs(storage, mode=0o700, exist_ok=True)
                sample = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF\n"
                doc = Document.query.filter_by(owner_id=owner.id, title="TrustVault Evaluation Sample").first()
                if not doc:
                    key = uuid.uuid4().hex
                    with open(os.path.join(storage, key), "wb") as handle:
                        handle.write(sample)
                    doc = Document(
                        owner_id=owner.id,
                        title="TrustVault Evaluation Sample",
                        description="Seeded sample PDF used to test protected access.",
                        category="Demo",
                        original_filename="trustvault-evaluation-sample.pdf",
                        storage_key=key,
                        mime_type="application/pdf",
                        size_bytes=len(sample),
                        current_version=1
                    )
                    db.session.add(doc)
                    db.session.flush()
                    db.session.add(DocumentVersion(
                        document_id=doc.id,
                        version_number=1,
                        storage_key=key,
                        uploaded_by=owner.id,
                        checksum=hashlib.sha256(sample).hexdigest()
                    ))
                    db.session.add(Permission(
                        document_id=doc.id,
                        user_id=viewer.id,
                        permission_type="read",
                        granted_by=owner.id
                    ))

                db.session.commit()
                app.logger.info("Database tables and demo accounts initialized successfully.")
        except Exception as e:
            db.session.rollback()
            app.logger.warning(f"Database auto-initialization note: {e}")


def create_app(test_config=None):

    app = Flask(
        __name__,
        template_folder="frontend",
        static_folder=None
    )

    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # SECRET KEY CONFIGURATION
    secret_key = app.config.get("SECRET_KEY") or os.getenv("SECRET_KEY")

    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY is missing. Add it to your .env file."
        )

    app.config["SECRET_KEY"] = secret_key

    if app.config.get("TRUST_PROXY"):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1,
            x_proto=1,
            x_host=1
        )

    # FLASK-MAIL SMTP CONFIGURATION
    app.config["MAIL_SERVER"] = os.getenv(
        "MAIL_SERVER", "smtp.gmail.com"
    )

    app.config["MAIL_PORT"] = int(
        os.getenv("MAIL_PORT", "587")
    )

    app.config["MAIL_USE_TLS"] = (
        os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    )

    app.config["MAIL_USE_SSL"] = (
        os.getenv("MAIL_USE_SSL", "False").lower() == "true"
    )

    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")

    app.config["MAIL_DEFAULT_SENDER"] = (
        os.getenv("MAIL_DEFAULT_SENDER")
        or app.config["MAIL_USERNAME"]
    )

    # DATABASE INITIALIZATION
    db.init_app(app)

    # CSRF PROTECTION INITIALIZATION
    csrf.init_app(app)

    # FLASK-LOGIN INITIALIZATION
    login_manager.init_app(app)
    login_manager.login_view = "login_page"

    # FLASK-MAIL INITIALIZATION
    mail.init_app(app)

    # REGISTER BLUEPRINTS
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(owner_bp)
    app.register_blueprint(viewer_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(invitations_bp)

    # FRONTEND DIRECTORY
    frontend_folder = os.path.join(
        app.root_path,
        "frontend"
    )

    # GOOGLE SEARCH CONSOLE VERIFICATION
    @app.route("/google475f0aed161d73b1.html")
    def google_site_verification():
        return send_from_directory(
            app.root_path,
            "google475f0aed161d73b1.html"
        )

    # ROBOTS.TXT
    @app.route("/robots.txt")
    def robots_txt():
        return Response("User-agent: *\nAllow: /\n", mimetype="text/plain")

    # SECURITY HEADERS
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data:; frame-ancestors 'none'; "
            "form-action 'self'; base-uri 'self'",
        )
        return response

    # PUBLIC PAGES
    contact_email = (
        os.getenv("CONTACT_EMAIL")
        or os.getenv("MAIL_DEFAULT_SENDER")
        or os.getenv("MAIL_USERNAME")
        or "rangapujithadomala@gmail.com"
    )

    @app.route("/privacy")
    def privacy_page():
        return render_template("privacy.html", contact_email=contact_email)

    @app.route("/terms")
    def terms_page():
        return render_template("terms.html", contact_email=contact_email)

    # LOGIN PAGE
    @app.route("/login.html")
    def login_page():
        return render_template("login.html", contact_email=contact_email)

    # REGISTER PAGE
    @app.route("/register.html")
    def register_page():
        return redirect(url_for("login_page"))

    # FRONTEND PAGE ALIASES
    @app.route("/email-verification.html")
    def email_verification_page():
        return render_template("email-verification.html")

    @app.route("/forgot-password.html")
    def forgot_password_page():
        return render_template("forgot-password.html")

    @app.route("/reset-password.html")
    def reset_password_page():
        return render_template("reset-password.html")

    @app.route("/verification-pending.html")
    def verification_pending_page():
        return render_template("verification-pending.html")

    # FRONTEND CSS AND JAVASCRIPT
    @app.route("/<path:filename>")
    def frontend_assets(filename):

        if not filename.endswith((".css", ".js")):
            abort(404)

        return send_from_directory(
            frontend_folder,
            filename
        )

    # DATABASE HEALTH CHECK
    @app.route("/health")
    def health():
        from sqlalchemy import text

        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ok"}, 200

        except Exception as e:
            app.logger.exception(
                "Health check database query failed"
            )
            return {"status": "unavailable", "error": str(e)}, 503

    # HOME PAGE
    @app.route("/")
    def home():
        return render_template("landing.html", contact_email=contact_email)

    if not app.config.get("TESTING"):
        _init_db_and_seed(app)

    return app


if __name__ == "__main__":
    import os

    app = create_app()

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )

import os

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
    url_for
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
    contact_email = os.getenv("CONTACT_EMAIL", "contact@example.com")

    @app.route("/privacy")
    def privacy_page():
        return render_template("privacy.html", contact_email=contact_email)

    @app.route("/terms")
    def terms_page():
        return render_template("terms.html", contact_email=contact_email)

    # LOGIN PAGE
    @app.route("/login.html")
    def login_page():
        return render_template("login.html")

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

        except Exception:
            app.logger.exception(
                "Health check database query failed"
            )
            return {"status": "unavailable"}, 503

    # HOME PAGE
    @app.route("/")
    def home():
        return render_template("landing.html", contact_email=contact_email)

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
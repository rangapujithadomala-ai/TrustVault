
import os

from dotenv import load_dotenv

# Load environment variables before loading Config
load_dotenv()

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

import models
import security.user_loader


def create_app(test_config=None):

    app = Flask(
        __name__,
        template_folder="frontend",
        static_folder=None
    )

    # Load existing application configuration
    app.config.from_object(Config)

    # -----------------------------------
    # SECRET KEY CONFIGURATION
    # -----------------------------------

    secret_key = os.getenv("SECRET_KEY") or app.config.get("SECRET_KEY")

    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY is missing. Add it to your .env file."
        )

    app.config["SECRET_KEY"] = secret_key

    # -----------------------------------
    # FLASK-MAIL SMTP CONFIGURATION
    # -----------------------------------

    app.config["MAIL_SERVER"] = os.getenv(
        "MAIL_SERVER",
        "smtp.gmail.com"
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

    # Apply test configuration when supplied
    if test_config:
        app.config.update(test_config)

    # -----------------------------------
    # DATABASE INITIALIZATION
    # -----------------------------------

    db.init_app(app)

    # -----------------------------------
    # CSRF PROTECTION INITIALIZATION
    # -----------------------------------

    csrf.init_app(app)

    # -----------------------------------
    # FLASK-LOGIN INITIALIZATION
    # -----------------------------------

    login_manager.init_app(app)

    login_manager.login_view = "login_page"

    # -----------------------------------
    # FLASK-MAIL INITIALIZATION
    # -----------------------------------

    mail.init_app(app)

    # -----------------------------------
    # REGISTER BLUEPRINTS
    # -----------------------------------

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(owner_bp)
    app.register_blueprint(viewer_bp)
    app.register_blueprint(notifications_bp)

    # -----------------------------------
    # FRONTEND DIRECTORY
    # -----------------------------------

    frontend_folder = os.path.join(
        app.root_path,
        "frontend"
    )

    # -----------------------------------
    # LOGIN PAGE
    # -----------------------------------

    @app.route("/login.html")
    def login_page():
        return render_template("login.html")

    # -----------------------------------
    # REGISTER PAGE
    # -----------------------------------

    @app.route("/register.html")
    def register_page():
        return render_template("register.html")

    # -----------------------------------
    # FRONTEND CSS AND JAVASCRIPT
    # -----------------------------------

    @app.route("/<path:filename>")
    def frontend_assets(filename):

        if not filename.endswith((".css", ".js")):
            abort(404)

        return send_from_directory(
            frontend_folder,
            filename
        )

    # -----------------------------------
    # HOME PAGE
    # -----------------------------------

    @app.route("/")
    def home():
        return redirect(url_for("login_page"))

    return app


if __name__ == "__main__":

    app = create_app()

    app.run(debug=True)

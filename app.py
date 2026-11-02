
from flask import Flask
from config import Config
from extensions import db, csrf, login_manager, mail
from routes.auth import auth_bp
import models
import security.user_loader


def create_app(test_config=None):
    # Create Flask application
    app = Flask(__name__)

    # Load application configuration
    app.config.from_object(Config)

        # Apply test-specific settings when provided
    if test_config:
        app.config.update(test_config)

    # Initialise database
    db.init_app(app)

    # Enable CSRF protection
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    # Initialise email service
    mail.init_app(app)
    app.register_blueprint(auth_bp)
    # Home route
    @app.route("/")
    def home():
        return "TrustVault is running!"
   

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()

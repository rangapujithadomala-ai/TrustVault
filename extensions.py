from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from flask_mail import Mail

# Database extension
db = SQLAlchemy()

# CSRF protection extension
csrf = CSRFProtect()

# Login session management
login_manager = LoginManager()

# Email sending extension
mail = Mail()
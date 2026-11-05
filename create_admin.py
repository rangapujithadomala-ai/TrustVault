
from getpass import getpass

from app import create_app
from extensions import db
from models import User
from security.password import hash_password


app = create_app()

with app.app_context():

    print("\n===== TrustVault Initial Admin Setup =====\n")

    name = input("Enter Admin name: ").strip()
    email = input("Enter Admin email: ").strip().lower()

    password = getpass("Create Admin password: ")
    confirm_password = getpass("Confirm Admin password: ")

    if not name or not email:
        print("Name and email are required.")
        raise SystemExit

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        raise SystemExit

    if password != confirm_password:
        print("Passwords do not match.")
        raise SystemExit

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        print("An account with this email already exists.")
        raise SystemExit

    admin = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="admin",
        is_active=True,
        email_verified=True
    )

    try:
        db.session.add(admin)
        db.session.commit()
        print("\nAdmin account created successfully!")
        print("You can now log in through TrustVault.")

    except Exception as error:
        db.session.rollback()
        print("Admin creation failed:", error)

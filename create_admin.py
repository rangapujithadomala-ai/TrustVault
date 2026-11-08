
from getpass import getpass
import os

from app import create_app
from extensions import db
from models import User
from security.password import hash_password, validate_password
from security.audit import append_audit


app = create_app()

with app.app_context():

    print("\n===== TrustVault Initial Admin Setup =====\n")

    name = (os.getenv("ADMIN_NAME") or input("Enter Admin name: ")).strip()
    email = (os.getenv("ADMIN_EMAIL") or input("Enter Admin email: ")).strip().lower()

    password = os.getenv("ADMIN_PASSWORD") or getpass("Create Admin password: ")
    confirm_password = os.getenv("ADMIN_PASSWORD") or getpass("Confirm Admin password: ")

    if not name or not email:
        print("Name and email are required.")
        raise SystemExit

    valid, message = validate_password(password)
    if not valid:
        print(message)
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
        db.session.flush()
        append_audit(admin.id, "admin_bootstrap", "success", details={"email":admin.email})
        db.session.commit()
        print("\nAdmin account created successfully!")
        print("You can now log in through TrustVault.")

    except Exception as error:
        db.session.rollback()
        print("Admin creation failed:", error)

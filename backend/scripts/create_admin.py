#!/usr/bin/env python3
"""
Create Admin Account Script
Usage: python create_admin.py [email] [password]
Defaults: admin@csnavigator.com / Admin123!
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import engine, SessionLocal, Base
from models import User
from security import hash_password

def create_admin(email: str = "admin@csnavigator.com", password: str = "Admin123!"):
    """Create an admin user in the database"""

    # Create all tables if they don't exist
    print("Creating database tables if needed...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if admin already exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User {email} already exists!")
            if existing.role != "admin":
                existing.role = "admin"
                db.commit()
                print(f"Updated {email} to admin role.")
            else:
                print(f"{email} is already an admin.")
            return existing

        # Create new admin user
        admin = User(
            email=email,
            password_hash=hash_password(password),
            role="admin",
            name="System Admin",
            major="Administration"
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print(f"Admin account created successfully!")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print(f"  Role: admin")

        return admin

    except Exception as e:
        db.rollback()
        print(f"Error creating admin: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Get email and password from command line args, or use defaults
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@csnavigator.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "Admin123!"

    print(f"\nCreating admin account...")
    print(f"Database: {os.getenv('DATABASE_URL', 'Not set - check .env')}\n")

    create_admin(email, password)

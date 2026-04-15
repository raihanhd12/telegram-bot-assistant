"""
Create service (DB-level) for users.

Contains only database-related operations for creating a user so higher-level
service can perform notifications / tracking without mixing responsibilities.
"""

import hashlib

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from src.app.repositories.user import UserRepository
from src.app.schemas.user import UserCreate
from src.database.factories import User
from src.database.session import SessionLocal


def create_user_db(user_data: UserCreate) -> User:
    """Create the user in DB and return the model instance.

    Raises DB exceptions (IntegrityError / OperationalError) to be handled by caller.
    """
    db: Session = SessionLocal()
    try:
        # check duplicates
        existing = UserRepository.get_by_username(
            db, user_data.username
        ) or UserRepository.get_by_email(db, user_data.email)
        if existing:
            if str(existing.username) == user_data.username:
                raise ValueError("Username already exists")
            else:
                raise ValueError("Email already exists")

        # Hash password before persisting
        # Fallback to a simple SHA-256 hash for the password to ensure the
        # non-nullable password column is populated. For production use a
        # stronger adaptive hashing (bcrypt/argon2). This keeps the current
        # change small and avoids passlib backend issues in the dev env.
        hashed_password = hashlib.sha256(user_data.password.encode("utf-8")).hexdigest()
        new_user = UserRepository.create_user(
            db,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            password=hashed_password,
        )
        return new_user

    except IntegrityError:
        # let caller handle
        raise
    except OperationalError:
        raise
    finally:
        db.close()

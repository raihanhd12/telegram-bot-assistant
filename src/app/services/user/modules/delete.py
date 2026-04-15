"""
Delete service for users (DB-level deletion).
"""

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from src.app.repositories.user import UserRepository
from src.database.session import SessionLocal


def delete_user_db(user_id: int) -> bool:
    db: Session = SessionLocal()
    try:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return False

        UserRepository.delete_user(db, user)
        return True
    except OperationalError:
        raise
    finally:
        db.close()

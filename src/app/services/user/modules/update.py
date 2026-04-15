"""
Update service for users (DB-level updates).
"""

from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from src.app.repositories.user import UserRepository
from src.app.schemas.user import UserUpdate
from src.database.factories import User
from src.database.session import SessionLocal


def update_user_db(user_id: int, user_data: UserUpdate) -> Optional[User]:
    db: Session = SessionLocal()
    try:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return None

        update_data: Dict[str, Any] = user_data.model_dump(exclude_unset=True)
        updated = UserRepository.update_user(db, user, update_data)
        return updated

    except IntegrityError:
        db.rollback()
        raise
    except OperationalError:
        raise
    finally:
        db.close()

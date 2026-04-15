"""
User repository

Simple CRUD helpers for User model. Services call these functions and manage
Sessions (commit/rollback) where appropriate.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.database.factories import User


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).limit(1).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).limit(1).first()

    @staticmethod
    def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def create_user(db: Session, **kwargs: Any) -> User:
        user = User(**kwargs)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_user(db: Session, user: User, update_data: Dict[str, Any]) -> User:
        for key, value in update_data.items():
            setattr(user, key, value)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user: User) -> None:
        db.delete(user)
        db.commit()

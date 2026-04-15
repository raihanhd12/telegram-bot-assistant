"""
Read service for users (DB-level retrievals).
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.app.repositories.user import UserRepository
from src.database.factories import User
from src.database.session import SessionLocal


def get_user_by_id(user_id: int) -> Optional[User]:
    db: Session = SessionLocal()
    try:
        return UserRepository.get_by_id(db, user_id)
    finally:
        db.close()


def get_user_by_username(username: str) -> Optional[User]:
    db: Session = SessionLocal()
    try:
        return UserRepository.get_by_username(db, username)
    finally:
        db.close()


def get_user_by_email(email: str) -> Optional[User]:
    db: Session = SessionLocal()
    try:
        return UserRepository.get_by_email(db, email)
    finally:
        db.close()


def list_users(skip: int = 0, limit: int = 100) -> List[User]:
    db: Session = SessionLocal()
    try:
        return UserRepository.list_users(db, skip=skip, limit=limit)
    finally:
        db.close()

"""
User Service

Handles business logic for user operations including validation,
notifications, external integrations, and business rules.
"""

from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.exc import IntegrityError, OperationalError

from src.app.schemas.user import UserCreate, UserUpdate
from src.app.services.base import BaseService
from src.database.factories import User

# Use relative imports to avoid circular import issues when this module
# is imported via the package `src.app.services.user` (its __init__ imports
# this file). Import submodules relatively so Python doesn't re-enter the
# package initialization during the import.
from .modules import create, delete, read, update, validators


class UserService(BaseService):
    """Facade service that delegates DB work to split modules and keeps higher-level
    responsibilities (notifications, tracking, permission checks).
    """

    def __init__(self):
        super().__init__()

    def validate_user_data(self, user_data: UserCreate) -> Dict[str, Any]:
        # Delegate to validators module (keeps public API for compatibility)
        return validators.validate_user_create(user_data)

    def send_welcome_notification(self, user: User) -> bool:
        try:
            logger.info(f"📧 Welcome notification sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send welcome notification: {e}")
            return False

    def track_user_activity(self, user_id: int, activity: str) -> None:
        logger.info(f"📊 User {user_id} performed activity: {activity}")

    def check_user_permissions(self, user_id: int, permission: str) -> bool:
        logger.debug(f"🔐 Checking permission '{permission}' for user {user_id}")
        return True

    def create_user(self, user_data: UserCreate) -> User:
        # 1. Validate business rules
        validation = validators.validate_user_create(user_data)
        if not validation["valid"]:
            raise ValueError(f"Validation failed: {', '.join(validation['issues'])}")

        # 2. DB create (delegated)
        try:
            new_user = create.create_user_db(user_data)
            # Post-creation actions
            # Attempt to get numeric id for tracking; be permissive about types
            user_id_val = getattr(new_user, "id", None)
            try:
                if user_id_val is not None:
                    user_id_val = int(user_id_val)
            except Exception:
                # keep original value if casting fails
                pass
            self.send_welcome_notification(new_user)
            if user_id_val is not None:
                self.track_user_activity(user_id_val, "user_created")
            logger.info(f"✅ User created: {new_user.username}")
            return new_user
        except IntegrityError as e:
            # Try to provide a clearer error message for common unique constraint
            # violations (username/email). Different DB drivers expose details
            # on the exception object; for psycopg2 we can inspect `e.orig`.
            try:
                orig = getattr(e, "orig", None)
                constraint = None
                # psycopg2 exposes diag.constraint_name
                if orig is not None and hasattr(orig, "diag"):
                    constraint = getattr(orig.diag, "constraint_name", None)
                msg = None
                if constraint:
                    if "username" in constraint:
                        msg = "Username already exists"
                    elif "email" in constraint:
                        msg = "Email already exists"
                # Fallback: inspect stringified message
                if not msg:
                    text = str(e)
                    if "username" in text:
                        msg = "Username already exists"
                    elif "email" in text:
                        msg = "Email already exists"
                if msg:
                    raise ValueError(msg) from e
            except Exception:
                # If parsing fails, fall through to generic error
                pass
            # translate DB errors to a runtime error for upper layers
            raise RuntimeError("Database integrity error during user creation") from e
        except OperationalError as e:
            raise RuntimeError("Database operational error during user creation") from e

    def get_user(self, user_id: int) -> Optional[User]:
        return read.get_user_by_id(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        return read.get_user_by_username(username)

    def get_user_by_email(self, email: str) -> Optional[User]:
        return read.get_user_by_email(email)

    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        return read.list_users(skip=skip, limit=limit)

    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        # validate update fields
        validation = validators.validate_user_update(user_data)
        if not validation["valid"]:
            raise ValueError(f"Validation failed: {', '.join(validation['issues'])}")

        try:
            updated = update.update_user_db(user_id, user_data)
            if updated:
                logger.info(f"✅ User updated: {updated.username}")
            return updated
        except IntegrityError as e:
            raise ValueError("Username or email already exists") from e
        except OperationalError as e:
            raise RuntimeError("Database operational error during user update") from e

    def delete_user(self, user_id: int) -> bool:
        try:
            deleted = delete.delete_user_db(user_id)
            if deleted:
                logger.info(f"✅ User deleted: ID {user_id}")
            return deleted
        except OperationalError as e:
            raise RuntimeError("Database operational error during user deletion") from e

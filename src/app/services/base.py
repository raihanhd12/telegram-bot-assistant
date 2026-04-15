"""
Base Service

Contains base service class with common functionality for all services.
Services can handle various business logic: API calls, file operations, calculations, etc.
Not just database operations.
"""

from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

import src.config.env as env
from src.database.session import SessionLocal


class BaseService:
    """
    Base service class with common functionality for all types of services
    """

    def __init__(self):
        """Initialize base service - only log in development mode"""
        if env.DEVELOPMENT:
            logger.debug(f"✅ {self.__class__.__name__} initialized")

    def get_db_session(self) -> Session:
        """
        Get database session - only use this if your service needs database access
        """
        # Create a session instance directly. `get_db` is a contextmanager and
        # returns a _GeneratorContextManager when called; using `next(get_db())`
        # causes a "'_GeneratorContextManager' object is not an iterator" error.
        # Services are responsible for closing the session (they already call
        # `db.close()` in finally blocks), so returning a SessionLocal() here
        # is appropriate.
        return SessionLocal()

    def _handle_database_error(self, db: Session, error: Exception, operation: str):
        """
        Handle database errors consistently - only for database-related services
        """
        db.rollback()
        logger.error(f"❌ Database error during {operation}: {error}")
        raise RuntimeError(f"Database error during {operation}") from error

    def _log_operation(self, operation: str, details: Optional[str] = None):
        """
        Log service operations consistently
        """
        message = f"🔄 {operation}"
        if details:
            message += f" - {details}"
        logger.info(message)

    def _handle_validation_error(self, message: str, details: Optional[str] = None):
        """
        Handle validation errors consistently
        """
        full_message = message
        if details:
            full_message += f": {details}"
        logger.warning(f"⚠️ Validation error: {full_message}")
        raise ValueError(full_message)

    def _handle_business_logic_error(self, message: str, details: Optional[str] = None):
        """
        Handle business logic errors consistently
        """
        full_message = message
        if details:
            full_message += f": {details}"
        logger.error(f"❌ Business logic error: {full_message}")
        raise RuntimeError(full_message)

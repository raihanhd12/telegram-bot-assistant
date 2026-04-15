"""Pytest configuration and fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.app.models  # noqa: F401
from src.database.session import Base


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(in_memory_db):
    """Create a database session for testing"""
    TestingSessionLocal = sessionmaker(bind=in_memory_db)
    session = TestingSessionLocal()
    yield session
    session.close()

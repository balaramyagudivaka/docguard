"""Shared test setup."""

import os

# Use a small SQLite file for tests instead of PostgreSQL. Must run before the app is imported.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest  # noqa: E402

from app import models  # noqa: E402,F401
from app.database import Base, SessionLocal, engine  # noqa: E402


@pytest.fixture
def db():
    """A fresh, empty database for every test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
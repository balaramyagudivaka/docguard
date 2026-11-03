"""Database connection: one place that knows how to talk to PostgreSQL."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Read the address from an environment variable, with the local Docker database as default.
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://docguard:docguard@localhost:5432/docguard"
)

engine = create_engine(DATABASE_URL)          # the connection to the database
SessionLocal = sessionmaker(bind=engine)      # a factory that makes sessions


class Base(DeclarativeBase):
    """Every table class inherits from this, so SQLAlchemy can find them all."""


def get_db():
    """Give each request its own session, and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
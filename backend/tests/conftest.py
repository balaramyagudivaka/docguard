"""Shared test setup.

Tests run against a separate PostgreSQL database, "docguard_test", so they use
the same features as the real app (including pgvector) without touching your
real data. Embeddings use the fast FakeEmbedder so no AI model is downloaded.
"""

import os

# Must run before the app is imported.
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://docguard:docguard@localhost:5432/docguard_test"
)
os.environ["EMBEDDER"] = "fake"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401
from app.database import Base, SessionLocal, engine, get_db, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db():
    """A fresh, empty database for every test."""
    Base.metadata.drop_all(bind=engine)
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db):
    """A test client whose requests use the same fresh test database."""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(client):
    """Factory: make_user("a@x.com") registers + logs in, and returns auth headers."""

    def _make(email: str) -> dict:
        creds = {"email": email, "password": "correct-horse-battery"}
        client.post("/auth/register", json=creds)
        token = client.post("/auth/login", json=creds).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make

"""Tests for POST /auth/register."""

from sqlalchemy import select

from app.models import User
from app.security import verify_password

GOOD = {"email": "ramya@example.com", "password": "correct-horse-battery"}


def test_register_creates_user(client):
    response = client.post("/auth/register", json=GOOD)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ramya@example.com"
    assert "id" in body
    assert "password" not in body and "hashed_password" not in body


def test_password_is_stored_hashed(client, db):
    client.post("/auth/register", json=GOOD)

    user = db.scalars(select(User)).one()
    assert user.hashed_password != GOOD["password"]
    assert verify_password(GOOD["password"], user.hashed_password)


def test_duplicate_email_is_rejected(client):
    client.post("/auth/register", json=GOOD)
    response = client.post("/auth/register", json=GOOD)

    assert response.status_code == 409


def test_email_is_case_insensitive(client):
    client.post("/auth/register", json=GOOD)
    response = client.post("/auth/register", json={**GOOD, "email": "RAMYA@example.com"})

    assert response.status_code == 409


def test_invalid_email_is_rejected(client):
    response = client.post("/auth/register", json={**GOOD, "email": "not-an-email"})

    assert response.status_code == 422


def test_short_password_is_rejected(client):
    response = client.post("/auth/register", json={**GOOD, "password": "short"})

    assert response.status_code == 422

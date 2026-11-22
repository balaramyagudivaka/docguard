"""Tests for POST /auth/login and GET /auth/me."""

from app.security import create_access_token

USER = {"email": "ramya@example.com", "password": "correct-horse-battery"}


def register_and_login(client) -> str:
    """Helper: create the test user and return a valid token."""
    client.post("/auth/register", json=USER)
    response = client.post("/auth/login", json=USER)
    return response.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_token(client):
    client.post("/auth/register", json=USER)
    response = client.post("/auth/login", json=USER)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_login_email_is_case_insensitive(client):
    client.post("/auth/register", json=USER)
    response = client.post("/auth/login", json={**USER, "email": "RAMYA@example.com"})

    assert response.status_code == 200


def test_wrong_password_is_rejected(client):
    client.post("/auth/register", json=USER)
    response = client.post("/auth/login", json={**USER, "password": "wrong-password"})

    assert response.status_code == 401


def test_unknown_email_is_rejected_with_same_message(client):
    client.post("/auth/register", json=USER)
    wrong_password = client.post("/auth/login", json={**USER, "password": "wrong-password"})
    unknown_email = client.post("/auth/login", json={**USER, "email": "nobody@example.com"})

    assert unknown_email.status_code == 401
    assert unknown_email.json() == wrong_password.json()  # reveals nothing extra


def test_me_returns_logged_in_user(client):
    token = register_and_login(client)
    response = client.get("/auth/me", headers=auth_header(token))

    assert response.status_code == 200
    assert response.json()["email"] == "ramya@example.com"


def test_me_without_token_is_rejected(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_with_fake_token_is_rejected(client):
    response = client.get("/auth/me", headers=auth_header("not.a.real-token"))

    assert response.status_code == 401


def test_me_with_tampered_token_is_rejected(client):
    token = register_and_login(client)
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

    response = client.get("/auth/me", headers=auth_header(tampered))
    assert response.status_code == 401


def test_me_with_expired_token_is_rejected(client):
    client.post("/auth/register", json=USER)
    expired = create_access_token(user_id=1, expires_minutes=-1)

    response = client.get("/auth/me", headers=auth_header(expired))
    assert response.status_code == 401
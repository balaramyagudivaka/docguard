"""Password hashing and login tokens.

Passwords: we never store real passwords. A hash is a one-way scramble. At login
we hash what the user typed and compare it with the stored hash. Argon2 adds a
random salt to every hash, so equal passwords still get different hashes.

Tokens: after a successful login we give the user a JWT (JSON Web Token), a small
signed "pass" that says "this is user 7, valid until 6 pm". The user sends it with
every request instead of the password. Only the server knows the secret used to
sign it, so nobody can forge or edit a token without the signature breaking.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()  # uses Argon2

# The signing secret comes from an environment variable. The default is ONLY for
# local development; a real deployment must set its own long random JWT_SECRET.
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret-change-me-before-deploying-0123456789")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user_id: int, expires_minutes: int = ACCESS_TOKEN_MINUTES) -> str:
    """Make a signed token that identifies the user and expires after a while."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # "subject": who this token belongs to
        "iat": now,  # issued at
        "exp": now + timedelta(minutes=expires_minutes),  # expires at
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Return the user id inside a valid token, or None if the token is fake, edited or expired."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
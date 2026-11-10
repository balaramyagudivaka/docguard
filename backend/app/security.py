"""Password hashing.

We never store real passwords. A hash is a one-way scramble: easy to compute,
practically impossible to reverse. At login we hash what the user typed and
compare it with the stored hash.

Argon2 is the current recommended algorithm. It adds a random "salt" to every
hash, so two users with the same password still get different hashes.
"""

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()  # uses Argon2


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import User


def test_can_save_and_read_a_user(db):
    db.add(User(email="ramya@example.com", hashed_password="not-a-real-hash"))
    db.commit()

    saved = db.scalars(select(User).where(User.email == "ramya@example.com")).one()
    assert saved.id is not None
    assert saved.created_at is not None


def test_email_must_be_unique(db):
    db.add(User(email="same@example.com", hashed_password="x"))
    db.commit()

    db.add(User(email="same@example.com", hashed_password="y"))
    with pytest.raises(IntegrityError):   # the database itself must refuse the duplicate
        db.commit()
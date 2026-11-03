"""Database tables, written as Python classes."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)  # 1, 2, 3... assigned automatically
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # no two users share one
    hashed_password: Mapped[str] = mapped_column(String(255))  # NEVER the real password
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
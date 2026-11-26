"""Database tables, written as Python classes."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.embeddings import EMBEDDING_DIM


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)  # 1, 2, 3... assigned automatically
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # no two users share one
    hashed_password: Mapped[str] = mapped_column(String(255))  # NEVER the real password
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Membership(Base):
    """Links a user to a team with a role. One row per (team, user) pair."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("team_id", "user_id"),)  # can't join the same team twice

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)  # must point to a real team
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)  # must point to a real user
    role: Mapped[str] = mapped_column(String(20))  # "owner", "member" or "viewer"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Document(Base):
    """A text document uploaded to a team."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    visibility: Mapped[str] = mapped_column(String(20))  # "team" or "restricted"
    content: Mapped[str] = mapped_column(Text)  # the document's text
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DocumentAccess(Base):
    """Grants one user access to one restricted document."""

    __tablename__ = "document_access"
    __table_args__ = (UniqueConstraint("document_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)


class Chunk(Base):
    """One small piece of a document, with its embedding (a list of numbers capturing its meaning)."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)  # 0, 1, 2... position in the document
    text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(EMBEDDING_DIM))  # stored by pgvector

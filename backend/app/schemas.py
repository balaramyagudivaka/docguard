"""Shapes of the data that goes in and out of the API.

FastAPI checks every request against these automatically. If the data doesn't
fit (bad email, password too short), the request is rejected with status 422
before your code even runs.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """What the client sends to sign up."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    """What the API sends back. Note: no password field, not even the hash."""

    model_config = ConfigDict(from_attributes=True)  # allows building this from a database User

    id: int
    email: EmailStr
    created_at: datetime



class LoginRequest(BaseModel):
    """What the client sends to log in."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """What the API returns after a successful login."""

    access_token: str
    token_type: str = "bearer"



class TeamCreate(BaseModel):
    """What the client sends to create a team."""

    name: str = Field(min_length=1, max_length=100)


class TeamOut(BaseModel):
    """A team as seen by one of its members."""

    id: int
    name: str
    created_at: datetime
    my_role: str


class MemberOut(BaseModel):
    """One person in a team."""

    user_id: int
    email: EmailStr
    role: str


class TeamDetail(TeamOut):
    """A team plus its member list."""

    members: list[MemberOut]
    

Role = Literal["owner", "member", "viewer"]  # the only allowed role values


class MemberAdd(BaseModel):
    """What the owner sends to add someone to a team."""

    email: EmailStr
    role: Role = "member"


class RoleUpdate(BaseModel):
    """What the owner sends to change someone's role."""

    role: Role




Visibility = Literal["team", "restricted"]


class DocumentOut(BaseModel):
    """A document's details, without its text."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    filename: str
    size_bytes: int
    visibility: Visibility
    uploaded_by: int
    created_at: datetime


class DocumentDetail(DocumentOut):
    """A document's details plus its full text."""

    content: str


class AccessGrant(BaseModel):
    """Who to give access to a restricted document."""

    email: EmailStr


class SearchRequest(BaseModel):
    """A search over a team's documents."""

    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)  # how many results to return


class SearchResult(BaseModel):
    """One matching chunk."""

    document_id: int
    filename: str
    chunk_index: int
    text: str
    score: float  # 1.0 = identical meaning, 0 = unrelated


class AskRequest(BaseModel):
    """A question about a team's documents."""

    question: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)  # how many chunks to give the LLM


class Citation(BaseModel):
    """A source the answer may refer to as [1], [2], ..."""

    number: int
    document_id: int
    filename: str
    chunk_index: int
    text: str
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]

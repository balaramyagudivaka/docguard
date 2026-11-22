"""Shapes of the data that goes in and out of the API.

FastAPI checks every request against these automatically. If the data doesn't
fit (bad email, password too short), the request is rejected with status 422
before your code even runs.
"""

from datetime import datetime

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
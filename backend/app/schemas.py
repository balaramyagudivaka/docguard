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

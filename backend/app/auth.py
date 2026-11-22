"""Sign-up, login and "who am I" endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, Token, UserCreate, UserOut
from app.security import create_access_token, decode_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Reads the "Authorization: Bearer <token>" header. auto_error=False lets us
# return our own clear 401 message when the header is missing.
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)) -> User:
    """Create a new account."""
    email = data.email.lower()  # treat Ramya@x.com and ramya@x.com as the same person

    if db.scalars(select(User).where(User.email == email)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=email, hashed_password=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two sign-ups with the same email at the exact same moment
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")
    db.refresh(user)  # load the id and created_at the database just assigned
    return user


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> Token:
    """Check email and password; return a token to use on later requests."""
    user = db.scalars(select(User).where(User.email == data.email.lower())).first()

    # Same message whether the email or the password is wrong, so attackers
    # can't use this endpoint to discover which emails have accounts.
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    return Token(access_token=create_access_token(user.id))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency for protected endpoints: turns a valid token into the logged-in User."""
    not_authenticated = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise not_authenticated

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise not_authenticated

    user = db.get(User, user_id)
    if user is None:  # token is valid but the account no longer exists
        raise not_authenticated
    return user


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the logged-in user. Requires a valid token."""
    return current_user
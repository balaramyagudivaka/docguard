"""Team endpoints: create a team, list my teams, view one team.

Authentication answers "who are you?" (the login token).
Authorization answers "what are you allowed to do?" (your role in a team).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Membership, Team, User
from app.schemas import MemberOut, TeamCreate, TeamDetail, TeamOut

router = APIRouter(prefix="/teams", tags=["teams"])

ROLES = ("owner", "member", "viewer")


def get_membership(db: Session, team_id: int, user_id: int) -> Membership | None:
    """The user's membership in a team, or None if they aren't in it."""
    return db.scalars(
        select(Membership).where(Membership.team_id == team_id, Membership.user_id == user_id)
    ).first()


def require_membership(db: Session, team_id: int, user: User) -> Membership:
    """Stop the request unless the user belongs to the team.

    We answer 404 (not 403) to non-members on purpose: a 403 would confirm that
    the team exists, which leaks information. To an outsider it simply doesn't exist.
    """
    membership = get_membership(db, team_id, user.id)
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Team not found")
    return membership


@router.post("", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(
    data: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamOut:
    """Create a team. The creator automatically becomes its owner."""
    team = Team(name=data.name.strip())
    db.add(team)
    db.flush()  # sends the INSERT so team.id is assigned, without committing yet

    db.add(Membership(team_id=team.id, user_id=current_user.id, role="owner"))
    db.commit()  # team and membership are saved together, or not at all
    db.refresh(team)
    return TeamOut(id=team.id, name=team.name, created_at=team.created_at, my_role="owner")


@router.get("", response_model=list[TeamOut])
def list_my_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TeamOut]:
    """List only the teams the logged-in user belongs to."""
    rows = db.execute(
        select(Team, Membership.role)
        .join(Membership, Membership.team_id == Team.id)  # combine the two tables
        .where(Membership.user_id == current_user.id)
        .order_by(Team.id)
    ).all()
    return [
        TeamOut(id=team.id, name=team.name, created_at=team.created_at, my_role=role)
        for team, role in rows
    ]


@router.get("/{team_id}", response_model=TeamDetail)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamDetail:
    """Show one team and its members. Only members can see it."""
    my_membership = require_membership(db, team_id, current_user)
    team = db.get(Team, team_id)

    rows = db.execute(
        select(User.id, User.email, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.team_id == team_id)
        .order_by(User.id)
    ).all()
    members = [MemberOut(user_id=uid, email=email, role=role) for uid, email, role in rows]

    return TeamDetail(
        id=team.id, name=team.name, created_at=team.created_at,
        my_role=my_membership.role, members=members,
    )
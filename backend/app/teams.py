"""Team endpoints: create, list and view teams; add members and change roles.

Authentication answers "who are you?" (the login token).
Authorization answers "what are you allowed to do?" (your role in a team).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Membership, Team, User
from app.schemas import MemberAdd, MemberOut, RoleUpdate, TeamCreate, TeamDetail, TeamOut

router = APIRouter(prefix="/teams", tags=["teams"])


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


def require_owner(db: Session, team_id: int, user: User) -> Membership:
    """Stop the request unless the user is an owner of the team.

    Non-members still get 404. Members and viewers DO know the team exists,
    so for them we answer 403 Forbidden: "we know who you are, but you may not do this".
    """
    membership = require_membership(db, team_id, user)
    if membership.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only a team owner can do this")
    return membership


def count_owners(db: Session, team_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Membership)
        .where(Membership.team_id == team_id, Membership.role == "owner")
    )


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


@router.post("/{team_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    team_id: int,
    data: MemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberOut:
    """Add an existing user to the team by email. Owners only."""
    require_owner(db, team_id, current_user)

    user = db.scalars(select(User).where(User.email == data.email.lower())).first()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No account with that email")

    if get_membership(db, team_id, user.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Already a member of this team")

    db.add(Membership(team_id=team_id, user_id=user.id, role=data.role))
    db.commit()
    return MemberOut(user_id=user.id, email=user.email, role=data.role)


@router.patch("/{team_id}/members/{user_id}", response_model=MemberOut)
def change_role(
    team_id: int,
    user_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberOut:
    """Change a member's role. Owners only. A team must always keep at least one owner."""
    require_owner(db, team_id, current_user)

    target = get_membership(db, team_id, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Member not found")

    demoting_an_owner = target.role == "owner" and data.role != "owner"
    if demoting_an_owner and count_owners(db, team_id) == 1:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="A team must keep at least one owner")

    target.role = data.role
    db.commit()
    user = db.get(User, user_id)
    return MemberOut(user_id=user.id, email=user.email, role=target.role)
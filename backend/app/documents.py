"""Document endpoints: upload, list, read, and share restricted documents.

Who may do what:
  - upload:          owners and members (viewers can only read)
  - see a document:  "team" documents  -> every team member
                     "restricted" ones -> the uploader, team owners, and people granted access
  - grant access:    the uploader or a team owner

The visibility rule is applied INSIDE the database query (see visible_documents),
so documents a user may not see are never even loaded. Filtering after loading is
easy to get wrong and is how real systems leak data.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Document, DocumentAccess, User
from app.schemas import AccessGrant, DocumentDetail, DocumentOut, Visibility
from app.teams import get_membership, require_membership

router = APIRouter(tags=["documents"])

MAX_BYTES = 1_000_000  # 1 MB
ALLOWED_EXTENSIONS = (".txt", ".md")


def visible_documents(user_id: int, team_id: int, is_owner: bool) -> Select:
    """A query for exactly the team's documents this user is allowed to see."""
    granted_ids = select(DocumentAccess.document_id).where(DocumentAccess.user_id == user_id)
    query = select(Document).where(Document.team_id == team_id)
    if is_owner:
        return query  # owners can see every document in their team
    return query.where(
        or_(
            Document.visibility == "team",
            Document.uploaded_by == user_id,
            Document.id.in_(granted_ids),
        )
    )


def get_visible_document(db: Session, document_id: int, user: User) -> Document:
    """Load one document if the user may see it; otherwise answer 404."""
    not_found = HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found")

    team_id = db.scalar(select(Document.team_id).where(Document.id == document_id))
    if team_id is None:
        raise not_found
    membership = get_membership(db, team_id, user.id)
    if membership is None:
        raise not_found

    query = visible_documents(user.id, team_id, membership.role == "owner")
    document = db.scalars(query.where(Document.id == document_id)).first()
    if document is None:
        raise not_found
    return document


@router.post("/teams/{team_id}/documents", response_model=DocumentOut,
             status_code=status.HTTP_201_CREATED)
async def upload_document(
    team_id: int,
    file: UploadFile = File(...),
    visibility: Visibility = Form("team"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    """Upload a .txt or .md file to a team. Owners and members only."""
    membership = require_membership(db, team_id, current_user)
    if membership.role == "viewer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Viewers cannot upload documents")

    filename = file.filename or "untitled.txt"
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail="Only .txt and .md files are supported")

    data = await file.read(MAX_BYTES + 1)  # read one extra byte to detect oversized files
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail="File is larger than 1 MB")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File must be UTF-8 text")
    if not text.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File is empty")

    document = Document(
        team_id=team_id, uploaded_by=current_user.id, filename=filename,
        size_bytes=len(data), visibility=visibility, content=text,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/teams/{team_id}/documents", response_model=list[DocumentOut])
def list_documents(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Document]:
    """List the team's documents that the logged-in user is allowed to see."""
    membership = require_membership(db, team_id, current_user)
    query = visible_documents(current_user.id, team_id, membership.role == "owner")
    return list(db.scalars(query.order_by(Document.id)))


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def read_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    """Read one document, including its text, if the user may see it."""
    return get_visible_document(db, document_id, current_user)


@router.post("/documents/{document_id}/access", status_code=status.HTTP_201_CREATED)
def grant_access(
    document_id: int,
    data: AccessGrant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Give a team member access to a restricted document. Uploader or owner only."""
    document = get_visible_document(db, document_id, current_user)
    membership = get_membership(db, document.team_id, current_user.id)
    if document.uploaded_by != current_user.id and membership.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="Only the uploader or a team owner can share this document")

    user = db.scalars(select(User).where(User.email == data.email.lower())).first()
    if user is None or get_membership(db, document.team_id, user.id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="That person is not in this team")

    already = db.scalars(select(DocumentAccess).where(
        DocumentAccess.document_id == document_id, DocumentAccess.user_id == user.id)).first()
    if already is None:
        db.add(DocumentAccess(document_id=document_id, user_id=user.id))
        db.commit()
    return {"document_id": document_id, "user_id": user.id, "access": "granted"}
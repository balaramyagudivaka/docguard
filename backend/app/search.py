"""Semantic search: find the chunks whose meaning is closest to a question.

The permission filter is part of the SAME database query as the similarity
search. The database never even considers chunks from documents the user can't
see, so they can't slip into the results.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.documents import visible_documents
from app.embeddings import get_embedder
from app.models import Chunk, Document, User
from app.schemas import SearchRequest, SearchResult
from app.teams import require_membership

router = APIRouter(tags=["search"])


def find_relevant_chunks(db: Session, team_id: int, user: User, query: str, top_k: int) -> list[SearchResult]:
    """The chunks most similar in meaning to `query`, from documents this user may see.

    Used by both /search and /ask, so the permission rule lives in exactly one place.
    """
    membership = require_membership(db, team_id, user)

    allowed_ids = visible_documents(
        user.id, team_id, membership.role == "owner"
    ).with_only_columns(Document.id)

    query_vector = get_embedder().embed([query])[0]
    distance = Chunk.embedding.cosine_distance(query_vector)  # 0 = same direction

    rows = db.execute(
        select(Chunk, Document.filename, distance.label("distance"))
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.document_id.in_(allowed_ids))  # ⭐ permission filter inside the query
        .order_by(distance)
        .limit(top_k)
    ).all()

    return [
        SearchResult(
            document_id=chunk.document_id, filename=filename, chunk_index=chunk.chunk_index,
            text=chunk.text, score=round(1 - dist, 4),
        )
        for chunk, filename, dist in rows
    ]


@router.post("/teams/{team_id}/search", response_model=list[SearchResult])
def search(
    team_id: int,
    data: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SearchResult]:
    """Return the chunks most similar in meaning to the query, from documents you may see."""
    return find_relevant_chunks(db, team_id, current_user, data.query, data.top_k)

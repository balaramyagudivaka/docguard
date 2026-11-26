"""DocGuard API entry point.

Start the server (from the backend/ folder):
    uvicorn app.main:app --reload

Then open http://localhost:8000/docs to try the API in your browser.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import auth, documents, models, search, teams  # noqa: F401  (importing models registers the tables)
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts: enable pgvector and create missing tables."""
    init_db()
    yield


app = FastAPI(
    title="DocGuard",
    description="Ask questions about your team's documents, without ever seeing documents you aren't allowed to.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(documents.router)
app.include_router(search.router)


@app.get("/health")
def health() -> dict[str, str]:
    """A tiny endpoint that says the server is running."""
    return {"status": "ok"}

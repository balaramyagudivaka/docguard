"""DocGuard API entry point.

Start the server (from the backend/ folder):
    uvicorn app.main:app --reload

Then open http://localhost:8000/docs to try the API in your browser.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import auth, models  # noqa: F401  (importing models registers the tables)
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts: create any tables that don't exist yet."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="DocGuard",
    description="Ask questions about your team's documents, without ever seeing documents you aren't allowed to.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router)


@app.get("/health")
def health() -> dict[str, str]:
    """A tiny endpoint that says the server is running."""
    return {"status": "ok"}
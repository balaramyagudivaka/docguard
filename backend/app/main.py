"""DocGuard API entry point.

Start the server (from the backend/ folder):
    uvicorn app.main:app --reload

Then open http://localhost:8000/docs to try the API in your browser.
"""

from fastapi import FastAPI

app = FastAPI(
    title="DocGuard",
    description="Ask questions about your team's documents, without ever seeing documents you aren't allowed to.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """A tiny endpoint that says the server is running.

    Deployment platforms call this to check the app is alive.
    """
    return {"status": "ok"}

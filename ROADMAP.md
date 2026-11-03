# DocGuard build roadmap

Build one milestone at a time. Each one ends with something that works, a test that proves it, and a commit. Tick the boxes as you go.

**Rule for every milestone:** you write the code. Ask Claude to explain, review, or help debug, but make sure you can explain every line, because interviewers will ask.

---

## Milestone 0: Run the starter (≈1 hour)

- [ ] Install Python 3.12, Docker Desktop and VS Code
- [ ] Clone this repo and open it in VS Code
- [ ] In `backend/`: create a virtual environment and `pip install -r requirements.txt`
- [ ] Run `uvicorn app.main:app --reload` and open http://localhost:8000/docs
- [ ] Run `pytest` and see 1 test pass
- [ ] Run `docker compose up -d` and check the database starts

**Learn:** what an API endpoint is, what a virtual environment is, what Docker does.
**Done when:** the `/health` page shows `{"status": "ok"}` in your browser.

## Milestone 1: Users and login (≈3–4 days)

- [ ] Connect to PostgreSQL with SQLAlchemy; create a `users` table
- [ ] `POST /auth/register`: create a user, storing a **hashed** password (never plain text)
- [ ] `POST /auth/login`: check the password and return a JWT access token
- [ ] `GET /me`: return the logged-in user (requires the token)
- [ ] Tests: register, login with right and wrong password, `/me` with and without a token

**Learn:** password hashing, JWT tokens, HTTP status codes (200, 201, 401, 409).
**Done when:** all auth tests pass in GitHub Actions (green check).

## Milestone 2: Teams and roles (≈2–3 days)

- [ ] Tables: `teams`, `memberships` (user + team + role: owner / member / viewer)
- [ ] Create a team; invite a user; change a role (owner only)
- [ ] Tests: a member **cannot** change roles; a non-member **cannot** see the team

**Learn:** database relationships, authorization (what you may do) vs authentication (who you are).
**Done when:** every "cannot" case has a test that returns 403.

## Milestone 3: Upload documents with permissions (≈3–4 days)

- [ ] Upload PDF or text files to a team; store the file and its metadata
- [ ] Split each document into chunks and create embeddings (sentence-transformers, like the Mistral project)
- [ ] Store chunks and embeddings in PostgreSQL with pgvector
- [ ] Per-document visibility: whole team, or only listed members
- [ ] Tests: a user can list only the documents they are allowed to see

**Learn:** file uploads, background processing, vector search.

## Milestone 4: Ask questions, safely (≈4–5 days) ⭐ the core

- [ ] `POST /ask`: embed the question, then search **only chunks the user is allowed to read**
- [ ] Send the retrieved chunks to an LLM and return the answer **with citations**
- [ ] The permission filter lives **inside the database query**, not after it (this is the key design decision; it's the same idea as your AMS691 work)
- [ ] Tests with "canary" facts: put a secret phrase in a restricted document and prove that an unauthorized user's answers never contain it

**Learn:** retrieval-augmented generation (RAG), why filtering after retrieval can leak data.
**Done when:** the canary tests pass.

## Milestone 5: Frontend (≈4–5 days)

- [ ] Create a React + TypeScript app with Vite in `frontend/`
- [ ] Pages: sign up / log in, team page, upload, ask a question
- [ ] Show answer citations as links to the source document

## Milestone 6: Audit log and polish (≈2 days)

- [ ] Record who asked what and which documents were used; owners can view it
- [ ] Clear error messages; loading states in the frontend

## Milestone 7: Deploy (≈2 days)

- [ ] Backend and database on a free tier (Render, Railway or Fly.io); frontend on Vercel or Netlify
- [ ] Add the live link and a 60-second demo GIF to the README
- [ ] Make the repo public and pin it

---

**Resume-ready after Milestone 4** (backend only, demo through `/docs`). **Portfolio-ready after Milestone 7.**

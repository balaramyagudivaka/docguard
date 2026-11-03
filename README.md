# 🛡️ DocGuard

![ci](https://github.com/balaramyagudivaka/docguard/actions/workflows/ci.yml/badge.svg)

**Ask questions about your team's documents, without ever seeing documents you aren't allowed to.**

> 🚧 **In development.** See [ROADMAP.md](ROADMAP.md) for progress.

## The problem

AI assistants that answer questions from company documents (retrieval-augmented generation, or RAG) can accidentally leak information: if the search step pulls in a document the user shouldn't see, the AI may quote it in its answer. DocGuard enforces document permissions **inside the retrieval step itself**, so restricted content never reaches the model.

## Features (planned)

- Sign-up and login with hashed passwords and JWT tokens
- Teams with roles: owner, member, viewer
- Upload documents and choose exactly who can see each one
- Ask questions and get answers with citations, from **allowed documents only**
- Audit log of who asked what and which sources were used
- "Canary" tests that prove restricted facts never leak into answers

## Tech stack

| Layer | Tools |
|---|---|
| Backend API | Python, FastAPI |
| Database | PostgreSQL + pgvector |
| AI | sentence-transformers embeddings, an LLM for answers |
| Frontend | React, TypeScript, Vite |
| Quality | pytest, GitHub Actions |
| Deployment | Docker |

## Run locally

```bash
docker compose up -d                 # start the database
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload        # open http://localhost:8000/docs
pytest                               # run the tests
```

---

Built by [Bala Ramya Gudivaka](https://www.linkedin.com/in/bala-ramya-gudivaka-54731424b/)

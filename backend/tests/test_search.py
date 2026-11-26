"""Tests for chunking on upload and permission-safe semantic search."""

import pytest
from sqlalchemy import func, select

from app.models import Chunk

SECRET = "PURPLE ELEPHANT 42 is the vault password"


@pytest.fixture
def team(client, make_user):
    """Alice owns the team; Bob and Erin are members; Carol is a viewer; Dave is an outsider."""
    users = {n: make_user(f"{n}@example.com") for n in ("alice", "bob", "carol", "dave", "erin")}
    team_id = client.post("/teams", json={"name": "Lab"}, headers=users["alice"]).json()["id"]
    for name, role in (("bob", "member"), ("carol", "viewer"), ("erin", "member")):
        client.post(f"/teams/{team_id}/members", json={"email": f"{name}@example.com", "role": role},
                    headers=users["alice"])
    return {"id": team_id, **users}


def upload(client, team, who, text, name="notes.txt", visibility="team"):
    response = client.post(
        f"/teams/{team['id']}/documents",
        files={"file": (name, text.encode(), "text/plain")},
        data={"visibility": visibility},
        headers=team[who],
    )
    assert response.status_code == 201
    return response.json()["id"]


def search(client, team, who, query, top_k=5):
    return client.post(f"/teams/{team['id']}/search", json={"query": query, "top_k": top_k},
                       headers=team[who])


def test_upload_creates_chunks(client, team, db):
    long_text = " ".join(f"word{i}" for i in range(450))  # 450 words -> 3 chunks of up to 200
    doc_id = upload(client, team, "bob", long_text)

    count = db.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_id == doc_id))
    assert count == 3


def test_search_finds_most_relevant_document(client, team):
    upload(client, team, "bob", "Cats purr and sleep in the sun all afternoon.", name="cats.txt")
    upload(client, team, "bob", "The rocket launch put a satellite into orbit.", name="space.txt")

    results = search(client, team, "erin", "rocket launch orbit").json()
    assert results[0]["filename"] == "space.txt"
    assert results[0]["score"] > results[1]["score"]


def test_viewer_can_search_team_documents(client, team):
    upload(client, team, "bob", "Quarterly budget planning notes.", name="budget.txt")

    response = search(client, team, "carol", "budget")
    assert response.status_code == 200
    assert response.json()[0]["filename"] == "budget.txt"


def test_outsider_cannot_search(client, team):
    upload(client, team, "bob", "Quarterly budget planning notes.")
    assert search(client, team, "dave", "budget").status_code == 404


def test_top_k_limits_results(client, team):
    for i in range(4):
        upload(client, team, "bob", f"Meeting notes number {i}.", name=f"m{i}.txt")

    assert len(search(client, team, "erin", "meeting notes", top_k=2).json()) == 2


def test_invalid_top_k_rejected(client, team):
    assert search(client, team, "erin", "anything", top_k=0).status_code == 422
    assert search(client, team, "erin", "anything", top_k=50).status_code == 422


# ---------- canary tests: a secret must never leak through search ----------

def test_canary_secret_never_reaches_unauthorized_member(client, team):
    upload(client, team, "bob", "Lunch menu: pasta and salad.", name="lunch.txt")
    upload(client, team, "bob", SECRET, name="vault.txt", visibility="restricted")

    # Erin searches for the exact secret words, and still must not get it.
    response = search(client, team, "erin", "PURPLE ELEPHANT vault password", top_k=20)
    assert response.status_code == 200
    assert "PURPLE ELEPHANT" not in response.text
    assert all(r["filename"] != "vault.txt" for r in response.json())


def test_canary_secret_never_reaches_viewer(client, team):
    upload(client, team, "bob", SECRET, name="vault.txt", visibility="restricted")

    response = search(client, team, "carol", "PURPLE ELEPHANT vault password", top_k=20)
    assert "PURPLE ELEPHANT" not in response.text


def test_uploader_and_owner_can_find_secret(client, team):
    upload(client, team, "bob", SECRET, name="vault.txt", visibility="restricted")

    for who in ("bob", "alice"):
        results = search(client, team, who, "vault password").json()
        assert results[0]["filename"] == "vault.txt"


def test_granted_member_can_find_secret(client, team):
    doc_id = upload(client, team, "bob", SECRET, name="vault.txt", visibility="restricted")
    client.post(f"/documents/{doc_id}/access", json={"email": "erin@example.com"}, headers=team["bob"])

    results = search(client, team, "erin", "vault password").json()
    assert results[0]["filename"] == "vault.txt"

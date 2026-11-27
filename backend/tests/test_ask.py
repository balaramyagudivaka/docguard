"""Tests for asking questions (RAG) without leaking restricted documents."""

import pytest

from app.ask import NOT_FOUND_ANSWER
from app.llm import LLMUnavailable, get_llm
from app.main import app

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


def ask(client, team, who, question, top_k=5):
    return client.post(f"/teams/{team['id']}/ask", json={"question": question, "top_k": top_k},
                       headers=team[who])


def test_answer_comes_with_citations(client, team):
    upload(client, team, "bob", "The rocket launch put a satellite into orbit.", name="space.txt")

    response = ask(client, team, "erin", "What did the rocket launch do?")
    assert response.status_code == 200
    body = response.json()
    assert body["citations"][0]["number"] == 1
    assert body["citations"][0]["filename"] == "space.txt"
    assert "satellite into orbit" in body["answer"]  # the fake LLM saw the right source


def test_no_accessible_documents_gives_not_found_answer(client, team):
    response = ask(client, team, "erin", "What is the budget?")

    assert response.status_code == 200
    assert response.json() == {"answer": NOT_FOUND_ANSWER, "citations": []}


def test_outsider_cannot_ask(client, team):
    upload(client, team, "bob", "Quarterly budget notes.")
    assert ask(client, team, "dave", "budget?").status_code == 404


def test_empty_question_rejected(client, team):
    assert ask(client, team, "erin", "").status_code == 422


def test_llm_down_returns_503(client, team):
    class BrokenLLM:
        def complete(self, system, user):
            raise LLMUnavailable("connection refused")

    upload(client, team, "bob", "Quarterly budget notes.")
    app.dependency_overrides[get_llm] = lambda: BrokenLLM()

    response = ask(client, team, "erin", "budget?")
    assert response.status_code == 503


# ---------- canary tests: a secret must never reach the LLM or the answer ----------

def test_canary_never_reaches_unauthorized_member(client, team):
    upload(client, team, "bob", "Lunch menu: pasta and salad.", name="lunch.txt")
    upload(client, team, "bob", SECRET, name="vault.txt", visibility="restricted")

    # Erin even types part of the secret. The fake LLM repeats its whole prompt (including
    # her question), so we check for "ELEPHANT 42", which only the restricted file contains.
    response = ask(client, team, "erin", "What is the PURPLE ELEPHANT vault password?", top_k=10)
    assert response.status_code == 200
    assert "ELEPHANT 42" not in response.text  # not in the answer, not in any citation
    assert all(c["filename"] != "vault.txt" for c in response.json()["citations"])


def test_canary_never_reaches_viewer(client, team):
    upload(client, team, "bob", SECRET, name="vault.txt", visibility="restricted")

    response = ask(client, team, "carol", "What is the vault password?", top_k=10)
    assert "ELEPHANT 42" not in response.text


def test_uploader_gets_secret_in_answer(client, team):
    upload(client, team, "bob", SECRET, name="vault.txt", visibility="restricted")

    response = ask(client, team, "bob", "What is the vault password?")
    assert "ELEPHANT 42" in response.json()["answer"]
    assert response.json()["citations"][0]["filename"] == "vault.txt"



def test_only_cited_sources_are_returned(client, team):
    class OneSourceLLM:
        def complete(self, system, user):
            return "A satellite went into orbit [1]."

    upload(client, team, "bob", "The rocket launch put a satellite into orbit.", name="space.txt")
    upload(client, team, "bob", "Our cat sleeps in the sun.", name="cats.txt")
    app.dependency_overrides[get_llm] = lambda: OneSourceLLM()

    citations = ask(client, team, "erin", "What did the rocket do?").json()["citations"]
    assert [c["number"] for c in citations] == [1]  # cats.txt was retrieved but not cited


def test_not_found_answer_has_no_citations(client, team):
    class NothingFoundLLM:
        def complete(self, system, user):
            return NOT_FOUND_ANSWER

    upload(client, team, "bob", "Our cat sleeps in the sun.", name="cats.txt")
    app.dependency_overrides[get_llm] = lambda: NothingFoundLLM()

    response = ask(client, team, "erin", "What is the capital of France?").json()
    assert response == {"answer": NOT_FOUND_ANSWER, "citations": []}

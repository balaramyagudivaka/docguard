"""Tests for uploading documents and who can see them."""

import pytest


@pytest.fixture
def team(client, make_user):
    """Alice owns the team; Bob and Erin are members; Carol is a viewer; Dave is an outsider."""
    users = {n: make_user(f"{n}@example.com") for n in ("alice", "bob", "carol", "dave", "erin")}
    team_id = client.post("/teams", json={"name": "Lab"}, headers=users["alice"]).json()["id"]
    for name, role in (("bob", "member"), ("carol", "viewer"), ("erin", "member")):
        client.post(f"/teams/{team_id}/members", json={"email": f"{name}@example.com", "role": role},
                    headers=users["alice"])
    return {"id": team_id, **users}


def upload(client, team, who, text="Hello team", name="notes.txt", visibility="team"):
    return client.post(
        f"/teams/{team['id']}/documents",
        files={"file": (name, text.encode(), "text/plain")},
        data={"visibility": visibility},
        headers=team[who],
    )


def visible_names(client, team, who):
    return [d["filename"] for d in client.get(f"/teams/{team['id']}/documents", headers=team[who]).json()]


# ---------- uploading ----------

def test_member_can_upload(client, team):
    response = upload(client, team, "bob")

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["visibility"] == "team"
    assert body["size_bytes"] == len("Hello team")


def test_viewer_cannot_upload(client, team):
    assert upload(client, team, "carol").status_code == 403


def test_outsider_cannot_upload(client, team):
    assert upload(client, team, "dave").status_code == 404


def test_only_text_files_allowed(client, team):
    assert upload(client, team, "bob", name="report.pdf").status_code == 415


def test_empty_file_rejected(client, team):
    assert upload(client, team, "bob", text="   ").status_code == 400


def test_large_file_rejected(client, team):
    assert upload(client, team, "bob", text="x" * 1_000_001).status_code == 413


# ---------- who can see what ----------

def test_team_document_visible_to_all_members(client, team):
    upload(client, team, "bob", name="shared.txt")

    for who in ("alice", "bob", "carol", "erin"):
        assert visible_names(client, team, who) == ["shared.txt"]


def test_outsider_cannot_list_documents(client, team):
    upload(client, team, "bob")
    response = client.get(f"/teams/{team['id']}/documents", headers=team["dave"])
    assert response.status_code == 404


def test_restricted_document_hidden_from_other_members(client, team):
    upload(client, team, "bob", name="shared.txt")
    upload(client, team, "bob", name="secret.txt", visibility="restricted")

    assert visible_names(client, team, "bob") == ["shared.txt", "secret.txt"]   # uploader
    assert visible_names(client, team, "alice") == ["shared.txt", "secret.txt"]  # owner
    assert visible_names(client, team, "erin") == ["shared.txt"]   # other member
    assert visible_names(client, team, "carol") == ["shared.txt"]  # viewer


def test_reading_restricted_document_directly_returns_404(client, team):
    doc_id = upload(client, team, "bob", text="the launch code", visibility="restricted").json()["id"]

    response = client.get(f"/documents/{doc_id}", headers=team["erin"])
    assert response.status_code == 404
    assert "launch code" not in response.text


def test_uploader_can_read_content(client, team):
    doc_id = upload(client, team, "bob", text="the launch code", visibility="restricted").json()["id"]

    response = client.get(f"/documents/{doc_id}", headers=team["bob"])
    assert response.status_code == 200
    assert response.json()["content"] == "the launch code"


# ---------- sharing restricted documents ----------

def test_uploader_can_grant_access(client, team):
    doc_id = upload(client, team, "bob", name="secret.txt", visibility="restricted").json()["id"]

    response = client.post(f"/documents/{doc_id}/access", json={"email": "erin@example.com"},
                           headers=team["bob"])
    assert response.status_code == 201
    assert visible_names(client, team, "erin") == ["secret.txt"]
    assert visible_names(client, team, "carol") == []  # still hidden from others


def test_other_member_cannot_grant_access(client, team):
    doc_id = upload(client, team, "bob", visibility="team").json()["id"]

    response = client.post(f"/documents/{doc_id}/access", json={"email": "carol@example.com"},
                           headers=team["erin"])
    assert response.status_code == 403


def test_cannot_grant_access_to_outsider(client, team):
    doc_id = upload(client, team, "bob", visibility="restricted").json()["id"]

    response = client.post(f"/documents/{doc_id}/access", json={"email": "dave@example.com"},
                           headers=team["bob"])
    assert response.status_code == 400
    assert client.get(f"/documents/{doc_id}", headers=team["dave"]).status_code == 404
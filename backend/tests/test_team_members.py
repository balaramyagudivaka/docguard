"""Tests for adding members and changing roles (owner-only actions)."""

import pytest


@pytest.fixture
def team(client, make_user):
    """A team owned by Alice, with Bob as member and Carol as viewer. Dave is an outsider."""
    users = {name: make_user(f"{name}@example.com") for name in ("alice", "bob", "carol", "dave")}
    team_id = client.post("/teams", json={"name": "Lab"}, headers=users["alice"]).json()["id"]
    client.post(f"/teams/{team_id}/members", json={"email": "bob@example.com", "role": "member"},
                headers=users["alice"])
    client.post(f"/teams/{team_id}/members", json={"email": "carol@example.com", "role": "viewer"},
                headers=users["alice"])
    return {"id": team_id, **users}


# user ids are assigned in creation order: alice=1, bob=2, carol=3, dave=4
BOB, CAROL, ALICE = 2, 3, 1


# ---------- adding members ----------

def test_owner_can_add_member(client, team):
    response = client.post(f"/teams/{team['id']}/members",
                           json={"email": "dave@example.com", "role": "viewer"}, headers=team["alice"])

    assert response.status_code == 201
    assert response.json() == {"user_id": 4, "email": "dave@example.com", "role": "viewer"}


def test_added_member_can_see_team(client, team):
    response = client.get(f"/teams/{team['id']}", headers=team["bob"])

    assert response.status_code == 200
    assert response.json()["my_role"] == "member"
    assert len(response.json()["members"]) == 3


def test_member_cannot_add_people(client, team):
    response = client.post(f"/teams/{team['id']}/members",
                           json={"email": "dave@example.com"}, headers=team["bob"])
    assert response.status_code == 403


def test_viewer_cannot_add_people(client, team):
    response = client.post(f"/teams/{team['id']}/members",
                           json={"email": "dave@example.com"}, headers=team["carol"])
    assert response.status_code == 403


def test_outsider_cannot_add_people(client, team):
    response = client.post(f"/teams/{team['id']}/members",
                           json={"email": "dave@example.com"}, headers=team["dave"])
    assert response.status_code == 404  # to Dave, the team doesn't exist


def test_cannot_add_unknown_email(client, team):
    response = client.post(f"/teams/{team['id']}/members",
                           json={"email": "nobody@example.com"}, headers=team["alice"])
    assert response.status_code == 404


def test_cannot_add_same_person_twice(client, team):
    response = client.post(f"/teams/{team['id']}/members",
                           json={"email": "bob@example.com"}, headers=team["alice"])
    assert response.status_code == 409


def test_invalid_role_is_rejected(client, team):
    response = client.post(f"/teams/{team['id']}/members",
                           json={"email": "dave@example.com", "role": "admin"}, headers=team["alice"])
    assert response.status_code == 422


# ---------- changing roles ----------

def test_owner_can_change_role(client, team):
    response = client.patch(f"/teams/{team['id']}/members/{BOB}",
                            json={"role": "viewer"}, headers=team["alice"])

    assert response.status_code == 200
    assert response.json()["role"] == "viewer"
    assert client.get(f"/teams/{team['id']}", headers=team["bob"]).json()["my_role"] == "viewer"


def test_member_cannot_change_roles(client, team):
    response = client.patch(f"/teams/{team['id']}/members/{CAROL}",
                            json={"role": "member"}, headers=team["bob"])
    assert response.status_code == 403


def test_member_cannot_promote_themselves(client, team):
    response = client.patch(f"/teams/{team['id']}/members/{BOB}",
                            json={"role": "owner"}, headers=team["bob"])
    assert response.status_code == 403


def test_last_owner_cannot_be_demoted(client, team):
    response = client.patch(f"/teams/{team['id']}/members/{ALICE}",
                            json={"role": "member"}, headers=team["alice"])
    assert response.status_code == 409


def test_owner_can_step_down_if_another_owner_exists(client, team):
    client.patch(f"/teams/{team['id']}/members/{BOB}", json={"role": "owner"}, headers=team["alice"])

    response = client.patch(f"/teams/{team['id']}/members/{ALICE}",
                            json={"role": "member"}, headers=team["alice"])
    assert response.status_code == 200


def test_changing_role_of_non_member_returns_404(client, team):
    response = client.patch(f"/teams/{team['id']}/members/4",
                            json={"role": "member"}, headers=team["alice"])
    assert response.status_code == 404
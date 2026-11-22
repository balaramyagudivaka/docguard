"""Tests for creating, listing and viewing teams."""


def test_create_team_makes_creator_owner(client, make_user):
    alice = make_user("alice@example.com")
    response = client.post("/teams", json={"name": "Research Lab"}, headers=alice)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Research Lab"
    assert body["my_role"] == "owner"


def test_create_team_requires_login(client):
    response = client.post("/teams", json={"name": "Research Lab"})

    assert response.status_code == 401


def test_team_name_cannot_be_empty(client, make_user):
    alice = make_user("alice@example.com")
    response = client.post("/teams", json={"name": ""}, headers=alice)

    assert response.status_code == 422


def test_list_shows_only_my_teams(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    client.post("/teams", json={"name": "Alice Team"}, headers=alice)
    client.post("/teams", json={"name": "Bob Team"}, headers=bob)

    names = [t["name"] for t in client.get("/teams", headers=alice).json()]
    assert names == ["Alice Team"]


def test_member_can_view_team_and_members(client, make_user):
    alice = make_user("alice@example.com")
    team_id = client.post("/teams", json={"name": "Research Lab"}, headers=alice).json()["id"]

    response = client.get(f"/teams/{team_id}", headers=alice)
    assert response.status_code == 200
    body = response.json()
    assert body["my_role"] == "owner"
    assert body["members"] == [{"user_id": 1, "email": "alice@example.com", "role": "owner"}]


def test_non_member_cannot_see_team(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    team_id = client.post("/teams", json={"name": "Research Lab"}, headers=alice).json()["id"]

    response = client.get(f"/teams/{team_id}", headers=bob)
    assert response.status_code == 404  # to Bob, the team doesn't exist


def test_missing_team_returns_404(client, make_user):
    alice = make_user("alice@example.com")

    response = client.get("/teams/999", headers=alice)
    assert response.status_code == 404
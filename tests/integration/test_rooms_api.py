def _get_auth_header(test_client, username="alice", email="alice@test.com"):
    test_client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "password123"},
    )
    login_res = test_client.post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_room_and_list(test_client):
    headers = _get_auth_header(test_client, "roomcreator", "creator@test.com")

    # Create room
    create_res = test_client.post(
        "/rooms/",
        json={"name": "Engineering", "description": "Engineers room", "is_private": False},
        headers=headers,
    )
    assert create_res.status_code == 201
    room_data = create_res.json()
    assert room_data["name"] == "Engineering"
    room_id = room_data["id"]

    # List public rooms
    list_res = test_client.get("/rooms/", headers=headers)
    assert list_res.status_code == 200
    rooms = list_res.json()
    assert any(r["id"] == room_id for r in rooms)


def test_join_room_and_list_members(test_client):
    owner_headers = _get_auth_header(test_client, "owner", "owner@test.com")
    member_headers = _get_auth_header(test_client, "joiner", "joiner@test.com")

    # Owner creates room
    c_res = test_client.post(
        "/rooms/",
        json={"name": "Design Team", "is_private": False},
        headers=owner_headers,
    )
    room_id = c_res.json()["id"]

    # Joiner joins room
    join_res = test_client.post(f"/rooms/{room_id}/join", headers=member_headers)
    assert join_res.status_code == 200

    # Get room members
    members_res = test_client.get(f"/rooms/{room_id}/members", headers=member_headers)
    assert members_res.status_code == 200
    members = members_res.json()
    # Expect 2 members (creator + joiner)
    assert len(members) == 2


def test_join_nonexistent_room_returns_404(test_client):
    headers = _get_auth_header(test_client, "loner", "loner@test.com")
    res = test_client.post("/rooms/99999/join", headers=headers)
    assert res.status_code == 404

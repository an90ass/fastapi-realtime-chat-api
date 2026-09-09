def _register_and_get_token(test_client, username, email):
    test_client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "password123"},
    )
    res = test_client.post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    return res.json()["access_token"]


def test_get_messages_cursor_pagination(test_client):
    token = _register_and_get_token(test_client, "chatuser", "chatuser@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create room
    create_room_res = test_client.post(
        "/rooms/",
        json={"name": "Frontend Squad", "is_private": False},
        headers=headers,
    )
    room_id = create_room_res.json()["id"]

    # Initial history should be empty
    get_res = test_client.get(f"/chat/{room_id}/messages", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["items"] == []
    assert data["has_more"] is False


def test_get_messages_non_member_returns_403(test_client):
    owner_token = _register_and_get_token(test_client, "chatformat_owner", "cf_owner@test.com")
    other_token = _register_and_get_token(test_client, "outsider", "outsider@test.com")

    # Owner creates room
    c_res = test_client.post(
        "/rooms/",
        json={"name": "Secret Squad", "is_private": True},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    room_id = c_res.json()["id"]

    # Outsider tries to read messages
    res = test_client.get(
        f"/chat/{room_id}/messages",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert res.status_code == 403
    assert "not a member" in res.json()["detail"]

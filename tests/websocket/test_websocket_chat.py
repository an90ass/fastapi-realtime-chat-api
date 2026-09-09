from contextlib import contextmanager
import json

from starlette.websockets import WebSocketDisconnect


@contextmanager
def assert_raises_ws_disconnect(expected_code: int = 1008):
    """Context manager validating WebSocket disconnection code without requiring pytest."""
    disconnected = False
    try:
        yield
    except WebSocketDisconnect as exc:
        disconnected = True
        assert exc.code == expected_code, f"Expected WS code {expected_code}, got {exc.code}"
    assert disconnected, "Expected WebSocketDisconnect was not raised"


def _setup_user_and_room(test_client, username="wsuser", email="wsuser@test.com", room_name="WS Room"):
    # Register & Login
    test_client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "password123"},
    )
    login_res = test_client.post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create Room (user auto-joined)
    room_res = test_client.post(
        "/rooms/",
        json={"name": room_name, "is_private": False},
        headers=headers,
    )
    room_id = room_res.json()["id"]
    return token, room_id


def test_websocket_connection_and_message_broadcast(test_client):
    token, room_id = _setup_user_and_room(test_client, "chatter1", "chatter1@test.com", "Chatroom Alpha")

    # Connect via secure Query Param endpoint
    with test_client.websocket_connect(f"/chat/ws/{room_id}?token={token}") as ws:
        # Send a message
        ws.send_text(json.dumps({"content": "Hello from automated test!"}))

        # Verify invalid JSON handling returns error response
        ws.send_text("not-a-json-string")
        response = json.loads(ws.receive_text())
        assert "error" in response


def test_websocket_invalid_token_rejected_with_1008(test_client):
    _, room_id = _setup_user_and_room(test_client, "chatter2", "chatter2@test.com", "Chatroom Beta")

    with (
        assert_raises_ws_disconnect(1008),
        test_client.websocket_connect(f"/chat/ws/{room_id}?token=invalid_token_12345"),
    ):
        pass


def test_websocket_non_member_rejected_with_1008(test_client):
    _, room_id = _setup_user_and_room(test_client, "creator_ws", "cws@test.com", "Private Vault")

    # Register second user who has NOT joined the room
    test_client.post(
        "/auth/register",
        json={"username": "intruder_ws", "email": "intruder_ws@test.com", "password": "password123"},
    )
    res = test_client.post(
        "/auth/login",
        json={"email": "intruder_ws@test.com", "password": "password123"},
    )
    outsider_token = res.json()["access_token"]

    with (
        assert_raises_ws_disconnect(1008),
        test_client.websocket_connect(f"/chat/ws/{room_id}?token={outsider_token}"),
    ):
        pass

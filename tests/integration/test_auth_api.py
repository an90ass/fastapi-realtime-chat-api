def test_register_user_endpoint_success(test_client):
    response = test_client.post(
        "/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data
    assert data["id"] is not None


def test_register_duplicate_user_returns_400(test_client):
    payload = {"username": "duplicate", "email": "duplicate@example.com", "password": "password123"}
    r1 = test_client.post("/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = test_client.post("/auth/register", json=payload)
    assert r2.status_code == 400
    assert "already registered" in r2.json()["detail"]


def test_login_and_get_me_flow(test_client):
    # Register user
    test_client.post(
        "/auth/register",
        json={"username": "loggeduser", "email": "logged@example.com", "password": "secureSecret1"},
    )

    # Login
    login_res = test_client.post(
        "/auth/login",
        json={"email": "logged@example.com", "password": "secureSecret1"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # Access protected /auth/me
    me_res = test_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == "loggeduser"
    assert me_data["email"] == "logged@example.com"


def test_login_invalid_password_returns_401(test_client):
    test_client.post(
        "/auth/register",
        json={"username": "someone", "email": "someone@example.com", "password": "realPassword"},
    )
    res = test_client.post(
        "/auth/login",
        json={"email": "someone@example.com", "password": "wrongPassword"},
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]


def test_protected_route_without_token_returns_401(test_client):
    res = test_client.get("/auth/me")
    assert res.status_code == 401

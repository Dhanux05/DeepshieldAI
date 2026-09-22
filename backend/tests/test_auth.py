from app.constants.roles import Roles
from app.models.user import User

from tests.conftest import register_and_login


def test_register_creates_user_with_default_user_role(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "password": "Sup3rSecret!",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["is_active"] is True

    user = db_session.query(User).filter(User.email == "ada@example.com").first()
    assert user is not None
    # AuthService._get_default_role() resolves "User" by name, never by a
    # hardcoded id — self-registration must never be able to grant Admin.
    assert user.role.role_name == Roles.USER


def test_register_rejects_duplicate_email(client):
    payload = {
        "full_name": "Ada Lovelace",
        "email": "dup@example.com",
        "password": "Sup3rSecret!",
    }

    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 200

    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 400
    assert "already registered" in second.json()["detail"].lower()


def test_login_success_returns_working_token(client):
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Grace Hopper",
            "email": "grace@example.com",
            "password": "Sup3rSecret!",
        },
    )

    login = client.post(
        "/api/auth/login",
        json={"email": "grace@example.com", "password": "Sup3rSecret!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert login.json()["token_type"] == "bearer"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "grace@example.com"
    # UserMeResponse resolves role_id -> role_name so the frontend never has
    # to hardcode an id->name mapping (see schemas/user.py's docstring).
    assert body["role_name"] == Roles.USER


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Grace Hopper",
            "email": "grace2@example.com",
            "password": "Sup3rSecret!",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "grace2@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert response.status_code == 401


def test_protected_route_requires_a_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_protected_route_rejects_a_garbage_token(client):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_change_password_requires_correct_current_password(client):
    headers = register_and_login(client, "rotate@example.com")

    response = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "WrongOne!", "new_password": "NewPassw0rd!"},
    )
    assert response.status_code == 400

    response = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "Sup3rSecret!", "new_password": "NewPassw0rd!"},
    )
    assert response.status_code == 200

    # The old password no longer works; the new one does.
    old_login = client.post(
        "/api/auth/login",
        json={"email": "rotate@example.com", "password": "Sup3rSecret!"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login",
        json={"email": "rotate@example.com", "password": "NewPassw0rd!"},
    )
    assert new_login.status_code == 200

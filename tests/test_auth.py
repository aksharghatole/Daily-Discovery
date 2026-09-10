import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient

TEST_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test_auth.sqlite3"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

import database.db as database_module
import backend.app.main as app_module

importlib.reload(database_module)
importlib.reload(app_module)

app = app_module.app

client = TestClient(app)


def _register(email: str, password: str = "StrongPass1", display_name: str = "Test User"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    return response


def test_register_login_and_me():
    email = "alice.auth@example.com"
    password = "StrongPass1"

    response = _register(email, password, "Alice")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["email"] == email

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["email"] == email

    unauthorized = client.get("/api/auth/me")
    assert unauthorized.status_code == 401


def test_duplicate_email_and_weak_password_are_rejected():
    email = "bob.auth@example.com"
    first = _register(email, "StrongPass1", "Bob")
    assert first.status_code == 201

    second = _register(email, "StrongPass1", "Another Bob")
    assert second.status_code == 409

    weak = _register("weak.auth@example.com", "weak", "Weak User")
    assert weak.status_code == 422


def test_change_password_and_logout():
    email = "charlie.auth@example.com"
    password = "StrongPass1"
    register = _register(email, password, "Charlie")
    assert register.status_code == 201

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login.json()["access_token"]
    refresh = login.json()["refresh_token"]

    changed = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": password, "new_password": "EvenStronger2"},
    )
    assert changed.status_code == 200, changed.text

    logout = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
        json={"refresh_token": refresh},
    )
    assert logout.status_code == 200


def test_authenticated_users_do_not_share_favorites_or_history():
    alice_email = "alice.isolation@example.com"
    bob_email = "bob.isolation@example.com"
    a = _register(alice_email, "StrongPass1", "Alice")
    b = _register(bob_email, "StrongPass1", "Bob")
    assert a.status_code == 201
    assert b.status_code == 201

    a_login = client.post(
        "/api/auth/login",
        json={"email": alice_email, "password": "StrongPass1"},
    )
    b_login = client.post(
        "/api/auth/login",
        json={"email": bob_email, "password": "StrongPass1"},
    )
    a_headers = {"Authorization": f"Bearer {a_login.json()['access_token']}"}
    b_headers = {"Authorization": f"Bearer {b_login.json()['access_token']}"}

    discovery = client.get("/api/discoveries/today").json()[0]
    favorite = client.post(
        f"/api/discoveries/{discovery['id']}/favorite",
        headers=a_headers,
    )
    assert favorite.status_code == 200

    a_favorites = client.get("/api/favorites", headers=a_headers)
    b_favorites = client.get("/api/favorites", headers=b_headers)
    assert a_favorites.status_code == 200
    assert b_favorites.status_code == 200
    assert a_favorites.json()["total"] >= 1
    assert b_favorites.json()["total"] == 0

    a_history = client.get("/api/history", headers=a_headers)
    b_history = client.get("/api/history", headers=b_headers)
    assert a_history.status_code == 200
    assert b_history.status_code == 200
    assert a_history.json()["total"] >= 1
    assert b_history.json()["total"] == 0

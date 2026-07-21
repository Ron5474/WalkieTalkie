"""API tests for auth endpoints using FastAPI TestClient + a temp DB (no LLM calls)."""
import pytest
from fastapi.testclient import TestClient

import app.db.database as database


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "api.db"))
    database.init_db()
    from app.main import app
    return TestClient(app)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_login_and_me(client):
    r = client.post("/api/auth/register", json={"username": "alice", "password": "password123", "budget": 20})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["session_token"]
    token = body["session_token"]

    me = client.get("/api/auth/me", headers=_auth(token))
    assert me.status_code == 200 and me.json()["user"]["user_id"] == "alice"

    login = client.post("/api/auth/login", json={"username": "ALICE", "password": "password123"})
    assert login.status_code == 200 and login.json()["session_token"]


def test_duplicate_register_conflicts(client):
    client.post("/api/auth/register", json={"username": "bob", "password": "password123"})
    r = client.post("/api/auth/register", json={"username": "bob", "password": "password123"})
    assert r.status_code == 409 and r.json()["detail"] == "username_taken"


def test_login_wrong_password_401(client):
    client.post("/api/auth/register", json={"username": "carol", "password": "password123"})
    r = client.post("/api/auth/login", json={"username": "carol", "password": "wrong"})
    assert r.status_code == 401 and r.json()["detail"] == "invalid_credentials"


def test_weak_password_400(client):
    r = client.post("/api/auth/register", json={"username": "dave", "password": "short"})
    assert r.status_code == 400 and r.json()["detail"] == "weak_password"


def test_protected_route_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.patch("/api/user/profile", json={"budget": 40}).status_code == 401


def test_profile_update_scoped_to_session_user(client):
    tok = client.post("/api/auth/register", json={"username": "erin", "password": "password123"}).json()["session_token"]
    r = client.patch("/api/user/profile", json={"budget": 42}, headers=_auth(tok))
    assert r.status_code == 200 and r.json()["profile"]["budget"] == 42

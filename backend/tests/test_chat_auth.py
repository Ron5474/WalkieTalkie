"""Chat auth gate + tool identity binding (no LLM calls)."""
import pytest
from fastapi.testclient import TestClient

import app.db.database as database
from app.services.chat_service import enforce_tool_identity


def test_enforce_tool_identity_overrides_user_scoped_tools():
    # The model tried to target another user; the server must overwrite it.
    args = enforce_tool_identity("fetch_user_profile", {"user_id": "victim"}, "alice")
    assert args["user_id"] == "alice"
    args = enforce_tool_identity("record_visited_place", {"user_id": "victim", "place_name": "X"}, "alice")
    assert args["user_id"] == "alice"


def test_enforce_tool_identity_leaves_other_tools_untouched():
    args = enforce_tool_identity("search_web", {"query": "tacos"}, "alice")
    assert args == {"query": "tacos"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "chat.db"))
    database.init_db()
    from app.main import app
    return TestClient(app)


def test_chat_without_session_is_401(client):
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}], "city": "San Francisco"})
    assert r.status_code == 401

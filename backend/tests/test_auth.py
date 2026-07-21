"""Unit tests for password hashing + credentialed user creation (no server, temp DB)."""
import app.db.database as database


def _fresh_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file))
    database.init_db()


def test_hash_roundtrip_and_wrong_password(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    import secrets
    salt = secrets.token_bytes(16)
    h = database._hash_password("correct horse", salt)
    assert database._verify_password("correct horse", salt.hex(), h) is True
    assert database._verify_password("wrong", salt.hex(), h) is False


def test_same_password_different_salt_differs(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    import secrets
    h1 = database._hash_password("pw", secrets.token_bytes(16))
    h2 = database._hash_password("pw", secrets.token_bytes(16))
    assert h1 != h2


def test_create_user_and_duplicate(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    ok = database.create_user_with_password("Alice", "password123", budget=20)
    assert ok["ok"] is True
    assert ok["user_id"] == "alice"
    dup = database.create_user_with_password("alice", "password123")
    assert dup == {"ok": False, "error": "username_taken"}


def test_create_user_weak_password_and_empty_username(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    assert database.create_user_with_password("bob", "short")["error"] == "weak_password"
    assert database.create_user_with_password("   ", "password123")["error"] == "username_required"


def test_authenticate_user(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    database.create_user_with_password("carol", "password123")
    assert database.authenticate_user("CAROL", "password123")["user_id"] == "carol"
    assert database.authenticate_user("carol", "nope") is None
    assert database.authenticate_user("nobody", "password123") is None

"""Filesystem paths anchored at the backend root.

Centralizing these removes the `os.path.dirname(__file__)` landmines: modules can
live at any depth inside `app/` and still resolve the DB, vector store, .env, and
seed data relative to `backend/` rather than relative to their own location.
"""
from pathlib import Path

# app/paths.py -> app/ -> backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = BACKEND_ROOT / "data"
CHROMA_DIR = BACKEND_ROOT / "chroma_db"
DB_PATH = BACKEND_ROOT / "walkie_talkie.db"
ENV_PATH = BACKEND_ROOT / ".env"

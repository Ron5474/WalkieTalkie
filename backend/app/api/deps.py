"""Shared FastAPI auth dependency: resolve the bearer token to a user or 401."""
from fastapi import Header, HTTPException

from app.db.database import get_user_by_session


def bearer_token(authorization: str | None) -> str:
    """Extract the raw token from an 'Authorization: Bearer <token>' header."""
    if not authorization:
        return ""
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def require_user(authorization: str | None = Header(default=None)) -> dict:
    user = get_user_by_session(bearer_token(authorization))
    if not user:
        raise HTTPException(status_code=401, detail="invalid_or_expired_session")
    return user

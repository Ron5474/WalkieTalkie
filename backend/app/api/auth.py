import logging

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.deps import bearer_token, require_user
from app.db.database import (
    authenticate_user,
    create_session,
    create_user_with_password,
    get_chat_history,
    get_user_preferences,
    purge_expired_sessions,
    revoke_session,
    save_visited_place,
    update_user_preferences,
)
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
    VisitedPlaceRequest,
)

router = APIRouter()
logger = logging.getLogger("walkietalkie.auth")

_ERROR_STATUS = {
    "username_taken": 409,
    "weak_password": 400,
    "username_required": 400,
}


def _session_payload(user_id: str) -> dict:
    s = create_session(user_id, ttl_hours=24)
    prefs = get_user_preferences(user_id) or {}
    return {"ok": True, **s, "profile": prefs}


@router.post("/api/auth/register")
def auth_register(req: RegisterRequest):
    purge_expired_sessions()
    result = create_user_with_password(
        req.username,
        req.password,
        display_name=req.display_name,
        budget=req.budget,
        dietary=req.dietary,
        country=req.country,
    )
    if not result["ok"]:
        raise HTTPException(status_code=_ERROR_STATUS.get(result["error"], 400), detail=result["error"])
    return _session_payload(result["user_id"])


@router.post("/api/auth/login")
def auth_login(req: LoginRequest):
    purge_expired_sessions()
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    return _session_payload(user["user_id"])


@router.post("/api/auth/logout")
def auth_logout(authorization: str | None = Header(default=None)):
    ok = revoke_session(bearer_token(authorization))
    return {"ok": ok}


@router.get("/api/auth/me")
def auth_me(user: dict = Depends(require_user)):
    return {"ok": True, "user": user}


@router.patch("/api/user/profile")
def update_profile(req: UpdateProfileRequest, user: dict = Depends(require_user)):
    update_user_preferences(user["user_id"], budget=req.budget, dietary=req.dietary, country=req.country)
    prefs = get_user_preferences(user["user_id"]) or {}
    return {"ok": True, "profile": prefs}


@router.post("/api/user/visited")
def save_visited(req: VisitedPlaceRequest, user: dict = Depends(require_user)):
    msg = save_visited_place(user["user_id"], req.place_name, city=req.city)
    return {"ok": True, "message": msg}


@router.get("/api/chat/history")
def chat_history(city: str, limit: int = 100, user: dict = Depends(require_user)):
    rows = get_chat_history(user["user_id"], city, limit=limit)
    return {"ok": True, "history": rows}

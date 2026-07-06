import logging

from fastapi import APIRouter

from app.db.database import (
    canonicalize_user_id,
    create_session,
    ensure_user,
    get_user_by_session,
    get_user_preferences,
    purge_expired_sessions,
    revoke_session,
    save_visited_place,
    update_user_preferences,
)
from app.schemas.auth import (
    LogoutRequest,
    SignInRequest,
    UpdateProfileRequest,
    VisitedPlaceRequest,
)

router = APIRouter()
logger = logging.getLogger("walkietalkie.auth")


@router.post("/api/auth/signin")
def auth_signin(req: SignInRequest):
    uid = canonicalize_user_id(req.user_id)
    if not uid:
        return {"error": "user_id is required"}
    purged = purge_expired_sessions()
    if purged:
        logger.info("Purged expired sessions on signin | deleted=%s", purged)
    ensure_user(uid, display_name=req.display_name or uid)
    if req.budget is not None or req.dietary is not None or req.country is not None:
        update_user_preferences(uid, budget=req.budget, dietary=req.dietary, country=req.country)
    s = create_session(uid, ttl_hours=24)
    prefs = get_user_preferences(uid) or {}
    return {"ok": True, **s, "profile": prefs}


@router.get("/api/auth/me")
def auth_me(session_token: str):
    s = get_user_by_session(session_token)
    if not s:
        return {"ok": False, "error": "invalid_or_expired_session"}
    return {"ok": True, "user": s}


@router.post("/api/auth/logout")
def auth_logout(req: LogoutRequest):
    ok = revoke_session((req.session_token or "").strip())
    return {"ok": ok}


@router.patch("/api/user/profile")
def update_profile(req: UpdateProfileRequest):
    s = get_user_by_session(req.session_token)
    if not s:
        return {"ok": False, "error": "invalid_or_expired_session"}
    update_user_preferences(s["user_id"], budget=req.budget, dietary=req.dietary, country=req.country)
    prefs = get_user_preferences(s["user_id"]) or {}
    return {"ok": True, "profile": prefs}


@router.post("/api/user/visited")
def save_visited(req: VisitedPlaceRequest):
    s = get_user_by_session(req.session_token)
    if not s:
        return {"ok": False, "error": "invalid_or_expired_session"}
    msg = save_visited_place(s["user_id"], req.place_name, city=req.city)
    return {"ok": True, "message": msg}


@router.get("/api/chat/history")
def chat_history(session_token: str, city: str, limit: int = 100):
    from app.db.database import get_chat_history

    s = get_user_by_session(session_token)
    if not s:
        return {"ok": False, "error": "invalid_or_expired_session", "history": []}
    rows = get_chat_history(s["user_id"], city, limit=limit)
    return {"ok": True, "history": rows}

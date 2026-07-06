import time

from fastapi import APIRouter

from app import config
from app.db.database import get_city_index_status
from app.schemas.auth import CityWarmupRequest
from app.services.warmup import CITY_INDEX_TTL_SEC, ensure_city_warmup_async

router = APIRouter()


@router.post("/api/city/warmup")
def city_warmup(req: CityWarmupRequest):
    city = (req.city or "").strip()
    if city not in config.HERO_CITIES:
        return {"ok": False, "error": f"Unsupported city. Choose one of: {', '.join(config.HERO_CITIES)}"}
    ensure_city_warmup_async(city)
    st = get_city_index_status(city)
    return {"ok": True, "city": city, "status": st or {"city": city, "status": "building"}}


@router.get("/api/city/status")
def city_status(city: str):
    city = (city or "").strip()
    if not city:
        return {"ok": False, "error": "city is required"}
    st = get_city_index_status(city)
    if not st:
        return {"ok": True, "city": city, "status": "missing"}
    fresh = int(time.time()) - int(st.get("updated_at") or 0) < CITY_INDEX_TTL_SEC
    return {"ok": True, "city": city, **st, "fresh": fresh}

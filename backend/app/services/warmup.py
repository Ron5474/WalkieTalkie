"""Lazy, background city-index warmup with per-city locking."""
import logging
import threading
import time

from app.db.database import get_city_index_status
from app.ingestion.ingest import ingest_city

logger = logging.getLogger("walkietalkie.warmup")

CITY_INDEX_TTL_SEC = 14 * 24 * 3600
_city_warmup_locks: dict[str, threading.Lock] = {}


def city_is_ready_fresh(city: str) -> bool:
    st = get_city_index_status(city)
    if not st or st.get("status") != "ready":
        return False
    return int(time.time()) - int(st.get("updated_at") or 0) < CITY_INDEX_TTL_SEC


def ensure_city_warmup_async(city: str) -> None:
    city = (city or "").strip()
    if not city:
        return
    if city_is_ready_fresh(city):
        return

    lock = _city_warmup_locks.setdefault(city, threading.Lock())
    if lock.locked():
        return

    def _job():
        if not lock.acquire(blocking=False):
            return
        try:
            logger.info("City warmup start | city=%s", city)
            result = ingest_city(city, max_sources=8)
            logger.info("City warmup complete | city=%s result=%s", city, result)
        except Exception as e:
            logger.exception("City warmup failed | city=%s err=%s", city, e)
        finally:
            lock.release()

    threading.Thread(target=_job, daemon=True).start()

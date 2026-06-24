"""Reverse-image lookup via SerpAPI Google Lens (+ temp public image hosting)."""
import logging
import time
from io import BytesIO

import requests

from app import config

logger = logging.getLogger("walkietalkie.tools")


def _upload_image_to_public_url(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """
    Upload image bytes to a temporary public host and return a direct URL.
    Primary: 0x0.st (plain text URL)
    Fallback: tmpfiles.org (JSON page URL transformed to /dl/ direct URL)
    """
    # Primary: 0x0.st
    try:
        resp = requests.post(
            "https://0x0.st",
            files={"file": ("image.jpg", image_bytes, mime_type)},
            timeout=25,
        )
        resp.raise_for_status()
        url = (resp.text or "").strip()
        if url.startswith("https://"):
            logger.info("Uploaded image to 0x0.st | url=%s", url)
            return url
        logger.warning("0x0.st returned unexpected body: %s", (resp.text or "")[:300])
    except Exception as e:
        logger.warning("0x0.st upload failed: %s", e)

    # Fallback: tmpfiles.org
    try:
        resp = requests.post(
            "https://tmpfiles.org/api/v1/upload",
            files={"file": ("image.jpg", image_bytes, mime_type)},
            timeout=25,
        )
        resp.raise_for_status()
        data = resp.json()
        page_url = str(((data.get("data") or {}).get("url") or "")).strip()
        if page_url and "tmpfiles.org/" in page_url:
            direct_url = page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            if direct_url.startswith("http://"):
                direct_url = "https://" + direct_url[len("http://") :]
            logger.info("Uploaded image to tmpfiles.org | url=%s", direct_url)
            return direct_url
        raise ValueError(f"tmpfiles.org response missing usable URL: {str(data)[:300]}")
    except Exception as e:
        raise RuntimeError(f"All public upload providers failed: {e}")


def _serpapi_get_with_retry(params: dict, retries: int = 2, base_delay_sec: float = 1.5) -> requests.Response:
    """
    GET SerpAPI with retry/backoff for 429 rate-limit responses.
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                "https://serpapi.com/search.json",
                params=params,
                timeout=25,
            )
            if resp.status_code == 429 and attempt < retries:
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        sleep_sec = max(base_delay_sec, float(retry_after))
                    except Exception:
                        sleep_sec = base_delay_sec * (2 ** (attempt - 1))
                else:
                    sleep_sec = base_delay_sec * (2 ** (attempt - 1))
                logger.warning(
                    "SerpAPI rate-limited (429) | attempt=%s/%s | sleeping %.2fs",
                    attempt,
                    retries,
                    sleep_sec,
                )
                time.sleep(sleep_sec)
                continue
            resp.raise_for_status()
            return resp
        except requests.HTTPError as e:
            last_exc = e
            if attempt < retries and getattr(e.response, "status_code", None) == 429:
                sleep_sec = base_delay_sec * (2 ** (attempt - 1))
                logger.warning(
                    "SerpAPI HTTP 429 on exception | attempt=%s/%s | sleeping %.2fs",
                    attempt,
                    retries,
                    sleep_sec,
                )
                time.sleep(sleep_sec)
                continue
            raise
        except Exception as e:
            last_exc = e
            if attempt < retries:
                sleep_sec = base_delay_sec * (2 ** (attempt - 1))
                logger.warning(
                    "SerpAPI transient error | attempt=%s/%s | sleeping %.2fs | err=%s",
                    attempt,
                    retries,
                    sleep_sec,
                    e,
                )
                time.sleep(sleep_sec)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("SerpAPI request failed without specific exception")


def serpapi_google_lens_lookup(image_bytes: bytes, city: str = "", max_results: int = 5) -> dict:
    """
    Reverse-image lookup via SerpAPI Google Reverse Image.
    Returns normalized top matches and knowledge graph if available.
    """
    api_key = config.serpapi_api_key()
    if not api_key:
        logger.warning("SERPAPI_API_KEY missing; cannot perform reverse image lookup")
        return {"ok": False, "error": "SERPAPI_API_KEY not configured", "matches": []}
    try:
        from PIL import Image

        # 1) Resize image to max dimension 1024 for faster and safer downstream requests.
        img = Image.open(BytesIO(image_bytes))
        img = img.convert("RGB")
        max_dim = max(img.size)
        if max_dim > 1024:
            scale = 1024 / float(max_dim)
            new_size = (max(1, int(img.size[0] * scale)), max(1, int(img.size[1] * scale)))
            img = img.resize(new_size, Image.LANCZOS)
        out_buf = BytesIO()
        img.save(out_buf, format="JPEG", quality=88, optimize=True)
        resized_bytes = out_buf.getvalue()

        logger.info(
            "SerpAPI Lens lookup start | city=%s bytes_in=%s bytes_resized=%s max_results=%s",
            city,
            len(image_bytes or b""),
            len(resized_bytes or b""),
            max_results,
        )

        # 2) Upload image to public temp URL host.
        image_url = _upload_image_to_public_url(resized_bytes, mime_type="image/jpeg")
        payload = {}
        serpapi_engine_used = ""
        logger.info("Public image URL ready | url=%s", image_url)
        serpapi_params = {
            "engine": "google_lens",
            "url": image_url,
            "api_key": api_key,
            "hl": "en",
            "gl": "us",
        }
        resp = _serpapi_get_with_retry(serpapi_params, retries=2, base_delay_sec=1.5)
        try:
            payload = resp.json()
        except Exception:
            logger.error(
                "SerpAPI non-JSON response (URL mode) | status=%s body_preview=%s",
                resp.status_code,
                (resp.text or "")[:800],
            )
            payload = {}
        serpapi_engine_used = "google_lens_url"

        visual_matches = (
            payload.get("visual_matches")
            or payload.get("image_results")
            or payload.get("inline_images")
            or payload.get("organic_results")
            or []
        )
        knowledge_graph = payload.get("knowledge_graph") or {}

        matches = []
        for item in visual_matches[:max_results]:
            title = str(item.get("title", "")).strip()
            link = str(item.get("link", "")).strip()
            snippet = str(item.get("snippet", "") or item.get("source", "") or "").strip()
            if len(snippet) > 400:
                snippet = snippet[:400] + "..."
            if not (title or link):
                continue
            matches.append(
                {
                    "title": title,
                    "snippet": snippet,
                    "link": link,
                }
            )

        # Optional city filter score boost for caller-side ranking.
        city_l = (city or "").strip().lower()
        if city_l:
            for m in matches:
                hay = f"{m.get('title','')} {m.get('snippet','')} {m.get('link','')}".lower()
                m["city_hint_match"] = city_l in hay

        result = {
            "ok": True,
            "error": "",
            "matches": matches,
            "knowledge_graph": knowledge_graph,
            "search_metadata": payload.get("search_metadata", {}),
            "image_url": image_url,
            "engine_used": serpapi_engine_used,
        }
        logger.info("SerpAPI Lens lookup complete | matches=%s has_kg=%s", len(matches), bool(knowledge_graph))
        if matches:
            logger.debug("Top image match: %s", str(matches[0])[:500])
        return result
    except Exception as e:
        logger.exception("SerpAPI Google Lens lookup failed: %s", e)
        return {"ok": False, "error": f"SerpAPI Google Lens failed: {e}", "matches": []}

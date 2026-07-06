"""Image-upload research pipeline: reverse-image lookup → web search → prompt block.

There is no vision model in this path. An uploaded image is identified via SerpAPI
Google Lens, then a targeted web search grounds the answer; the result is folded
into the user's text content for the (text-only) chat LLM.
"""
import base64
import binascii
import logging

from app.tools import search_web, serpapi_google_lens_lookup
from app.utils.text_cleanup import preview

logger = logging.getLogger("walkietalkie.image_research")


def format_lens_matches(lens: dict, max_results: int = 5) -> str:
    matches = lens.get("matches") or []
    if not matches:
        return "No image matches found."
    lines = []
    for i, m in enumerate(matches[:max_results], start=1):
        lines.append(
            f"{i}. title={m.get('title','')} | snippet={m.get('snippet','')} | link={m.get('link','')}"
        )
    return "\n".join(lines)


def research_uploaded_image(raw_image_b64: str, user_text: str, city: str) -> str:
    """
    Return an enriched prompt block (Lens matches + web context + instruction) to
    use in place of the user's raw message. Falls back to the original text on any
    failure so chat still proceeds.
    """
    city = city or "San Francisco"
    try:
        logger.info(
            "Image upload detected | first_image_chars=%s", len(raw_image_b64 or "")
        )
        raw_img = raw_image_b64 or ""
        if "," in raw_img:
            raw_img = raw_img.split(",", 1)[1]
        try:
            image_bytes = base64.b64decode(raw_img, validate=False)
        except (binascii.Error, ValueError):
            image_bytes = b""

        lens = (
            serpapi_google_lens_lookup(image_bytes=image_bytes, city=city, max_results=5)
            if image_bytes
            else {"ok": False, "error": "Invalid image payload", "matches": []}
        )
        lens_block = format_lens_matches(lens, max_results=5)
        logger.info(
            "Image lookup result | ok=%s matches=%s error=%s",
            lens.get("ok"),
            len(lens.get("matches") or []),
            lens.get("error", ""),
        )
        logger.debug("Lens match block preview: %s", preview(lens_block, 1200))

        # Targeted web context synthesis from image matches and user intent.
        if lens.get("ok") and (lens.get("matches") or []):
            top_title = str((lens.get("matches") or [{}])[0].get("title", "")).strip()
            web_query = f"{city} {top_title} {user_text}".strip()
        elif lens.get("ok"):
            web_query = f"{city} {user_text}".strip()
        else:
            # Avoid propagating failure/error strings as web search query content.
            web_query = f"{city} image identification from user upload".strip()
        logger.info("Image web query: %s", preview(web_query, 500))
        web_context = search_web.invoke(web_query)
        logger.debug("Image web context preview: %s", preview(str(web_context), 1500))

        is_menu_query = any(k in (user_text or "").lower() for k in ["menu", "dish", "eat", "food"])
        if is_menu_query:
            instruction = (
                "Instruction: Use image recognition matches + web context to identify likely restaurant/menu, "
                "then recommend the most authentic or popular local dish with a short why."
            )
        else:
            instruction = (
                "Instruction: Use image recognition matches + web context to identify the place/mural, "
                "then explain its story (what it is, why it matters)."
            )

        if not lens.get("ok"):
            return (
                f"[SERPAPI GOOGLE LENS STATUS]\nfailed={lens.get('error','unknown')}\n\n"
                f"[WEB SEARCH CONTEXT]\n{str(web_context)[:2200]}\n\n"
                "Instruction: Be transparent that image recognition lookup failed. "
                "Answer from available context; if uncertain, clearly say so."
            )
        elif lens.get("matches"):
            return (
                f"[SERPAPI GOOGLE LENS TOP 5 MATCHES]\n{lens_block}\n\n"
                f"[WEB SEARCH CONTEXT]\n{str(web_context)[:2200]}\n\n"
                f"{instruction}"
            )
        else:
            return (
                "[SERPAPI GOOGLE LENS TOP 5 MATCHES]\nNo confident matches returned.\n\n"
                f"[WEB SEARCH CONTEXT]\n{str(web_context)[:2200]}\n\n"
                "Instruction: Tell the user no confident image match was found. "
                "Then provide a cautious answer from web context."
            )
    except Exception as e:
        logger.exception("Image research processing failed: %s", e)
        return user_text

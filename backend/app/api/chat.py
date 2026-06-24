import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.db.database import get_user_by_session, save_chat_message
from app.schemas.chat import ChatRequest
from app.services.chat_service import run_chat_turn
from app.services.image_research import research_uploaded_image
from app.services.warmup import ensure_city_warmup_async
from app.utils.streaming import stream_response
from app.utils.text_cleanup import friendly_error_message, preview

router = APIRouter()
logger = logging.getLogger("walkietalkie.chat")


def _resolve_tier(request: ChatRequest) -> str:
    t = (request.llm_tier or "large").lower()
    if t in ("small", "s"):
        return "small"
    if t in ("large", "l"):
        return "large"
    m = (request.model or "").lower()
    if m in ("phi4", "small", "vision", "gemini-flash-lite"):
        return "small"
    return "large"


def _resolve_prompting_mode(raw_mode: str | None) -> str:
    mode = (raw_mode or "self_reflection").strip().lower()
    if mode in ("regular", "meta", "chaining", "self_reflection"):
        return mode
    return "self_reflection"


@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    logger.info("--- NEW REQUEST ---")
    tier = _resolve_tier(request)
    prompting_mode = _resolve_prompting_mode(request.prompting_mode)
    logger.info(
        "chat request meta | tier=%s prompting_mode=%s city=%s stream=%s messages=%s",
        tier,
        prompting_mode,
        request.city,
        request.stream,
        len(request.messages or []),
    )

    session = get_user_by_session((request.session_token or "").strip())
    user_id = session["user_id"] if session else "guest_local"
    formatted_messages = []
    last_user_msg_idx: int | None = None

    last_raw_user_message = ""
    if not request.messages:
        error_msg = "Please send at least one message so I can help."
        return StreamingResponse(stream_response(error_msg), media_type="application/x-ndjson")

    city = request.city or "San Francisco"

    for m in request.messages:
        if m.role == "system":
            # Preserve frontend/system constraints so prompt strategy stays aligned.
            formatted_messages.append(SystemMessage(content=m.content))
        elif m.role == "user":
            last_raw_user_message = m.content or ""
            content_str = m.content
            logger.debug("user message preview: %s", preview(m.content))
            if m.images and len(m.images) > 0:
                content_str = research_uploaded_image(m.images[0] or "", m.content or "", city)
            formatted_messages.append(HumanMessage(content=content_str))
            last_user_msg_idx = len(formatted_messages) - 1
        else:
            formatted_messages.append(AIMessage(content=m.content))

    has_device_gps = request.latitude is not None and request.longitude is not None
    if has_device_gps:
        gps_line = (
            f"DEVICE_GPS_AVAILABLE=true; Lat={request.latitude}; Long={request.longitude}. "
            "You may tie the reply to this approximate area when it helps."
        )
    else:
        gps_line = (
            "DEVICE_GPS_AVAILABLE=false. "
            "Do NOT tell the user their GPS, location pin, or device places them in a neighborhood "
            "unless they stated their whereabouts in their own words. "
            "Use focus_city for general guidance only."
        )
    ensure_city_warmup_async(city)
    if last_user_msg_idx is None:
        error_msg = "Please include a user message in the chat payload."
        return StreamingResponse(stream_response(error_msg), media_type="application/x-ndjson")
    formatted_messages[last_user_msg_idx].content = (
        f"Backend context: user_id={user_id}; {gps_line} focus_city={city}.\n\n"
        + formatted_messages[last_user_msg_idx].content
    )

    try:
        final_answer, generation_time = run_chat_turn(
            formatted_messages,
            tier=tier,
            user_id=user_id,
            city=city,
            latitude=request.latitude if has_device_gps else None,
            longitude=request.longitude if has_device_gps else None,
            prompting_mode=prompting_mode,
        )
        # Save only the last user turn + final assistant response for history view.
        user_turn_text = (last_raw_user_message or "").strip()
        if request.messages and request.messages[-1].images:
            user_turn_text = f"{user_turn_text}\n[image_uploaded=true]"
        # Persist history only for authenticated sessions.
        if session:
            save_chat_message(user_id=user_id, city=city, role="user", content=user_turn_text)
            save_chat_message(user_id=user_id, city=city, role="assistant", content=final_answer)
        logger.info("generation complete | tier=%s elapsed=%.3fs", tier, generation_time)
        logger.debug("final answer preview: %s", preview(final_answer, 2000))
        return StreamingResponse(stream_response(final_answer), media_type="application/x-ndjson")
    except Exception as e:
        import traceback

        logger.error("INTERNAL ERROR TRACEBACK:\n%s", traceback.format_exc())
        error_msg = friendly_error_message(e, context="chat")
        return StreamingResponse(stream_response(error_msg), media_type="application/x-ndjson")

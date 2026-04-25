import json
import asyncio
import re
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

import config
from agent_runner import run_chat_turn
from database import (
    create_session,
    ensure_user,
    get_chat_history,
    get_user_by_session,
    get_user_preferences,
    save_chat_message,
    save_visited_place,
    update_user_preferences,
)
from llm_factory import get_chat_llm, get_vision_llm
from prompting import build_system_prompt
from tools import scrape_live_context, scrape_static_history, search_local_history, search_web, get_weather

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None


class ChatRequest(BaseModel):
    """llm_tier: 'small' | 'large' for dual-model experiments. Legacy `model` is still accepted."""

    model: Optional[str] = None
    llm_tier: Optional[str] = "large"
    messages: List[Message]
    stream: Optional[bool] = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = "San Francisco"
    session_token: Optional[str] = None


class ItineraryRequest(BaseModel):
    city: str
    dates: Optional[str] = None
    days: Optional[int] = 1
    budget: Optional[str] = "Moderate"
    llm_tier: Optional[str] = "large"


class HolidayBriefingRequest(BaseModel):
    city: str
    start_date: Optional[str] = None  # YYYY-MM-DD
    days: int = 1


class SignInRequest(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    budget: Optional[int] = None
    dietary: Optional[str] = None
    country: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    session_token: str
    budget: Optional[int] = None
    dietary: Optional[str] = None
    country: Optional[str] = None


class VisitedPlaceRequest(BaseModel):
    session_token: str
    city: str
    place_name: str


_PLACEHOLDER_TITLE_RE = re.compile(
    r"\b(restaurant|place|spot|museum|attraction|landmark)\s*\d+\b|\b(tbd|to be decided|unknown)\b",
    re.IGNORECASE,
)


def _is_placeholder_title(title: str) -> bool:
    if not title:
        return True
    return bool(_PLACEHOLDER_TITLE_RE.search(title.strip()))


def _itinerary_has_placeholder_names(nodes: dict) -> bool:
    for item in (nodes.get("places") or []) + (nodes.get("eats") or []):
        if _is_placeholder_title(str(item.get("title", ""))):
            return True
    return False


def _normalize_eats_quota(nodes: dict, max_ratio: float = 0.25) -> None:
    """
    Keep food suggestions as a small part of the route by default.
    """
    place_count = len(nodes.get("places") or [])
    eats = nodes.get("eats") or []
    if not eats:
        return
    max_eats = max(1, int(place_count * max_ratio)) if place_count else 1
    kept_eats = eats[:max_eats]
    removed_ids = {e.get("id") for e in eats[max_eats:] if e.get("id")}
    nodes["eats"] = kept_eats
    if not removed_ids:
        return
    for day in nodes.get("itinerary", []):
        day["plan"] = [pid for pid in day.get("plan", []) if pid not in removed_ids]


def _extract_json_object(raw: str) -> dict:
    content = (raw or "").strip()
    if "<final_answer>" in content and "</final_answer>" in content:
        content = content.split("<final_answer>")[-1].split("</final_answer>")[0].strip()
    elif "</planning>" in content:
        content = content.split("</planning>")[-1].strip()
    if content.startswith("```json"):
        content = content[7:-3]
    if content.startswith("```"):
        content = content[3:-3]
    start_idx = content.find("{")
    end_idx = content.rfind("}")
    if start_idx != -1 and end_idx != -1:
        content = content[start_idx : end_idx + 1]
    return json.loads(content)


def _normalize_tier_value(raw_tier: str | None) -> str:
    t = (raw_tier or "large").lower()
    if t in ("small", "s"):
        return "small"
    return "large"


async def _invoke_itinerary_model(prompt: str, tier: str) -> str:
    """
    Invoke itinerary model with timeout and one retry.
    """
    timeout_s = max(5.0, float(config.itinerary_timeout_seconds()))
    model_tiers = [tier, tier]
    last_err = None
    for attempt_idx, model_tier in enumerate(model_tiers, start=1):
        try:
            llm = get_chat_llm(model_tier)
            resp = await asyncio.wait_for(
                llm.ainvoke([HumanMessage(content=prompt)]),
                timeout=timeout_s,
            )
            return (resp.content or "").strip()
        except asyncio.TimeoutError as e:
            last_err = RuntimeError(
                f"timed out after {timeout_s:.1f}s (attempt {attempt_idx}, tier={model_tier})"
            )
            print(f">>> [ITINERARY GENERATION] {last_err}")
        except Exception as e:
            last_err = e
            print(
                f">>> [ITINERARY GENERATION] tier={model_tier} failed "
                f"(attempt {attempt_idx}): {repr(e)}"
            )
            continue
    raise RuntimeError(f"all itinerary model attempts failed: {last_err}")


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


vision_llm = None


def _get_vision():
    global vision_llm
    if vision_llm is None:
        vision_llm = get_vision_llm()
    return vision_llm


async def stream_response(text: str):
    words = text.split(" ")
    for word in words:
        chunk = json.dumps({"message": {"content": word + " "}})
        yield chunk + "\n"
        await asyncio.sleep(0.02)


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    print("\n--- NEW REQUEST ---")
    tier = _resolve_tier(request)
    print(f"tier={tier} city={request.city}")

    session = get_user_by_session((request.session_token or "").strip())
    user_id = session["user_id"] if session else "guest_local"
    formatted_messages = []

    for m in request.messages:
        if m.role == "system":
            continue
        if m.role == "user":
            content_str = m.content
            if m.images and len(m.images) > 0:
                print("Vision image detected — API vision model")
                try:
                    vision_prompt = (
                        f"Analyze this image. User asked: {m.content}. "
                        "Identify the landmark, mural, or location in detail. "
                        "If you CANNOT confidently identify the specific landmark or mural, "
                        "output EXACTLY the phrase 'UNKNOWN_LANDMARK' and nothing else."
                    )
                    v_msg = HumanMessage(
                        content=[
                            {"type": "text", "text": vision_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{m.images[0]}"}},
                        ]
                    )
                    v_resp = _get_vision().invoke([v_msg])
                    body = v_resp.content or ""

                    if "UNKNOWN_LANDMARK" in body:
                        print("Vision could not ID — web fallback")
                        gps_context = (
                            f"Lat: {request.latitude}, Long: {request.longitude}"
                            if request.latitude and request.longitude
                            else "Unknown Location"
                        )
                        search_query = f"{m.content} near {gps_context}"
                        web_result = search_web.invoke(search_query)
                        content_str = (
                            f"[IMAGE ANALYSIS FAILED. WEB FALLBACK DATA: {web_result}]. "
                            f"If the web data doesn't answer the user's specific question about the image, "
                            f"apologize once and give a generalized historical note about {gps_context}.\n\n"
                            f"User Question: {m.content}"
                        )
                    else:
                        content_str = f"[IMAGE ANALYSIS CONTEXT: {body}]\n\nUser Question: {m.content}"
                except Exception as e:
                    print(f"Vision processing failed: {e}")

            formatted_messages.append(HumanMessage(content=content_str))
        else:
            formatted_messages.append(AIMessage(content=m.content))

    gps_info = (
        f"Lat: {request.latitude}, Long: {request.longitude}"
        if request.latitude and request.longitude
        else "Location Unknown"
    )
    city = request.city or "San Francisco"
    formatted_messages[-1].content = (
        f"Backend context: user_id={user_id}; GPS={gps_info}; focus_city={city}.\n\n"
        + formatted_messages[-1].content
    )

    try:
        final_answer, generation_time = run_chat_turn(
            formatted_messages,
            tier=tier,
            user_id=user_id,
            city=city,
            latitude=request.latitude,
            longitude=request.longitude,
        )
        # Save only the last user turn + final assistant response for history view.
        user_turn_text = ""
        if formatted_messages:
            last_msg = formatted_messages[-1]
            user_turn_text = str(getattr(last_msg, "content", "") or "")
        # Persist history only for authenticated sessions.
        if session:
            save_chat_message(user_id=user_id, city=city, role="user", content=user_turn_text)
            save_chat_message(user_id=user_id, city=city, role="assistant", content=final_answer)
        print(f"[Profiling] generation {generation_time:.3f}s (tier={tier})")
        return StreamingResponse(stream_response(final_answer), media_type="application/x-ndjson")
    except Exception as e:
        import traceback

        print("INTERNAL ERROR TRACEBACK:")
        print(traceback.format_exc())
        error_msg = f"Agent Error: {repr(e)}"
        return StreamingResponse(stream_response(error_msg), media_type="application/x-ndjson")


@app.post("/api/synthesize-itinerary")
async def synthesize_itinerary(req: ItineraryRequest):
    if req.city not in config.HERO_CITIES:
        return {
            "error": f"Itinerary synthesis is scoped to hero cities: {', '.join(config.HERO_CITIES)}",
            "places": [],
            "eats": [],
            "itinerary": [],
        }

    itinerary_tier = _normalize_tier_value(req.llm_tier)
    print(f"\n--- ITINERARY {req.days} days | {req.city} | {req.dates} | tier={itinerary_tier} ---")

    static_history = scrape_static_history.invoke(req.city)
    live_context = ""
    if req.dates and req.dates.strip():
        live_context = scrape_live_context.invoke({"city": req.city, "date_range": req.dates})

    combined_context = (
        f"--- STATIC HISTORY ---\n{str(static_history)[:2500]}\n\n"
        f"--- LIVE EVENTS & WEATHER ---\n{str(live_context)[:1000]}"
    )

    prompt = f"""You are a travel agent creating a WALKABLE, LOCALITY-FIRST itinerary for {req.city} only.
Duration: {req.days} days. Budget: {req.budget}.

GEOGRAPHY RULES (critical):
- Each day must focus on ONE primary neighborhood / district (or two ADJACENT areas only). Name it in "locality".
- For each day, EVERY stop in "plan" must be places you could reasonably walk between the same day (roughly within ~2 km total spread, same side of town). Do NOT jump from e.g. Fisherman's Wharf to Outer Sunset on the same day.
- Order stops in "plan" as a sensible walking loop or north-to-south stroll through that area — not random city-wide hops.
- Prefer famous sights that sit near each other in real geography; use accurate lat/lng for {req.city}.
- Validate the days it is open based on the travel dates, explicitly checking for 'free museum days' or mapping out the cheapest admission options.
- If the budget is low, bias eats toward that neighborhood too.

CONTENT PRIORITY RULES (critical):
- Prioritize history, architecture, museums, artisan districts, and local culture.
- Food must be a SMALL part of the trip unless the user explicitly asks for a food-focused itinerary.
- Target mix: ~75-90% history/art/culture stops and <=25% food stops.
- Use REAL place names only (proper nouns). NEVER output placeholders like "Kolkata Restaurant 1", "Place 2", "TBD", or generic numbered names.
- If uncertain about a venue name, omit it rather than inventing one.

First, write a <planning> block where you outline your logic step-by-step:
Step 1: Calculate the distance between the requested locations. Are they actually near each other?
Step 2: Verify that all locations are currently open on the requested dates.
Step 3: Double-check that your plan does not involve jumping across town.

Once you have verified the plan in the <planning> block, output your final answer inside a <final_answer> block. 
Inside the <final_answer> block, output EXACTLY a JSON object with keys: "places", "eats", "itinerary".

- "places": array of {{ "id", "title", "lat", "lng", "anecdote", "visited": false }}. Each anecdote should mention the neighborhood or street context (locality), not generic directions.
- "eats": same shape; prefer eateries in or next to the day's area, but keep this list short.
- "itinerary": exactly {req.days} objects, each with:
  - "day" (int),
  - "locality" (string): the neighborhood / quarter / corridor for that day (e.g. "Embarcadero & Ferry Building", "Mission / Valencia St", "North Beach & Chinatown edge"),
  - "plan" (array of ids): only ids from places/eats, ordered for a single-day walking tour in that locality.
- No duplicate ids across days.

Context:
{combined_context}

Output ONLY valid JSON inside the <final_answer> block. No markdown around the JSON."""

    try:
        print(">>> [ITINERARY GENERATION] Prompting LLM with Chain of Thought...")
        nodes = None
        for attempt in range(2):
            attempt_prompt = prompt
            if attempt == 1:
                attempt_prompt += (
                    "\n\nRETRY INSTRUCTIONS: Your previous answer likely had fake or placeholder names. "
                    "Regenerate with only specific real venues and locality-accurate heritage/art stops."
                )
            content = await _invoke_itinerary_model(attempt_prompt, itinerary_tier)
            print(">>> [ITINERARY GENERATION] Received response snippet:", content[:200])
            candidate = _extract_json_object(content)
            if not _itinerary_has_placeholder_names(candidate):
                nodes = candidate
                break
            nodes = candidate

        if nodes is None:
            raise ValueError("Unable to generate itinerary JSON.")

        seen_ids = set()
        for day in nodes.get("itinerary", []):
            unique_plan = []
            for pid in day.get("plan", []):
                if pid not in seen_ids:
                    unique_plan.append(pid)
                    seen_ids.add(pid)
            day["plan"] = unique_plan
        _normalize_eats_quota(nodes, max_ratio=0.25)

        return nodes
    except Exception as e:
        import traceback

        print("JSON Synthesis Error:")
        print(traceback.format_exc())
        return {"places": [], "eats": [], "itinerary": [], "error": str(e)}


@app.post("/api/holiday-briefing")
async def holiday_briefing(req: HolidayBriefingRequest):
    """
    Web search for trip-period weather, then LLM packing suggestions for Holiday Mode.
    """
    if req.city not in config.HERO_CITIES:
        return {
            "error": f"Only hero cities are supported: {', '.join(config.HERO_CITIES)}",
            "packing_advice": "",
            "web_context": "",
        }

    if req.start_date and req.start_date.strip():
        window = f"starting {req.start_date} for {req.days} day(s)"
    else:
        window = f"next {req.days} day(s) (no start date set — generic outlook)"

    try:
        print(f">>> [HOLIDAY BRIEFING] Fetching reliable weather for: {req.city}")
        web = get_weather.invoke({"city": req.city})
        search_q = f"get_weather({req.city})"
        print(">>> [HOLIDAY BRIEFING] Weather data:", str(web)[:200])
    except Exception as e:
        search_q = f"get_weather({req.city})"
        web = f"(weather unavailable: {e})"

    prompt = f"""You help student travelers pack light and smart.

Web search results (may be incomplete or from aggregators — treat as hints, not guarantees):
---
{str(web)[:4000]}
---

Trip: {req.city}. Travel window: {window}.

Write:
1) A short paragraph on likely weather during this window (say if uncertain).
2) A bullet list of clothing and gear (layers, footwear, rain/sun, daypack) suited to this city and length ({req.days} days).
Keep total under 260 words. Friendly, practical tone. No markdown # headers."""

    try:
        llm = get_chat_llm("small")
        resp = llm.invoke([HumanMessage(content=prompt)])
        advice = (resp.content or "").strip()
    except Exception as e:
        return {
            "error": repr(e),
            "packing_advice": "",
            "web_context": str(web)[:2000],
        }

    return {
        "packing_advice": advice,
        "web_context": str(web)[:2000],
        "search_query": search_q,
    }


@app.get("/")
def read_root():
    return {
        "status": "WalkieTalkie backend",
        "hero_cities": list(config.HERO_CITIES),
        "system_prompt_preview": build_system_prompt()[:200] + "...",
    }


@app.post("/api/auth/signin")
def auth_signin(req: SignInRequest):
    uid = req.user_id.strip()
    if not uid:
        return {"error": "user_id is required"}
    ensure_user(uid, display_name=req.display_name or uid)
    if req.budget is not None or req.dietary is not None or req.country is not None:
        update_user_preferences(uid, budget=req.budget, dietary=req.dietary, country=req.country)
    s = create_session(uid, ttl_hours=24)
    prefs = get_user_preferences(uid) or {}
    return {"ok": True, **s, "profile": prefs}


@app.get("/api/auth/me")
def auth_me(session_token: str):
    s = get_user_by_session(session_token)
    if not s:
        return {"ok": False, "error": "invalid_or_expired_session"}
    return {"ok": True, "user": s}


@app.patch("/api/user/profile")
def update_profile(req: UpdateProfileRequest):
    s = get_user_by_session(req.session_token)
    if not s:
        return {"ok": False, "error": "invalid_or_expired_session"}
    update_user_preferences(s["user_id"], budget=req.budget, dietary=req.dietary, country=req.country)
    prefs = get_user_preferences(s["user_id"]) or {}
    return {"ok": True, "profile": prefs}


@app.post("/api/user/visited")
def save_visited(req: VisitedPlaceRequest):
    s = get_user_by_session(req.session_token)
    if not s:
        return {"ok": False, "error": "invalid_or_expired_session"}
    msg = save_visited_place(s["user_id"], req.place_name, city=req.city)
    return {"ok": True, "message": msg}


@app.get("/api/chat/history")
def chat_history(session_token: str, city: str, limit: int = 100):
    s = get_user_by_session(session_token)
    if not s:
        return {"ok": False, "error": "invalid_or_expired_session", "history": []}
    rows = get_chat_history(s["user_id"], city, limit=limit)
    return {"ok": True, "history": rows}


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "openrouter_base_url": config.openrouter_base_url(),
        "has_openrouter_key": bool(config.openrouter_api_key()),
        "embedding_backend": "openrouter" if config.OPENROUTER_EMBEDDING_MODEL else "ollama",
    }


@app.get("/api/qa/status")
def qa_status():
    """One-call smoke test for manual QA: embed dim, tiny chat, vector DB snippet."""
    out: dict = {
        "health": {
            "ok": True,
            "openrouter_base_url": config.openrouter_base_url(),
            "has_openrouter_key": bool(config.openrouter_api_key()),
            "embedding_backend": "openrouter" if config.OPENROUTER_EMBEDDING_MODEL else "ollama",
        },
        "models": {
            "small": config.SMALL_LLM_MODEL,
            "large": config.LARGE_LLM_MODEL,
            "vision": config.VISION_LLM_MODEL,
            "embedding": config.OPENROUTER_EMBEDDING_MODEL or config.EMBEDDING_MODEL,
        },
        "hero_cities": list(config.HERO_CITIES),
    }
    try:
        from llm_factory import get_chat_llm, get_embedding_model

        emb = get_embedding_model()
        dim = len(emb.embed_query("San Francisco walking tour"))
        llm = get_chat_llm("small")
        r = llm.invoke("Reply with exactly: OK")
        chat = (r.content or "").strip()[:200]
        vec = search_local_history.invoke("Ferry Building San Francisco history")
        out["smoke"] = {
            "ok": True,
            "embed_dim": dim,
            "chat_reply": chat,
            "vector_preview": (vec or "")[:600],
            "vector_ok": "failed" not in (vec or "").lower() and len(vec or "") > 50,
        }
    except Exception as e:
        out["smoke"] = {"ok": False, "error": repr(e)}
    return out

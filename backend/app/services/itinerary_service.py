"""Itinerary synthesis, holiday briefing, and walk-story generation."""
from __future__ import annotations

import re

from langchain_core.messages import HumanMessage, SystemMessage

from app import config
from app.llm.factory import get_chat_llm
from app.schemas.itinerary import HolidayBriefingRequest, ItineraryRequest, WalkStoryRequest
from app.services.prompting import build_system_prompt, strip_editor_meta_from_user_text
from app.tools import get_weather, scrape_live_context, scrape_static_history
from app.utils.json_extract import extract_json_object
from app.utils.text_cleanup import friendly_error_message

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


def _normalize_tier_value(raw_tier: str | None) -> str:
    t = (raw_tier or "large").lower()
    if t in ("small", "s"):
        return "small"
    return "large"


def _tier_model_candidates(tier: str) -> list[str]:
    if config.force_ollama_fallback():
        return [config.OLLAMA_LARGE_LLM_MODEL if tier == "large" else config.OLLAMA_SMALL_LLM_MODEL]
    if tier == "large":
        return [
            config.LARGE_LLM_MODEL,
            config.OLLAMA_LARGE_LLM_MODEL,
        ]
    return [config.SMALL_LLM_MODEL, config.OLLAMA_SMALL_LLM_MODEL]


async def _invoke_itinerary_model(prompt: str, tier: str) -> str:
    """
    Invoke itinerary model and wait for provider response.
    """
    model_tiers = [tier, tier]
    model_candidates = _tier_model_candidates(tier)
    provider_mode = "ollama_only" if config.force_ollama_fallback() else "openrouter_with_fallbacks"
    print(
        f">>> [ITINERARY GENERATION] model route | tier={tier} | mode={provider_mode} | "
        f"candidates={model_candidates}"
    )
    last_err = None
    for attempt_idx, model_tier in enumerate(model_tiers, start=1):
        try:
            print(
                f">>> [ITINERARY GENERATION] attempt={attempt_idx} invoking tier={model_tier} "
                f"(fallback chain may apply inside LLM client)"
            )
            llm = get_chat_llm(model_tier)
            resp = await llm.ainvoke([HumanMessage(content=prompt)])
            return (resp.content or "").strip()
        except Exception as e:
            last_err = e
            print(
                f">>> [ITINERARY GENERATION] tier={model_tier} failed "
                f"(attempt {attempt_idx}): {repr(e)}"
            )
            continue
    raise RuntimeError(f"all itinerary model attempts failed: {last_err}")


async def synthesize_itinerary(req: ItineraryRequest) -> dict:
    if req.city not in config.HERO_CITIES:
        return {
            "error": f"Itinerary synthesis is scoped to hero cities: {', '.join(config.HERO_CITIES)}",
            "places": [],
            "eats": [],
            "itinerary": [],
        }

    itinerary_tier = _normalize_tier_value(req.llm_tier)
    itinerary_candidates = _tier_model_candidates(itinerary_tier)
    provider_mode = "ollama_only" if config.force_ollama_fallback() else "openrouter_with_fallbacks"
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
            candidate = extract_json_object(content)
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

        nodes["_debug"] = {
            "tier": itinerary_tier,
            "provider_mode": provider_mode,
            "model_candidates": itinerary_candidates,
        }
        return nodes
    except Exception:
        import traceback

        print("JSON Synthesis Error:")
        print(traceback.format_exc())
        return {
            "places": [],
            "eats": [],
            "itinerary": [],
            "error": "Itinerary generation is temporarily unavailable. Please try again shortly.",
            "_debug": {
                "tier": itinerary_tier,
                "provider_mode": provider_mode,
                "model_candidates": itinerary_candidates,
            },
        }


async def generate_holiday_briefing(req: HolidayBriefingRequest) -> dict:
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
Keep total under 260 words. Friendly, practical tone. No markdown # headers.
Output only the advice text the traveler reads — no editor notes, word counts, or "key edits" lists."""

    try:
        llm = get_chat_llm("small")
        resp = llm.invoke([HumanMessage(content=prompt)])
        advice = strip_editor_meta_from_user_text((resp.content or "").strip())
    except Exception as e:
        safe_err = friendly_error_message(e, context="holiday")
        return {
            "error": safe_err,
            "packing_advice": "",
            "web_context": str(web)[:2000],
        }

    return {
        "packing_advice": advice,
        "web_context": str(web)[:2000],
        "search_query": search_q,
    }


async def generate_walk_story(req: WalkStoryRequest) -> dict:
    """
    Generate a short, vivid walk narration in the main assistant persona.
    This ensures spoken stop stories match the same persona style as chat.
    """
    city = (req.city or "").strip() or "this city"
    place = (req.place_title or "").strip()
    anecdote = (req.anecdote or "").strip()
    tier = _normalize_tier_value(req.llm_tier)
    if not place:
        return {"story": "", "error": "place_title is required"}

    prompt = f"""Create a spoken walking narration for a traveler standing near this place.
City: {city}
Place: {place}
Known local context:
{anecdote}

Requirements:
- 80-150 words.
- Output must be in English.
- Conversational and vivid (not robotic).
- The conversation could include a physical detail to notice right now, one historical/cultural detail and a local secret".
- Add a joke or light-hearted comment if it fits naturally, but don't force humor.
- Calculate the best next spot they should walk to from here, and if it is within a reasonable walking distance, mention it as a recommendation at the end.
- If there are no places to visit in walking distance, mention that fact and recommend another place near by they could visit by using transportation.
- Do not use markdown.
- Output only the spoken narration — no preambles, editor notes, or word counts.
"""
    try:
        llm = get_chat_llm(tier)
        out = await llm.ainvoke(
            [
                SystemMessage(content=build_system_prompt()),
                HumanMessage(content=prompt),
            ]
        )
        story = strip_editor_meta_from_user_text((out.content or "").strip())
        if not story:
            story = f"You're at {place}. {anecdote}".strip()
        return {"story": story, "model_tier": tier}
    except Exception as e:
        fallback = f"You're at {place}. {anecdote}".strip()
        return {"story": fallback, "model_tier": tier, "error": friendly_error_message(e, context="walk_story")}

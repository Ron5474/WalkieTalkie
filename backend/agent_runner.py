"""Cached LangChain agents (small vs large) and a single invoke path for API + eval."""
from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from llm_factory import get_chat_llm
from prompting import apply_self_reflection, build_chained_context, build_system_prompt
from tools import fetch_user_profile, get_weather, record_visited_place, search_local_history, search_web

TOOLS = [search_local_history, fetch_user_profile, record_visited_place, search_web, get_weather]

_agents: dict[str, object] = {}


def get_agent(tier: str):
    if tier not in _agents:
        _agents[tier] = create_agent(
            model=get_chat_llm(tier),
            tools=TOOLS,
            system_prompt=build_system_prompt(),
            debug=False,
        )
    return _agents[tier]


def _transcript_for_reflection(messages: list) -> str:
    lines: list[str] = []
    for m in messages[-12:]:
        role = type(m).__name__
        content = getattr(m, "content", "")
        if isinstance(content, list):
            content = str(content)
        lines.append(f"{role}: {content[:1200]}")
    return "\n".join(lines)


def run_chat_turn(
    formatted_messages: list,
    tier: str,
    user_id: str,
    city: str | None,
    latitude: float | None,
    longitude: float | None,
) -> tuple[str, float]:
    """
    formatted_messages: LangChain HumanMessage/AIMessage list (user content already prepared).
    Returns (final_text, elapsed_seconds).
    """
    import time

    agent = get_agent(tier)
    if formatted_messages:
        last = formatted_messages[-1]
        if isinstance(last, HumanMessage):
            chain = build_chained_context(user_id, city, latitude, longitude)
            if chain:
                last.content = chain + "\n" + last.content

    t0 = time.time()
    state = agent.invoke({"messages": formatted_messages})
    elapsed = time.time() - t0

    final = state["messages"][-1]
    draft = getattr(final, "content", "") or ""
    if isinstance(draft, list):
        draft = str(draft)

    transcript = _transcript_for_reflection(state["messages"])
    polished = apply_self_reflection(tier, draft, transcript)
    return polished, elapsed

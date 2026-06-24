from fastapi import APIRouter

from app import config
from app.services.prompting import build_system_prompt
from app.tools import search_local_history

router = APIRouter()


@router.get("/")
def read_root():
    return {
        "status": "WalkieTalkie backend",
        "hero_cities": list(config.HERO_CITIES),
        "system_prompt_preview": build_system_prompt()[:200] + "...",
    }


@router.get("/api/health")
def health():
    return {
        "ok": True,
        "openrouter_base_url": config.openrouter_base_url(),
        "has_openrouter_key": bool(config.openrouter_api_key()),
        "embedding_backend": "openrouter" if config.OPENROUTER_EMBEDDING_MODEL else "ollama",
    }


@router.get("/api/qa/status")
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
            "embedding": config.OPENROUTER_EMBEDDING_MODEL or config.EMBEDDING_MODEL,
        },
        "hero_cities": list(config.HERO_CITIES),
    }
    try:
        from app.llm.factory import get_chat_llm, get_embedding_model

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

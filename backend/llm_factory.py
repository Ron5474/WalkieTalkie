"""OpenRouter-backed chat/vision + OpenRouter/Ollama embeddings."""
from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_ollama import ChatOllama, OllamaEmbeddings

import config

_embeddings: OpenAIEmbeddings | OllamaEmbeddings | None = None


def _openrouter_base_url() -> str:
    config.assert_api_config()
    return config.openrouter_base_url()


def _openrouter_headers() -> dict[str, str]:
    headers: dict[str, str] = {"X-Title": config.openrouter_title()}
    referer = config.openrouter_referer()
    if referer:
        headers["HTTP-Referer"] = referer
    return headers


def _ollama_chat(model: str, temperature: float = 0.7) -> ChatOllama:
    return ChatOllama(model=model, temperature=temperature, base_url=config.ollama_base_url())


def _openrouter_chat(model: str, temperature: float = 0.7) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=config.openrouter_api_key(),
        base_url=_openrouter_base_url(),
        default_headers=_openrouter_headers(),
    )


def get_chat_llm(tier: str):
    """Return a model chain with automatic fallbacks.

    small : nvidia/nemotron-nano-9b-v2:free  → Ollama small
    large : nvidia/nemotron-3-nano-30b-a3b:free
              → google/gemma-4-31b-it:free
              → Ollama large
    """
    if config.force_ollama_fallback():
        ollama_model = config.OLLAMA_LARGE_LLM_MODEL if tier == "large" else config.OLLAMA_SMALL_LLM_MODEL
        return _ollama_chat(ollama_model)

    if tier == "large":
        primary = _openrouter_chat(config.LARGE_LLM_MODEL)
        mid_fallback = _openrouter_chat(config.LARGE_LLM_FALLBACK_MODEL)
        ollama_fallback = _ollama_chat(config.OLLAMA_LARGE_LLM_MODEL)
        return primary.with_fallbacks([mid_fallback, ollama_fallback])
    else:
        primary = _openrouter_chat(config.SMALL_LLM_MODEL)
        ollama_fallback = _ollama_chat(config.OLLAMA_SMALL_LLM_MODEL)
        return primary.with_fallbacks([ollama_fallback])


def get_vision_llm():
    """Multimodal model via OpenRouter-compatible Chat Completions, with Ollama fallback."""
    if config.force_ollama_fallback():
        return _ollama_chat(config.OLLAMA_VISION_LLM_MODEL, temperature=0)
    primary = _openrouter_chat(config.VISION_LLM_MODEL, temperature=0)
    ollama_fallback = _ollama_chat(config.OLLAMA_VISION_LLM_MODEL, temperature=0)
    return primary.with_fallbacks([ollama_fallback])


def get_embedding_model() -> OpenAIEmbeddings | OllamaEmbeddings:
    global _embeddings
    if _embeddings is None:
        # Allow OpenRouter embeddings even when chat fallback is forced to Ollama.
        # This keeps vector search current without changing chat/vision routing.
        if config.OPENROUTER_EMBEDDING_MODEL:
            _embeddings = OpenAIEmbeddings(
                model=config.OPENROUTER_EMBEDDING_MODEL,
                api_key=config.openrouter_api_key(),
                base_url=_openrouter_base_url(),
                default_headers=_openrouter_headers(),
            )
        else:
            _embeddings = OllamaEmbeddings(
                model=config.EMBEDDING_MODEL,
                base_url=config.ollama_base_url(),
            )
    return _embeddings

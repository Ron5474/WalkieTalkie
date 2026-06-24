"""Search tools: curated local-history vector search + live web search."""
import logging

import chromadb
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

from app.llm.factory import get_embedding_model
from app.paths import CHROMA_DIR

db_path = str(CHROMA_DIR)
logger = logging.getLogger("walkietalkie.tools")


@tool
def search_local_history(query: str) -> str:
    """Useful to search for local history, anecdotes, and context about a neighborhood or landmark (San Francisco & Kolkata curated stories)."""
    try:
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_collection("local_stories")
        embeddings_model = get_embedding_model()
        emb = embeddings_model.embed_query(query)
        q = (query or "").lower()
        city = None
        for c in (
            "san francisco",
            "kolkata",
            "new york",
            "boston",
            "chicago",
            "los angeles",
            "miami",
            "philadelphia",
            "seattle",
            "washington dc",
        ):
            if c in q:
                city = c.title() if c != "washington dc" else "Washington DC"
                break

        if city:
            results = collection.query(query_embeddings=[emb], n_results=3, where={"city": city})
            docs = (results.get("documents") or [[]])[0]
            if not docs:
                results = collection.query(query_embeddings=[emb], n_results=2)
        else:
            results = collection.query(query_embeddings=[emb], n_results=2)

        snippets = []
        for doc in (results.get("documents") or [[]])[0]:
            snippets.append(doc)
        if not snippets:
            return "No local history cache available for that city yet. Use search_web for live context."
        return "\n\n".join(snippets)
    except Exception as e:
        return f"Vector DB query failed ({e}). Rely on search_web or general knowledge with clear uncertainty."


@tool
def search_web(query: str) -> str:
    """Useful to search the internet for live facts, hours, weather, transit, tickets, visas, or unknown places."""
    try:
        logger.info("Web search start | query=%s", query[:300])
        search = DuckDuckGoSearchRun()
        out = search.run(query)
        logger.info("Web search complete | response_chars=%s", len(out or ""))
        logger.debug("Web search preview: %s", (out or "")[:1200])
        return out
    except Exception as e:
        logger.exception("Web search failed: %s", e)
        return f"Web search failed: {e}"

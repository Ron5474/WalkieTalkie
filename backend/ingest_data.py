"""
Ingest curated text into ChromaDB using the currently configured embedding backend.

Run from `backend/`:
  python ingest_data.py

Embedding source is selected by environment:
- OPENROUTER_EMBEDDING_MODEL set -> OpenRouter embeddings
- otherwise -> local Ollama embedding model (EMBEDDING_MODEL)

Requires network for SF URL scraping; Kolkata block is local.
"""
from __future__ import annotations

import os
import requests
from bs4 import BeautifulSoup
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

from llm_factory import get_embedding_model

URLS_SF = [
    "https://49miles.com/2022/a-brief-history-of-san-francisco-everything-you-need-to-know/",
    "https://sfcityguides.org/tour/1840s-san-francisco-and-the-astonishing-legacy-of-americas-first-black-millionaire/",
    "https://sfcityguides.org/find-your-tour/",
]

KOLKATA_FILE = os.path.join(os.path.dirname(__file__), "data", "kolkata_seed.txt")


def scrape_url(url: str) -> str:
    print(f"Scraping {url}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""


def main():
    import config

    config.assert_api_config()

    documents: list[dict] = []
    for url in URLS_SF:
        text = scrape_url(url)
        if text:
            documents.append({"text": text, "source": url})

    if os.path.isfile(KOLKATA_FILE):
        with open(KOLKATA_FILE, encoding="utf-8") as f:
            ktxt = f.read().strip()
        if ktxt:
            documents.append({"text": ktxt, "source": "kolkata_seed_local"})

    print("Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks: list[str] = []
    metadata: list[dict] = []

    for doc in documents:
        splits = text_splitter.split_text(doc["text"])
        chunks.extend(splits)
        metadata.extend([{"source": doc["source"]} for _ in splits])

    print(f"Created {len(chunks)} chunks.")

    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    try:
        client.delete_collection("local_stories")
    except Exception:
        pass
    collection = client.create_collection(name="local_stories")

    emb_model = get_embedding_model()

    print("Embedding chunks with configured embedding backend...")
    for i, chunk in enumerate(chunks):
        if i % 5 == 0:
            print(f"  chunk {i}/{len(chunks)}")
        try:
            emb = emb_model.embed_query(chunk)
            collection.add(
                embeddings=[emb],
                documents=[chunk],
                metadatas=[metadata[i]],
                ids=[f"doc_chunk_{i}"],
            )
        except Exception as e:
            print(f"Failed chunk {i}: {e}")

    print(f"Ingestion complete. {len(chunks)} vectors in {db_path}.")


if __name__ == "__main__":
    main()

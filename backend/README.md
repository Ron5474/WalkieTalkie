# WalkieTalkie backend

## Scope (hero flow)

- **Cities**: US metros + Kolkata — see `config.HERO_CITIES` (must match the app `CITIES` list).
- **Flow**: “Walk with me” (GPS + vector DB stories) + **budget** from SQLite profile + **personalization** (`record_visited_place` / profile tools).
- **Models**: **OpenRouter** for small/large/vision (OpenAI-compatible API) + optional embeddings via OpenRouter or Ollama fallback.

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Set OPENROUTER_API_KEY and model IDs in backend/.env
```

Recommended OpenRouter models:

- `SMALL_LLM_MODEL=openai/gpt-oss-20b:free`
- `LARGE_LLM_MODEL=nvidia/nemotron-3-super-120b-a12b:free`
- `VISION_LLM_MODEL=nvidia/nemotron-nano-12b-v2-vl:free`

## Ingest curated stories into Chroma

Embeddings options:

- **OpenRouter embeddings**: set `OPENROUTER_EMBEDDING_MODEL`.
- **Ollama fallback**: leave `OPENROUTER_EMBEDDING_MODEL` blank and run local Ollama with `EMBEDDING_MODEL` (default `nomic-embed-text:latest`).

```bash
python ingest_data.py
```

If you change the embedding model (or switch from another provider), delete `chroma_db/` or re-run ingest so vector dimensions stay consistent with queries.

## Run API

```bash
uvicorn main:app --reload --port 8000
```

Health: `GET http://localhost:8000/api/health`  
Manual QA bundle (embed + chat + vector): `GET http://localhost:8000/api/qa/status`

## Evaluation

From repo root (with venv active and OpenRouter key set):

```bash
python evaluation/run_eval.py
python evaluation/run_eval.py --injection --tier large
```

Set `OPENROUTER_API_KEY` before running. See `evaluation/EXPERIMENTS.md` for rubric notes.

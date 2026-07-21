# WalkieTalkie

An AI-powered virtual walking tour guide with story retrieval, and multi-user session management.

## 🎯 Overview

**WalkieTalkie Backend** serves as the intelligence engine:
- **LLM Integration**: OpenRouter + optional Ollama for open-source models
- **Vector Database**: Chroma (SQLite) for semantic story/location search
- **Multi-User Sessions**: SQLite profile persistence, auth isolation, personalization
- **Real-Time Tools**: Weather, web search, calendar events, location recommendations
- **Supported Cities**: San Francisco, Kolkata, and extensible via configuration

## Supported Models

### Recommended Free/Sponsored Tiers (OpenRouter)

| Model | Size | Purpose | Tier |
|-------|------|---------|------|
| `openai/gpt-oss-20b:free` | Small | Chat, routing | Free tier |
| `nvidia/nemotron-3-super-120b-a12b:free` | Large | Complex reasoning | Free tier |
| `nvidia/nemotron-nano-12b-v2-vl:free` | Vision | Image understanding | Free tier |

### Embeddings Options

- **OpenRouter**: Set `OPENROUTER_EMBEDDING_MODEL` (e.g., `openai/text-embedding-3-small`)

## Setup

### Prerequisites
- Python 3.8+
- OpenRouter API key (free from https://openrouter.ai/keys)
- Optional: Ollama (for local embeddings/fallback LLM)

### Installation

#### 1. Create Virtual Environment
```bash
cd backend
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` and provide:

```env
# REQUIRED
OPENROUTER_API_KEY=sk-or-v1-...  # Get from https://openrouter.ai/keys

# Model Selection (defaults shown)
LLM_MODEL=openai/gpt-oss-20b:free
EMBEDDING_BACKEND=ollama              # or "openrouter"
OPENROUTER_EMBEDDING_MODEL=          # Leave blank if using Ollama

# Optional APIs
OPENWEATHERMAP_API_KEY=               # Weather integration
SERPAPI_API_KEY=                      # Web search & events

# Ollama (only if EMBEDDING_BACKEND=ollama)
OLLAMA_BASE_URL=http://localhost:11434
```

### 4. Ingest City Data
Populate the vector database with curated stories and landmarks:

```bash
python scripts/ingest_cities.py
```

This:
- Creates `chroma_db/` SQLite database
- Ingests seed data from `backend/data/` (e.g., Kolkata landmarks)
- Generates embeddings for semantic search
- Creates indices for fast retrieval

**Important**: If you change embedding models, delete `chroma_db/` before re-running to ensure vector dimensions stay consistent.

## Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### Health Check
```bash
curl http://localhost:8000/api/health
```

**Response** (example):
```json
{
  "ok": true,
  "openrouter_base_url": "https://openrouter.ai/api/v1",
  "has_openrouter_key": true,
  "embedding_backend": "ollama"
}
```

## API Endpoints

### Core Routes

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/health` | GET | — | Server status & config |
| `/api/qa/status` | GET | — | LLM + embeddings health check |
| `/api/auth/register` | POST | — | Create an account (username + password) → session |
| `/api/auth/login` | POST | — | Log in → session |
| `/api/auth/logout` | POST | Bearer | Revoke the current session |
| `/api/auth/me` | GET | Bearer | Current user |
| `/api/chat` | POST | Bearer | Chat with the travel assistant |
| `/api/chat/history` | GET | Bearer | City-scoped chat history |
| `/api/user/profile` | PATCH | Bearer | Update budget / dietary / country |
| `/api/user/visited` | POST | Bearer | Record a visited place |
| `/api/synthesize-itinerary` | POST | — | Generate a walking tour |
| `/api/holiday-briefing` | POST | — | Weather + packing briefing |
| `/api/walk-story` | POST | — | Narrated walk story |

### Authentication

The app is gated: every `/api/chat`, `/api/chat/history`, and `/api/user/*` request
requires a valid session. There is **no anonymous/guest access** and no legacy
passwordless `/api/auth/signin`.

1. Register (or log in) to obtain a `session_token`:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123", "budget": 20}'
# → {"ok": true, "session_token": "...", "user_id": "alice", "expires_at": ..., "profile": {...}}
```

2. Send the token as a Bearer header on authenticated routes:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <session_token>" \
  -d '{"messages": [{"role": "user", "content": "Plan a cheap afternoon near Market Street"}], "city": "San Francisco"}'
```

Passwords are hashed with PBKDF2-HMAC-SHA256 (per-user salt). Sessions last 24 hours.

## Multi-User Session Management

### Accounts & Profiles
- Accounts are created with a **username + password** (`/api/auth/register`).
- Per-user SQLite records: visited places, preferences, budget.
- **User-scoped tools are bound to the authenticated session**: `fetch_user_profile`
  and `record_visited_place` always act on the logged-in user — the model cannot be
  prompt-injected into reading or writing another user's data.

### Testing Auth Isolation
Start the server, then run the live probe:
```bash
uvicorn app.main:app --port 8000        # terminal 1
python tests/test_auth_isolation.py     # terminal 2
```

It verifies: registration/login, wrong-password rejection (401), duplicate-registration
conflict (409), unauthenticated chat rejection (401), and that one user's session cannot
surface another user's profile through `/api/chat` (`cross_user_leak: false`).

Fast, server-free unit/API tests:
```bash
python -m pytest tests/test_auth.py tests/test_auth_api.py tests/test_chat_auth.py
```

## Vector Database (Chroma)

### Location
`backend/chroma_db/chroma.sqlite3`

### Collections
- `stories` — narrative content for locations
- `landmarks` — place metadata and descriptions

### Embeddings Lifecycle

**With OpenRouter**:
```python
EMBEDDING_BACKEND=openrouter
OPENROUTER_EMBEDDING_MODEL=openai/text-embedding-3-small
```
→ Embeddings generated on ingest, queried via OpenRouter

**With Ollama** (default):
```python
EMBEDDING_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
```
→ Requires local Ollama running; pulls `nomic-embed-text:latest` automatically

### Rebuilding the DB
```bash
rm -rf chroma_db/
python scripts/ingest_cities.py  # Regenerate with current embeddings
```

## Troubleshooting

### Error: "missing OPENROUTER_API_KEY"
**Cause**: Environment variable not set  
**Fix**: 
1. Get key from https://openrouter.ai/keys
2. Add to `.env`: `OPENROUTER_API_KEY=sk-or-...`
3. Restart server

### Error: "Ollama connection refused"
**Cause**: `EMBEDDING_BACKEND=ollama` but Ollama not running  
**Fix**:
1. Start Ollama: `ollama serve` (on port 11434)
2. OR switch to OpenRouter embeddings in `.env`

### Error: "Vector dimension mismatch"
**Cause**: Changed embedding model without rebuilding DB  
**Fix**:
```bash
rm -rf chroma_db/
python scripts/ingest_cities.py
```

### Frontend Proxy Errors
**Cause**: Backend not reachable from frontend  
**Fix**:
1. Verify backend running: `curl http://localhost:8000/api/health`
2. Check frontend Vite config: `walkie-talkie-app/vite.config.js` should proxy to `8000`
3. Restart frontend dev server

## File Structure

```
backend/
├── app/                     # Application package
│   ├── main.py              # FastAPI app + router wiring (thin)
│   ├── config.py            # Hero cities, model defaults, config loader
│   ├── paths.py             # Filesystem paths anchored at backend root
│   ├── api/                 # HTTP routers
│   │   ├── chat.py          # /api/chat
│   │   ├── itinerary.py     # /api/synthesize-itinerary, /holiday-briefing, /walk-story
│   │   ├── auth.py          # /api/auth/*, /api/user/*, /api/chat/history
│   │   ├── city.py          # /api/city/warmup, /api/city/status
│   │   └── health.py        # /, /api/health, /api/qa/status
│   ├── schemas/             # Pydantic request models
│   ├── services/            # Business logic
│   │   ├── chat_service.py  # Tool-calling loop (run_chat_turn)
│   │   ├── itinerary_service.py
│   │   ├── image_research.py
│   │   ├── warmup.py
│   │   └── prompting.py     # System prompts, prompting strategies
│   ├── tools/               # LangChain tools (search, weather, profile, vision, scrape)
│   ├── llm/factory.py       # LLM/embeddings initialization
│   ├── db/database.py       # SQLite operations
│   ├── ingestion/ingest.py  # Vector-DB ingestion
│   └── utils/               # json_extract, text_cleanup, streaming
├── scripts/                 # Operational scripts
│   ├── ingest_cities.py     # Populate vector DB
│   └── measure_latency.py   # Latency probe
├── tests/                   # QA scripts
│   ├── test_auth_isolation.py
│   └── test_comprehensive.py
├── requirements.txt         # Python dependencies
├── .env.example             # Template (copy to .env)
├── data/                    # Seed data
│   └── kolkata_seed.txt     # Kolkata landmarks
└── chroma_db/               # Vector store (auto-created)
    ├── chroma.sqlite3       # Main DB file
    └── [collection dirs]
```

## Configuration Reference

### Backend Environment Variables

```env
# REQUIRED
OPENROUTER_API_KEY=sk-or-v1-...

# Model Selection
LLM_MODEL=openai/gpt-oss-20b:free          # Main chat model
EMBEDDING_BACKEND=ollama                   # or "openrouter"
OPENROUTER_EMBEDDING_MODEL=                # Set if EMBEDDING_BACKEND=openrouter
OLLAMA_BASE_URL=http://localhost:11434    # Ollama server URL

# APIs (optional)
OPENWEATHERMAP_API_KEY=                    # Weather integration
SERPAPI_API_KEY=                           # Web search & events
```

### City Support

Defined in `config.HERO_CITIES`:
- `san-francisco` (US)
- `kolkata` (India)
- Extensible: add new cities to config and provide seed data

## See Also

- **[Root README](../README.md)** – Full project overview
- **[Frontend README](../walkie-talkie-app/README.md)** – React/PWA setup
- **[Prompting Notes](../docs/PROMPTING_NOTES.md)** – LLM system prompts

## Development

### Running Tests
```bash
python tests/test_auth_isolation.py  # Multi-user auth tests
```

### Code Style
- Follow PEP 8
- Use type hints where practical
- Document complex functions with docstrings
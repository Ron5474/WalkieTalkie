# WalkieTalkie — Restructuring Notes

Proposal for cleaning up and reorganizing the project. Tackled in three layers:
**hygiene** (free wins), **backend decomposition** (the real problem), and
**repo-root organization**.

---

## 1. Repo hygiene — untrack committed artifacts (do this first)

The `.gitignore` already lists `__pycache__/`, `*.db`, and `backend/chroma_db/`,
but those files are **still tracked** because they were committed *before* the
ignore rules existed. `.gitignore` never untracks what's already in the index.
The repo is currently versioning compiled bytecode, a binary vector store, a
SQLite DB, and the `cloudflared` binary.

Untrack them (no code changes, pure git):

```bash
git rm -r --cached backend/__pycache__ backend/chroma_db
git rm --cached backend/walkie_talkie.db backend/comprehensive_qa_results.txt
git rm --cached backend/cloudflared backend/cloudflared.tgz
```

Add the missing ignore rules:

```gitignore
# Tunneling binary (download locally, don't commit)
backend/cloudflared
backend/cloudflared.tgz
```

> Keep `backend/data/kolkata_seed.txt` tracked — it's source data, not a build artifact.

This alone removes ~20 junk files from the tree and shrinks the repo.

---

## 2. Backend — the actual clutter (flat modules + an 858-line `main.py`)

`backend/` is currently a flat pile of modules where `main.py` does HTTP routing
**and** request schemas **and** itinerary business logic **and** the image
pipeline **and** helpers. The fix is a conventional FastAPI package with clear
layers:

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # ONLY: app = FastAPI(), middleware, include_router()  (~40 lines)
│   ├── config.py               # (unchanged) settings + HERO_CITIES
│   │
│   ├── api/                    # HTTP layer — thin routers, one file per concern
│   │   ├── chat.py             # /api/chat
│   │   ├── itinerary.py        # /api/synthesize-itinerary, /api/walk-story, /api/holiday-briefing
│   │   ├── auth.py             # /api/auth/*, /api/user/*
│   │   ├── city.py             # /api/city/warmup, /api/city/status
│   │   └── health.py           # /, /api/health, /api/qa/status
│   │
│   ├── schemas/               # Pydantic request/response models (pulled out of main.py)
│   │   ├── chat.py             # Message, ChatRequest
│   │   ├── itinerary.py        # ItineraryRequest, HolidayBriefingRequest, WalkStoryRequest
│   │   └── auth.py             # SignInRequest, UpdateProfileRequest, ...
│   │
│   ├── services/              # business logic — no FastAPI imports here
│   │   ├── chat_service.py     # run_chat_turn lives here (was agent_runner.py)
│   │   ├── itinerary_service.py# the inline /synthesize logic + placeholder/eats-quota helpers
│   │   ├── image_research.py   # the Lens→web pipeline currently buried in chat_endpoint
│   │   ├── warmup.py           # _ensure_city_warmup_async + locks
│   │   └── prompting.py        # (unchanged)
│   │
│   ├── llm/
│   │   └── factory.py          # was llm_factory.py
│   │
│   ├── tools/                 # split tools.py (410 lines) by concern
│   │   ├── search.py           # search_local_history, search_web
│   │   ├── weather.py          # get_weather
│   │   ├── profile.py          # fetch_user_profile, record_visited_place
│   │   └── vision.py           # serpapi_google_lens_lookup + image upload helpers
│   │
│   ├── db/
│   │   ├── database.py         # connection + schema (was database.py)
│   │   └── repositories.py     # (optional) group the user/session/history query fns
│   │
│   ├── ingestion/
│   │   └── ingest.py           # was ingest_data.py
│   │
│   └── utils/
│       ├── json_extract.py     # _extract_json_object
│       └── text_cleanup.py     # strip_editor_meta..., _preview, _friendly_error_message
│
├── scripts/                   # operational / one-off scripts (NOT imported by app)
│   ├── ingest_cities.py        # the `main()` from ingest_data.py
│   └── measure_latency.py      # (already here)
│
├── tests/                     # QA scripts become real tests
│   ├── test_auth_isolation.py  # was auth_isolation_qa.py
│   └── test_comprehensive.py   # was comprehensive_qa.py
│
├── data/kolkata_seed.txt
├── requirements.txt
├── .env.example
└── README.md
```

### Key decompositions of `main.py`

| Current location in `main.py` | Moves to |
|---|---|
| Pydantic models (62–129) | `app/schemas/*` |
| Placeholder/eats helpers (132–167) + itinerary endpoint (498–614) | `app/services/itinerary_service.py` |
| `_extract_json_object` (169–183) | `app/utils/json_extract.py` |
| Image pipeline inside `chat_endpoint` (363–440) | `app/services/image_research.py` |
| City warmup (286–320) | `app/services/warmup.py` |
| `_friendly_error_message`, `_preview` (266–283) | `app/utils/text_cleanup.py` |
| The 8 endpoints | thin routers under `app/api/` |

Result: `main.py` drops from 858 lines to ~40, and each endpoint body becomes
"validate request → call a service → stream response." The image research and
itinerary logic become independently testable functions instead of being trapped
inside request handlers.

> Naming cleanup worth doing in the move: `agent_runner.py` → `chat_service.py`,
> since `tier`/`mode` are really chat concerns.

---

## 3. Repo root — separate the app from the coursework

The root currently mixes the running app with academic deliverables and stray drafts:

```
WalkieTalkie/
├── backend/                          # (restructured above)
├── walkie-talkie-app/                # frontend — already well-organized, leave it
├── evaluation/                       # keep, but split scripts vs reports (below)
├── docs/
│   ├── PROMPTING_NOTES.md
│   ├── RESTRUCTURING.md              # this file
│   ├── reports/                      # MOVE the eval *.md analyses here
│   │   ├── FINAL_MODEL_COMPARISON.md
│   │   ├── MODEL_COMPARISON_ANALYSIS.md
│   │   └── COMPARISON_SUMMARY.md
│   └── deliverables/                 # MOVE root PDFs + draft here (or untrack entirely)
│       ├── walkie-talkie-VA.pdf
│       └── text-extraction.ipynb
├── tasks/                            # keep as-is
└── README.md
```

Specifics:

- The three loose **PDFs + `*draft*.txt` + the root `.ipynb`** don't belong at
  top level — move to `docs/deliverables/`, or untrack them if they're just
  submission artifacts.
- `evaluation/` is half scripts (`run_eval.py`, `analyze_results.py`,
  `slice_queries.py`) and half **reports** (`FINAL_MODEL_COMPARISON.md`,
  `MODEL_COMPARISON_ANALYSIS.md`, etc.). Keep the `.py` in `evaluation/`, move
  the `.md` write-ups to `docs/reports/`.
- The frontend (`walkie-talkie-app/`) is already clean — standard Vite/React
  `src/{components,services,hooks,utils,db}` layout. Leave it.

---

## Priority & effort

| Layer | Effort | Risk | Payoff |
|---|---|---|---|
| **1. Hygiene** (untrack artifacts) | 5 min | None | High — removes ~20 junk files immediately |
| **3. Root reorg** (move docs/PDFs) | 15 min | None | Medium — clean top level |
| **2. Backend package** | Several hours | Medium — every import path changes | High — the structural fix |

### Caveat on the backend reshuffle

- The **`evaluation/` scripts import backend modules directly** (e.g.
  `run_eval.py` reaches into `agent_runner`/`config`), so moving things will
  break those import paths.
- `database.py` runs `init_db()` on import, and `config.py` resolves
  `backend/.env` relative to its own file location — both assumptions need
  re-checking after the move.
- The `python ingest_data.py` workflow and the READMEs reference current paths.

The backend decomposition needs the eval harness, ingestion entrypoint, and
READMEs updated in the **same pass**.

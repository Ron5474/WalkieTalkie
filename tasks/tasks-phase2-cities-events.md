## Relevant Files

- `walkie-talkie-app/src/App.jsx` - Core React file to host the City and Date Selection dropdowns/UI.
- `walkie-talkie-app/src/utils/geo.js` - Will handle hardcoded latitude/longitude centers for the 9 target cities to bootstrap mapping.
- `backend/tools.py` - Needs two distinct LangChain tools now: one for scraping Wikipedia/history sites, and one for hitting Live News/Weather via DuckDuckGo.
- `backend/main.py` - Core prompt engine holding the `SYSTEM_PROMPT`. Needs updating for the vibrant "human guide" persona.
- `walkie-talkie-app/src/utils/storyTemplating.js` - Could be tweaked to pass tone hints to the text-to-speech engine.

### Notes

- The 9 Target Cities are: SF, Boston, New York, San Diego, Kyoto, Tokyo, London, Kolkata, Mumbai.
- Keep the system prompt updates entirely neutral to avoid AI bias triggers when discussing local politics.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:
- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch (e.g., `git checkout -b feature/phase2-cities-events`)

- [x] 1.0 Build City & Date Selection UI
  - [x] 1.1 Add a Dropdown/Modal in `App.jsx` allowing user to select from the 9 target cities.
  - [x] 1.2 Add a Date Picker component to select anticipated travel dates.
  - [x] 1.3 Ensure this context (City + Dates) is saved to the user's session state and passed back to the `ChatRequest` model.

- [x] 2.0 Implement Static vs. Dynamic Split in Web Scraper
  - [x] 2.1 Refactor `scrape_itinerary_data` in `backend/tools.py` into `scrape_static_history` (focusing on timeless hidden gems).
  - [x] 2.2 Create a new tool `scrape_live_context` in `backend/tools.py` that specifically targets weather, upcoming festivals, and local current events based on the exact dates passed from React.

- [x] 3.0 Integrate Real-Time Weather & Events into Itinerary LLM
  - [x] 3.1 Update the `/api/synthesize-itinerary` prompt in `main.py` to ingest BOTH the static history dump AND the dynamic time-sensitive scrape.
  - [x] 3.2 Ensure JSON output embeds these time-sensitive facts into the node's `anecdote` fields.

- [x] 4.0 Overhaul Storytelling Persona Prompts
  - [x] 4.1 Update the `SYSTEM_PROMPT` in `main.py` from a generic assistant to a highly engaging human guide (cracking jokes, engaging for kids).
  - [x] 4.2 Instruct the `SYSTEM_PROMPT` to analyze and output unbiased, neutral local political context retrieved from the live scrape.

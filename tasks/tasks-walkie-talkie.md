## Relevant Files

- `backend/main.py` - Core FastAPI server housing the LangChain logic, Vision Multi-modal interception, and Prompt Caching parameters.
- `backend/tools.py` - Python definitions for LangChain toolkit. Must be updated for the new Web Scraper and Fallback Vision search logic.
- `walkie-talkie-app/src/db/db.js` - Needs to support dynamic nodes arriving from the itinerary synthesizer rather than relying permanently on `mockNodes.js`.
- `walkie-talkie-app/src/components/SpatialTrigger.jsx` - Will need integration with the new Live Navigation API (Google Maps/OSM) for walking tours.
- `walkie-talkie-app/src/App.jsx` - React component that handles multimodal input interactions and visualizes the walking route suggestions.
- `backend/requirements.txt` - Python dependencies (adding caching libraries or Beautiful Soup scraper tools).

### Notes

- Avoid overwriting existing functional features like the `NarratorService` or `SpatialTrigger`'s base 20m proximity locks; instead, augment them with the new dynamic data streams to form the full "proactive" tour guide mechanism.
- Unit tests should follow typical Python or React conventions alongside their respective files.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:
- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch for this feature (e.g., `git checkout -b feature/dynamic-explorer-bridge`)

- [x] 1.0 Implement Dynamic Web Scraper & Itinerary Synthesizer
  - [x] 1.1 Develop a LangChain tool in `backend/tools.py` capable of scraping top 5-10 blogs/history sites given a city/location.
  - [x] 1.2 Write the Itinerary Synthesizer prompt chain to extract Local Gems vs. Major Tourist monuments from the scraped data.
  - [x] 1.3 Update `walkie-talkie-app/src/db/db.js` to ingest these dynamically synthesized nodes into IndexedDB, entirely replacing `mockNodes.js`.

- [x] 2.0 Integrate Navigation Routing Engine for Guided Walking Tours
  - [x] 2.1 Set up a Routing API integration (e.g., OpenStreetMap or Google Maps Directions API) in the React frontend.
  - [x] 2.2 Update `App.jsx` logic so it can recommend a sequence of generated stops based on user constraints (e.g., Budget, Time).
  - [x] 2.3 Pass the generated route back into `SpatialTrigger.jsx` so the `NarratorService` triggers sequentially along the path.

- [x] 3.0 Add Multi-Tier Fallback Search Logic to Visual "Explorer" Eye
  - [x] 3.1 Update `backend/main.py` Vision prompt to parse standard objects and identify ambiguity explicitly.
  - [x] 3.2 If Vision fails, programmatically trigger the `search_web` tool specifically targeting the user's GPS context to identify the image content.
  - [x] 3.3 Ensure the prompt has fallback logic to issue a "generalized historical fact" if the web search returns null results for the visual query.

- [x] 4.0 Implement High-Performance Prompt Caching
  - [x] 4.1 Profile current Time to First Token (TTFT) speeds.
  - [x] 4.2 Configure KV Prefix Caching in `backend/main.py` using Ollama's caching parameters for the highly static 500-word "Urban Anthropologist" system prompt.
  - [x] 4.3 Verify TTFT remains reliably under the 0.5-second constraint specified in the PRD during multiple conversational turns.

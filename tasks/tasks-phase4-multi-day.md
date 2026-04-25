## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch (e.g., `git checkout -b feature/phase4-tabbed-planner`)

- [x] 1.0 Update UI Controls with Days & Budget Parameters
  - [x] 1.1 Add `numDays` and `budget` tracking state in `App.jsx`.
  - [x] 1.2 Add input fields for these metrics inside the App header.

- [x] 2.0 Overhaul Backend Data Models & Prompting for Complex Architecture
  - [x] 2.1 Update `main.py` `ItineraryRequest` to accept `days` and `budget` parameters.
  - [x] 2.2 Update `/api/synthesize-itinerary` strictly to output structured JSON holding `places`, `eats`, and `itinerary` objects.
  - [x] 2.3 Ensure context prompt instructs LLM to generate "most places" for the city and broad "must eats" (both near POIs and popular independent spots).

- [x] 3.0 Enforce Deduplication & No-Repeat Location Logic
  - [x] 3.1 Inject strict logic into LLM prompt forbidding repeats across the `itinerary` day mappings.

- [x] 4.0 Render the 3-Tab Interface in React (Places, Eats, Day-to-Day)
  - [x] 4.1 Update `db.js` to store and structure the complex JSON payload instead of a flat array.
  - [x] 4.2 Build `Places`, `Eats`, and `Itinerary` UI tab renders inside `App.jsx` when in Holiday mode.

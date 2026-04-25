## Relevant Files
- `walkie-talkie-app/src/App.jsx` - Core React file to host the trip state enum and render the Action Plan vs Chat toggle.
- `walkie-talkie-app/src/db/db.js` - Will need functions to retrieve just `visited: false` nodes and update specific nodes to `visited: true`.
- `backend/main.py` - Needs a new `/api/proactive-nudge` endpoint or modified `/api/chat` that actively sends a message based on time of day.

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch (e.g., `git checkout -b feature/phase3-proactive-planner`)

- [x] 1.0 Implement App State Manager (Planning vs. On-Trip Modes)
  - [x] 1.1 Add `tripMode` state (`planning` vs `active`) to `App.jsx`.
  - [x] 1.2 Add a clean UI toggle switch in the header to flip between Planning and On-Trip views.

- [x] 2.0 Build Daily Action Plan UI
  - [x] 2.1 Create an `ActionPlanList` component logic in `App.jsx`.
  - [x] 2.2 Wire the UI to render nodes from the DB where `visited === false`.

- [x] 3.0 Implement "Mark as Covered" Dynamic Re-Routing
  - [x] 3.1 Add a "Mark as Covered" checkbox/button next to each POI in the Action UI.
  - [x] 3.2 Update `db.js` with `markNodeVisited(id)` functionality.
  - [x] 3.3 Create a React side-effect that prompts the backend LLM to recalculate the itinerary if the user finishes a node exceptionally fast or skips one.

- [x] 4.0 Add Proactive Time-Based Suggestions
  - [x] 4.1 Allow the frontend to ping the backend silently every "X minutes" with the current time of day.
  - [x] 4.2 If the AI observes the user is severely behind schedule or it's nearing mealtime, inject an unsolicited chat message into the feed (e.g., "It's getting late, want to grab dinner near Node B?").

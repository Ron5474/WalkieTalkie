# Mobile-First Frontend Revamp — Design

**Date:** 2026-07-05
**Branch:** `feat/mobile-first-frontend`
**Status:** Approved design → ready for implementation plan

## Goal

Revamp the WalkieTalkie web frontend into a **mobile-first** UI/UX. The app is
most naturally used on a phone — you walk around a city while it narrates local
stories to you — so the interface should be designed for one-handed, on-the-move
phone use first, and scale up gracefully to desktop.

**The visual theme (colors and fonts) does not change.** This is a UX/layout and
code-structure revamp, not a rebrand. Every color and font value is carried over
from the existing app.

## Non-goals

- No changes to backend APIs, request/response shapes, or business logic.
- No changes to the color palette, typography, or overall "warm editorial local
  guide" aesthetic.
- No new product features. This maps every existing feature onto a mobile-first
  layout; nothing is added or removed.
- No changes to data storage (IndexedDB `db.js`, `localStorage` keys) or to the
  `NarratorService` / `useGeolocation` behavior.

## Current state (baseline)

- **Stack:** Vite + React 19, `vite-plugin-pwa`, IndexedDB via `idb`. No router,
  no CSS framework.
- **Structure:** One ~1100-line `src/App.jsx` holding all layout, a large inline
  `<style>` block, and most component markup. Supporting modules:
  `components/SpatialTrigger.jsx`, `services/NarratorService.js`,
  `hooks/useGeolocation.js`, `db/db.js`, `utils/geo.js`,
  `utils/storyTemplating.js`.
- **Layout is desktop-shaped:** a fixed 250px left history sidebar, a horizontal
  6-control planning toolbar that wraps, a header with a mode toggle and action
  buttons. The "Start Walk" experience is a separate full-screen overlay
  (`SpatialTrigger`).

### Existing features (all must be preserved)

- Two "trip modes": **Plan Itinerary** (chat + planning toolbar + history
  sidebar + composer) and **Holiday Mode** (action plan, no composer).
- Planning controls: City select, Model tier (large/small), Prompt strategy
  (regular / meta / chaining / self-reflection), Days, Budget/day, Start date,
  "Generate itinerary".
- Chat: welcome screen with suggestion prompts, streaming assistant responses,
  markdown-ish formatting (bold/italic, pipe tables, "Local Secret" callouts),
  image upload for vision analysis, typing indicator.
- Chat history by city (left sidebar), persisted per user in `localStorage`.
- Holiday action plan: **All Places / Must Eats / Day-to-Day** tabs, weather &
  packing briefing (`/api/holiday-briefing`), "✓ Covered" marking, "Day
  check-in" nudge.
- Live GPS walking narration (`SpatialTrigger`): stop list, distance-to-stop,
  auto-narration within ~20m, replay, walkie-talkie ping sound.
- Auth modal (sign in with a user id + budget), 24h session in `localStorage`.

## Theme (carried over verbatim — extracted into `theme.css`)

Colors:

| Token | Value | Used for |
|-------|-------|----------|
| `--bg` | `#0f0e0b` | app base background |
| `--surface` | `#1a1810` | cards, bubbles, input surfaces |
| `--surface-alt` | `#12110d` | history pane background |
| `--raised` | `#2a2820` | raised controls, selects, borders |
| `--gold` | `#c8a96e` | primary accent, headings |
| `--gold-deep` | `#8b6914` | gradient end, deep accent |
| `--cream` | `#f0ead6` | primary text |
| `--muted` | `#8a7d66` | secondary text |
| `--muted-dim` | `#6b6452` | tertiary text / placeholders |
| `--border` | `#2a2820` | hairline borders |
| gradient | `linear-gradient(135deg, #c8a96e, #8b6914)` | logo, avatars, send button |

Typography (already loaded from Google Fonts in the current app):

- Headings: **Playfair Display**
- Body: **Source Serif 4** (Georgia serif fallback)

These are the exact values already present in `App.jsx` today. `theme.css`
centralizes them as CSS custom properties; components reference the variables.

## Design

### Information architecture — bottom tab bar

The app has three real surfaces. A persistent, thumb-reachable bottom tab bar
maps to them:

| Tab | Absorbs (from today's UI) |
|-----|---------------------------|
| **🗺️ Guide** | The assistant chat: welcome + suggestion chips when empty, streaming message bubbles, image upload, composer. A **city chip** in the top bar opens the City & History sheet; a **gear** opens the Settings sheet. |
| **🧭 Trip** | Consumer controls (City, Days, Budget/day, Start date) + "Generate itinerary", then the generated plan: **Places / Must-Eats / Day-to-Day** sub-tabs, the **weather & packing** briefing, and "✓ Covered". Merges today's planning toolbar and "Holiday Mode" content. |
| **🚶 Walk** | The live GPS walking experience (today's `SpatialTrigger`): stop list, distance-to-stop, auto-narration at ~20m, replay, ping. Promoted from a modal overlay to a first-class tab. |

Slide-up sheets (dark, gold-edged — same modal styling as today's auth modal):

- **Settings sheet** (gear icon): the **eval controls** — Model tier and Prompt
  strategy — plus sign-in state / budget. These stay fully functional but out of
  the primary consumer flow. Default values when untouched: `large` tier,
  `self_reflection` strategy (unchanged from today).
- **City & History sheet** (city chip): switch active city + the "chat history
  by location" list that is currently the left sidebar.
- **Auth sheet**: sign-in (reuses current `signIn` logic and storage).

The current "Plan Itinerary / Holiday Mode" `tripMode` toggle is removed as a
top-level control; its two states become the **Guide** and **Trip** tabs. The
"Day check-in" nudge moves into the Trip tab.

### Screen layout (mobile)

- **Top app bar** — compact, sticky, ~56px: logo mark + "WalkieTalkie" wordmark
  on the left; city chip + gear on the right.
- **Content area** — scrolls; renders the active tab.
- **Composer** (Guide tab only) — sticky above the tab bar: auto-growing
  textarea, 📷 attach, ↑ send. Respects `env(safe-area-inset-bottom)` so it
  clears the phone home indicator.
- **Bottom tab bar** — sticky, 3 tabs, active tab in `--gold`, safe-area
  bottom padding.

Touch targets are ≥44px. The 6-control horizontal toolbar is gone; Trip controls
stack vertically in a compact form.

### Component / file structure

Split the monolithic `App.jsx` into focused components. `App.jsx` becomes a
slim shell owning shared state, tab routing, and sheet visibility.

```
src/
  theme.css                 // palette + fonts + resets as CSS variables
  App.jsx                   // shell: state, active-tab routing, sheet toggles
  components/
    TopBar.jsx              // logo, wordmark, city chip, gear
    TabBar.jsx              // Guide / Trip / Walk
    GuideView.jsx           // welcome, message list, composer host
    MessageList.jsx         // message mapping + typing indicator
    MessageBubble.jsx       // one bubble + formatText / markdown-table logic
    Composer.jsx            // textarea, image attach/preview, send
    TripView.jsx            // trip controls + itinerary/action plan + briefing
    WalkView.jsx            // refactor of SpatialTrigger into a tab
    sheets/
      SettingsSheet.jsx     // eval controls (model tier, prompt strategy) + budget
      CityHistorySheet.jsx  // city switch + chat-history-by-city
      AuthSheet.jsx         // sign-in
```

State ownership: shared state that multiple views/sheets read or write
(selected city, chat-by-city, session/auth, trip params, loading, etc.) stays in
`App.jsx` and is passed down via props. `formatText`, `formatTripDayHeading`,
`CITIES`, the system prompts, `PROMPT_STRATEGIES`, and `suggestedPrompts` move to
small modules or the component that owns them (e.g. `MessageBubble` for
`formatText`, a `constants.js` for `CITIES` / prompts).

**All behavior is preserved exactly:** same API endpoints (`/api/chat`,
`/api/holiday-briefing`, `/api/walk-story`, `/api/auth/signin`,
`/api/user/profile`, `/api/user/visited`), same streaming parse loop, same
IndexedDB access through `db.js`, same `NarratorService` / `useGeolocation`,
same `localStorage` keys (`walkie_talkie_auth_v1`,
`walkie_talkie_chat_by_city_v1_<user>`).

### Theming approach

`theme.css` (imported once in `main.jsx`) defines the tokens above as
`:root` custom properties and sets base `body`/reset rules. The large inline
`<style>` block currently in `App.jsx` is moved into component-scoped CSS (or a
shared stylesheet) that references the variables. The Vite `index.css` default
template styles (unrelated purple `#646cff` link/button defaults) are replaced by
the theme so they stop fighting the app palette.

Because every color/font is a variable sourced from today's values, "same theme,
new UX" is verifiable by diffing the token list against the baseline.

### Responsive scale-up (≥768px)

Mobile-first CSS with a single `min-width: 768px` breakpoint:

- The bottom **tab bar becomes a left nav rail**.
- The Guide's **city/history content docks back as a left side rail** (echoing
  today's sidebar) instead of living only in a sheet.
- Content sits in a centered max-width column so wide screens look intentional
  rather than a stretched phone.

No separate desktop codebase — the same components, adjusted by CSS.

## Testing / verification

- **Manual, mobile-first:** run `npm run dev`, use browser device emulation
  (iPhone-class viewport). Verify each tab, each sheet, the composer + image
  upload, streaming chat, itinerary generation, the weather briefing, and the
  GPS walk flow (geolocation permission + narration). Confirm safe-area insets
  and ≥44px touch targets.
- **Desktop check:** verify the ≥768px layout (nav rail + side rail + centered
  column).
- **Theme parity:** diff the `theme.css` token values against the colors/fonts
  listed above to confirm nothing drifted.
- **Lint:** `npm run lint` passes.
- **Regression:** all preserved features work identically to `main`
  (endpoints, storage keys, narration, streaming).

There is no existing automated test suite in the frontend; verification is
manual plus lint, consistent with the current project.

## Risks / notes

- `SpatialTrigger` uses inline `styles` objects; refactoring it into `WalkView`
  must keep the geolocation-distance and narration side-effect logic intact
  (the ~20m auto-trigger, `locked`/`visited` handling, ping-before-speak).
- The chat streaming loop and `formatText` (pipe tables, Local Secret spans,
  `dangerouslySetInnerHTML`) must move verbatim to avoid rendering regressions.
- PWA plugin config is unchanged; ensure the new entry/styles still build under
  `vite build`.

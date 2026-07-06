# Mobile-First Frontend Revamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Apply the **frontend-design:frontend-design** skill when writing the layout/CSS in Tasks 1, 8, 9, and 10.

**Goal:** Restructure the WalkieTalkie React frontend into a mobile-first UI — a bottom-tab-bar app (Guide / Trip / Walk) with slide-up sheets — while keeping the exact current theme (colors + fonts) and every existing behavior, and splitting the ~1100-line `App.jsx` monolith into focused components.

**Architecture:** `App.jsx` becomes a slim shell owning shared state (city, chat-by-city, auth/session, trip params, active tab, sheet visibility) and passing it via props to presentational components. Three tabs render the three surfaces; three slide-up sheets hold city/history, settings (eval controls), and auth. All styling moves into two global stylesheets (`theme.css` tokens + `app.css` layout/components) referencing CSS variables. No backend, storage, narration, geolocation, or streaming logic changes — those modules are reused as-is.

**Tech Stack:** Vite 7 + React 19, `vite-plugin-pwa`, IndexedDB (`idb`), Web Speech API (`NarratorService`), Geolocation API. No router, no CSS framework, no test runner.

## Global Constraints

- **Theme is frozen.** Use only these values (already in the current app), centralized as CSS variables in `theme.css`:
  - `--bg: #0f0e0b`, `--surface: #1a1810`, `--surface-alt: #12110d`, `--raised: #2a2820`
  - `--gold: #c8a96e`, `--gold-deep: #8b6914`, `--cream: #f0ead6`, `--muted: #8a7d66`, `--muted-dim: #6b6452`, `--border: #2a2820`
  - gradient: `linear-gradient(135deg, #c8a96e, #8b6914)`
  - fonts: headings `'Playfair Display', serif`; body `'Source Serif 4', serif` (Georgia fallback); Google Fonts import URL: `https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Source+Serif+4:wght@300;400;600&display=swap`
- **No behavior changes.** Preserve exactly: endpoints `/api/chat`, `/api/holiday-briefing`, `/api/walk-story`, `/api/auth/signin`, `/api/user/profile`, `/api/user/visited`; the streaming parse loop; IndexedDB access via `src/db/db.js`; `NarratorService`/`useGeolocation`; `localStorage` keys `walkie_talkie_auth_v1` and `walkie_talkie_chat_by_city_v1_<user>`.
- **`CITIES` must stay in sync** with backend `config.HERO_CITIES` — copy the array verbatim, do not edit its contents.
- **Verification gate per task (adapted — this project has no test suite):** the hard gate is `npm run build` succeeding from `walkie-talkie-app/`. Baseline `npm run lint` already has 9 pre-existing errors (in `vite.config.js` and existing hooks); a task must not add *new* lint errors in the files it touches. Each task also has a manual smoke-check via `npm run dev`.
- **Touch/mobile requirements:** interactive targets ≥44px; sticky composer and tab bar respect `env(safe-area-inset-bottom)`; body must never scroll horizontally.
- All commands run from `walkie-talkie-app/`. Commit after each task.

---

## File Structure

```
walkie-talkie-app/src/
  main.jsx                 # MODIFY: import theme.css + app.css
  index.css                # MODIFY: gut Vite default template styles
  constants.js             # CREATE: CITIES, PROMPT_STRATEGIES, prompts, suggestions
  theme.css                # CREATE: CSS variable tokens, font import, base reset
  app.css                  # CREATE: all layout + component classes (mobile-first + responsive)
  App.jsx                  # MODIFY (major): slim shell — state, tab routing, sheet toggles
  components/
    TopBar.jsx             # CREATE
    TabBar.jsx             # CREATE
    GuideView.jsx          # CREATE (chat surface)
    MessageList.jsx        # CREATE
    MessageBubble.jsx      # CREATE (+ formatText)
    Composer.jsx           # CREATE
    TripView.jsx           # CREATE (trip controls + itinerary/action plan + briefing)
    WalkView.jsx           # CREATE (refactor of SpatialTrigger)
    SpatialTrigger.jsx     # DELETE at end of Task 6 (replaced by WalkView)
    sheets/
      SettingsSheet.jsx    # CREATE (eval controls + budget)
      CityHistorySheet.jsx # CREATE (city switch + chat-history-by-city)
      AuthSheet.jsx        # CREATE (sign-in)
  # unchanged: db/db.js, services/NarratorService.js, hooks/useGeolocation.js,
  #            utils/geo.js, utils/storyTemplating.js
```

Reference line numbers below refer to the **current** `src/App.jsx` and `src/components/SpatialTrigger.jsx` at branch `feat/mobile-first-frontend` base (commit with the design spec). Read those spans before moving code.

---

## Task 1: Foundation — theme tokens, base CSS, constants

Establishes the design-token layer and extracts constants so later components import from one place. The current `App.jsx` keeps working after this task (its inline `<style>` block still applies; new stylesheets only add variables + reset).

**Files:**
- Create: `src/theme.css`
- Create: `src/app.css`
- Create: `src/constants.js`
- Modify: `src/main.jsx`
- Modify: `src/index.css`

**Interfaces:**
- Produces: CSS variables (see Global Constraints) available globally; `src/constants.js` exports `CITIES` (string[]), `PROMPT_STRATEGIES` (object keyed by `regular|meta|chaining|self_reflection`, each `{label, notes}`), `SYSTEM_PROMPT` (string), `VISION_SYSTEM_PROMPT` (string), `suggestedPrompts` (`{icon, text}[]`).

- [ ] **Step 1: Create `src/theme.css`**

```css
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Source+Serif+4:wght@300;400;600&display=swap');

:root {
  --bg: #0f0e0b;
  --surface: #1a1810;
  --surface-alt: #12110d;
  --raised: #2a2820;
  --gold: #c8a96e;
  --gold-deep: #8b6914;
  --cream: #f0ead6;
  --muted: #8a7d66;
  --muted-dim: #6b6452;
  --border: #2a2820;
  --gold-gradient: linear-gradient(135deg, #c8a96e, #8b6914);
  --font-head: 'Playfair Display', serif;
  --font-body: 'Source Serif 4', 'Georgia', serif;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html, body, #root { height: 100%; }

body {
  background: var(--bg);
  color: var(--cream);
  font-family: var(--font-body);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  overflow-x: hidden;
}
```

- [ ] **Step 2: Create `src/app.css` (placeholder header; filled by later tasks)**

```css
/* Mobile-first layout + component styles. Classes are added by later tasks.
   Everything below references the tokens in theme.css. */
```

- [ ] **Step 3: Create `src/constants.js`** — move these verbatim out of `App.jsx`: `SYSTEM_PROMPT` (App.jsx:3-22), `VISION_SYSTEM_PROMPT` (App.jsx:24-29), `PROMPT_STRATEGIES` (App.jsx:31-48), `suggestedPrompts` (App.jsx:50-55), `CITIES` (App.jsx:62-73). Prefix each with `export const`. Example shape:

```js
export const SYSTEM_PROMPT = `...verbatim from App.jsx:3-22...`;
export const VISION_SYSTEM_PROMPT = `...verbatim from App.jsx:24-29...`;
export const PROMPT_STRATEGIES = { /* verbatim App.jsx:31-48 */ };
export const suggestedPrompts = [ /* verbatim App.jsx:50-55 */ ];
export const CITIES = [ /* verbatim App.jsx:62-73 — keep in sync with backend HERO_CITIES */ ];
```

- [ ] **Step 4: Update `App.jsx` to import from constants** — delete the five inlined definitions and add `import { SYSTEM_PROMPT, VISION_SYSTEM_PROMPT, PROMPT_STRATEGIES, suggestedPrompts, CITIES } from './constants';` near the top. (This keeps the current UI working, just sourcing constants externally.)

- [ ] **Step 5: Modify `src/main.jsx`** — add stylesheet imports. Ensure these two lines are present (keep existing `index.css` import or replace it):

```jsx
import './theme.css';
import './app.css';
```

- [ ] **Step 6: Gut `src/index.css`** — replace its entire contents (the Vite purple `#646cff` template defaults fight the palette) with:

```css
/* Intentionally empty. Theme lives in theme.css; app styles in app.css. */
```

- [ ] **Step 7: Build gate**

Run: `npm run build`
Expected: `✓ built` with no errors; PWA files generated.

- [ ] **Step 8: Manual smoke check**

Run: `npm run dev`, open the app. Expected: it looks essentially unchanged (dark gold theme intact), no console errors, fonts still load.

- [ ] **Step 9: Commit**

```bash
git add src/theme.css src/app.css src/constants.js src/main.jsx src/index.css src/App.jsx
git commit -m "refactor(frontend): extract theme tokens, base CSS, and constants"
```

---

## Task 2: MessageBubble component (+ formatText)

Isolates the assistant/user bubble rendering and the markdown-ish formatter so the chat view stays small.

**Files:**
- Create: `src/components/MessageBubble.jsx`
- Modify: `src/app.css` (add chat bubble + table + local-secret classes)

**Interfaces:**
- Produces: `export default function MessageBubble({ msg })` where `msg` is `{ role: 'assistant'|'user', content?, text?, preview? }`. Renders avatar + bubble; assistant content via `formatText` + `dangerouslySetInnerHTML`, user via plain `<span>`; shows `msg.preview` image when present. Returns `null` when `msg.hidden` is truthy.

- [ ] **Step 1: Create `src/components/MessageBubble.jsx`** — move `formatText` (App.jsx:537-595) verbatim into this file as a module-scope function, then render one message. Structure:

```jsx
function formatText(text) {
  /* verbatim from App.jsx:537-595 */
}

export default function MessageBubble({ msg }) {
  if (msg.hidden) return null;
  const isAI = msg.role === 'assistant';
  return (
    <div className={`message ${msg.role}`}>
      <div className={`avatar ${isAI ? 'ai' : 'user'}`}>{isAI ? '🗺️' : '✈️'}</div>
      <div className={`bubble ${isAI ? 'ai' : 'user'}`}>
        {msg.preview && <img src={msg.preview} alt="uploaded" className="img-preview" />}
        {isAI
          ? <div dangerouslySetInnerHTML={{ __html: formatText(msg.content) }} />
          : <span>{msg.text}</span>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add bubble styles to `src/app.css`** — move these rules verbatim from the App.jsx `<style>` block (App.jsx:660-699) into `app.css`, unchanged (they already use hex values; leave them or swap to `var(--…)` equivalents — values are identical): `.message`, `@keyframes fadeUp`, `.message.user`, `.avatar`, `.avatar.ai`, `.avatar.user`, `.bubble`, `.bubble.ai`, `.bubble.user`, `.local-secret`, `.md-table-wrap`, `.md-table`, `.md-table th/td`, `.img-preview`.

- [ ] **Step 3: Build gate**

Run: `npm run build`
Expected: `✓ built`, no errors. (Component is not wired yet; an unused file is fine.)

- [ ] **Step 4: Commit**

```bash
git add src/components/MessageBubble.jsx src/app.css
git commit -m "refactor(frontend): extract MessageBubble + formatText"
```

---

## Task 3: Composer component

The Guide-tab input row: growing textarea, image attach/preview, send button.

**Files:**
- Create: `src/components/Composer.jsx`
- Modify: `src/app.css` (composer classes with safe-area inset)

**Interfaces:**
- Consumes (props): `input` (string), `setInput` (fn), `onSend` (fn — call with no args), `onKeyDown` (fn), `imagePreview` (string|null), `onPickImage` (fn — opens file dialog), `onRemoveImage` (fn), `fileRef` (ref), `onFileChange` (fn), `disabled` (bool).
- Produces: `export default function Composer(props)`. No internal fetch/state beyond the textarea auto-grow handler.

- [ ] **Step 1: Create `src/components/Composer.jsx`**

```jsx
export default function Composer({
  input, setInput, onSend, onKeyDown,
  imagePreview, onPickImage, onRemoveImage, fileRef, onFileChange, disabled,
}) {
  return (
    <div className="composer">
      <div className="composer-inner">
        <div className="composer-field">
          {imagePreview && (
            <div className="img-attach-preview">
              <img src={imagePreview} alt="preview" />
              <button className="remove-img" onClick={onRemoveImage}>✕</button>
            </div>
          )}
          <div className="inner-wrap">
            <div className="attach-row">
              <button className="attach-btn" title="Upload image" onClick={onPickImage}>📷</button>
              <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={onFileChange} />
            </div>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask about a city, neighborhood, food spot, or upload a photo..."
              rows={1}
              onInput={(e) => { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px'; }}
            />
          </div>
        </div>
        <button className="send-btn" onClick={onSend} disabled={disabled}>↑</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add composer styles to `src/app.css`** — adapt from App.jsx:707-736, made mobile-sticky:

```css
.composer {
  position: sticky; bottom: 0; z-index: 5;
  background: var(--bg);
  border-top: 1px solid var(--border);
  padding: 12px 12px calc(12px + env(safe-area-inset-bottom));
}
.composer-inner { max-width: 780px; margin: 0 auto; display: flex; gap: 8px; align-items: flex-end; }
.composer-field { flex: 1; }
.img-attach-preview { position: relative; margin-bottom: 8px; }
.img-attach-preview img { width: 64px; height: 64px; object-fit: cover; border-radius: 8px; border: 1px solid #c8a96e44; }
.remove-img { position: absolute; top: -6px; right: -6px; width: 18px; height: 18px; background: var(--gold); border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 10px; color: var(--bg); font-weight: bold; border: none; }
.inner-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; transition: border-color 0.2s; }
.inner-wrap:focus-within { border-color: #c8a96e55; }
.attach-row { display: flex; gap: 4px; padding: 8px 10px 0; }
.attach-btn { background: none; border: none; color: var(--muted-dim); cursor: pointer; padding: 4px; border-radius: 6px; font-size: 18px; min-width: 44px; min-height: 44px; }
.attach-btn:hover { color: var(--gold); }
.composer textarea {
  width: 100%; background: none; border: none; outline: none;
  color: var(--cream); font-family: var(--font-body); font-size: 16px;
  padding: 8px 12px 10px; resize: none; min-height: 44px; max-height: 140px; line-height: 1.5;
}
.composer textarea::placeholder { color: #4a4438; }
.send-btn {
  width: 46px; height: 46px; border-radius: 12px; background: var(--gold-gradient);
  border: none; cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: var(--bg); font-size: 18px; transition: opacity 0.2s; flex-shrink: 0;
}
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.send-btn:hover:not(:disabled) { opacity: 0.85; }
```

(Note: `font-size: 16px` on the textarea prevents iOS auto-zoom on focus.)

- [ ] **Step 3: Build gate** — Run: `npm run build`; Expected: `✓ built`.

- [ ] **Step 4: Commit**

```bash
git add src/components/Composer.jsx src/app.css
git commit -m "refactor(frontend): extract mobile Composer"
```

---

## Task 4: Guide surface — MessageList + GuideView

The chat tab body: welcome/suggestions when empty, otherwise the message list + typing indicator. Composer is hosted by the shell (Task 9), so GuideView renders only the scrolling body.

**Files:**
- Create: `src/components/MessageList.jsx`
- Create: `src/components/GuideView.jsx`
- Modify: `src/app.css` (welcome, suggestions, typing, chat-area classes)

**Interfaces:**
- Consumes: `MessageList({ messages, loading, bottomRef })`; `GuideView({ messages, loading, bottomRef, onSuggestion })` where `onSuggestion(text)` sends a suggested prompt.
- Produces: both as default exports.

- [ ] **Step 1: Create `src/components/MessageList.jsx`**

```jsx
import MessageBubble from './MessageBubble';

export default function MessageList({ messages, loading, bottomRef }) {
  return (
    <>
      {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}
      {loading && (
        <div className="message">
          <div className="avatar ai">🗺️</div>
          <div className="bubble ai">
            <div className="typing"><div className="dot" /><div className="dot" /><div className="dot" /></div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </>
  );
}
```

- [ ] **Step 2: Create `src/components/GuideView.jsx`**

```jsx
import { suggestedPrompts } from '../constants';
import MessageList from './MessageList';

export default function GuideView({ messages, loading, bottomRef, onSuggestion }) {
  const isEmpty = messages.length === 0;
  return (
    <div className="chat-area">
      {isEmpty ? (
        <div className="welcome">
          <h1>Explore Like a Local</h1>
          <p>I know the spots that don't show up on travel blogs — the century-old tea stall, the mural with a story, the $4 meal that locals swear by.</p>
          <div className="suggestions">
            {suggestedPrompts.map((p, i) => (
              <button key={i} className="suggestion-btn" onClick={() => onSuggestion(p.text)}>
                <span className="suggestion-icon">{p.icon}</span>
                <span>{p.text}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <MessageList messages={messages} loading={loading} bottomRef={bottomRef} />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add styles to `src/app.css`** — move/adapt from App.jsx:643-705. Make `.suggestions` a single column on mobile:

```css
.chat-area { flex: 1; overflow-y: auto; padding: 20px 14px; max-width: 780px; margin: 0 auto; width: 100%; }
.welcome { text-align: center; padding: 40px 12px 24px; }
.welcome h1 { font-family: var(--font-head); font-size: 30px; color: var(--gold); margin-bottom: 8px; }
.welcome p { color: var(--muted); font-size: 15px; line-height: 1.6; max-width: 480px; margin: 0 auto 28px; }
.suggestions { display: grid; grid-template-columns: 1fr; gap: 10px; max-width: 600px; margin: 0 auto; }
.suggestion-btn { background: var(--surface); border: 1px solid var(--border); color: #c4b69a; padding: 14px; border-radius: 10px; cursor: pointer; text-align: left; font-family: var(--font-body); font-size: 14px; line-height: 1.4; transition: all 0.2s; display: flex; gap: 8px; align-items: flex-start; }
.suggestion-btn:hover { background: #22201a; border-color: #c8a96e44; color: var(--cream); }
.suggestion-icon { font-size: 18px; flex-shrink: 0; margin-top: 1px; }
.typing { display: flex; gap: 4px; align-items: center; padding: 14px 16px; }
.dot { width: 6px; height: 6px; background: var(--gold); border-radius: 50%; animation: bounce 1.2s infinite; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }
```

- [ ] **Step 4: Build gate** — Run: `npm run build`; Expected: `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add src/components/MessageList.jsx src/components/GuideView.jsx src/app.css
git commit -m "refactor(frontend): extract GuideView + MessageList chat surface"
```

---

## Task 5: TripView — trip controls + itinerary/action plan + briefing

Merges today's planning toolbar (consumer controls only) and "Holiday Mode" action plan into one Trip tab. Eval controls (model tier, prompt strategy) are NOT here — they live in the Settings sheet (Task 7).

**Files:**
- Create: `src/components/TripView.jsx`
- Modify: `src/app.css` (trip form + action-plan classes)

**Interfaces:**
- Consumes (props): `selectedCity`, `setSelectedCity`, `numDaysInput`, `setNumDaysInput`, `numDays`, `setNumDays`, `userBudget`, `setUserBudget`, `saveBudgetPreference`, `travelDates`, `setTravelDates`, `loading`, `onGenerate` (fn — the `handleGenerateItinerary` handler from the shell), `actionPlan` (array), `itineraryMap` (array|null), `holidayBriefing` (object|null), `activeSubTab`, `setActiveSubTab`, `onMarkCovered(nodeId, nodeTitle)`, `onDayCheckIn` (fn).
- Produces: `export default function TripView(props)`. Uses `formatTripDayHeading` (move verbatim from App.jsx:76-88 into this file as a module function) and `CITIES` from constants.

- [ ] **Step 1: Create `src/components/TripView.jsx`** — assemble from these current spans, converting inline styles to the classes added in Step 2:
  - City / Days / Budget / Start date controls + Generate button: adapt from App.jsx:816-896 but **drop** the Model-tier (826-835) and Prompt-strategy (837-849) blocks.
  - Action-plan header + briefing + sub-tabs + lists: from App.jsx:919-1013.
  - `formatTripDayHeading`: verbatim from App.jsx:76-88.
  - Add a "Day check-in" button that calls `props.onDayCheckIn` (logic lives in shell; see Task 9).

  Skeleton:

```jsx
import { CITIES } from '../constants';

function formatTripDayHeading(isoDateStr, dayNum) {
  /* verbatim from App.jsx:76-88 */
}

export default function TripView({
  selectedCity, setSelectedCity, numDaysInput, setNumDaysInput, numDays, setNumDays,
  userBudget, setUserBudget, saveBudgetPreference, travelDates, setTravelDates,
  loading, onGenerate, actionPlan, itineraryMap, holidayBriefing,
  activeSubTab, setActiveSubTab, onMarkCovered, onDayCheckIn,
}) {
  return (
    <div className="trip-view">
      <section className="trip-controls">
        <label className="field"><span>City</span>
          <select value={selectedCity} onChange={(e) => setSelectedCity(e.target.value)}>
            {CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="field"><span>Days</span>
          <input type="text" inputMode="numeric" pattern="[0-9]*" value={numDaysInput}
            onChange={(e) => { const v = e.target.value.replace(/[^\d]/g, ''); if (v.length <= 2) setNumDaysInput(v); }}
            onBlur={() => { const n = parseInt(numDaysInput, 10); const safe = Number.isFinite(n) ? Math.min(14, Math.max(1, n)) : 1; setNumDays(safe); setNumDaysInput(String(safe)); }} />
        </label>
        <label className="field"><span>Budget/day (USD)</span>
          <input type="number" min={0} value={userBudget} placeholder="USD"
            onChange={(e) => setUserBudget(e.target.value)} onBlur={saveBudgetPreference} />
        </label>
        <label className="field"><span>Start date</span>
          <input type="date" value={travelDates} onChange={(e) => setTravelDates(e.target.value)} style={{ colorScheme: 'dark' }} />
        </label>
        <button className="btn-primary" onClick={onGenerate} disabled={loading}>Generate itinerary</button>
      </section>

      <section className="action-plan">
        {/* header + briefing + sub-tabs + place/eat/day lists — adapt App.jsx:920-1013,
            replacing inline styles with .action-* classes; wire buttons to
            setActiveSubTab / onMarkCovered; add a Day check-in button -> onDayCheckIn */}
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Add `src/app.css` classes** — `.trip-view`, `.trip-controls`, `.field` (stacked label + control, full-width, ≥44px controls), `.btn-primary`, `.subtab-row`, `.subtab`/`.subtab.active`, `.plan-card`, `.covered-btn`, `.day-heading`, `.briefing-card`. Use tokens. Controls span full width and stack vertically (mobile-first). Example core:

```css
.trip-view { max-width: 780px; margin: 0 auto; width: 100%; padding: 16px 14px; overflow-y: auto; }
.trip-controls { display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field > span { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; font-weight: 700; }
.field select, .field input {
  width: 100%; background: var(--raised); color: var(--cream);
  border: 1px solid #c8a96e44; padding: 12px; border-radius: 10px; outline: none;
  font-size: 16px; font-family: inherit; min-height: 44px;
}
.btn-primary { background: var(--gold-deep); color: var(--bg); border: none; padding: 14px; border-radius: 12px; font-size: 15px; font-weight: bold; cursor: pointer; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.subtab-row { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.subtab { background: var(--raised); color: var(--cream); border: none; padding: 10px 16px; border-radius: 16px; font-weight: bold; cursor: pointer; min-height: 44px; }
.subtab.active { background: var(--gold-deep); color: var(--bg); }
.plan-card { background: var(--surface); border: 1px solid var(--border); padding: 16px; border-radius: 12px; margin-bottom: 12px; }
.briefing-card { background: var(--surface); border: 1px solid #c8a96e44; border-radius: 12px; padding: 16px; margin-bottom: 20px; }
.day-heading { color: var(--gold); border-bottom: 1px solid #c8a96e44; padding-bottom: 8px; font-size: 17px; margin-bottom: 6px; }
.covered-btn { background: var(--raised); color: var(--gold); border: 1px solid #c8a96e44; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: bold; min-height: 44px; }
```

- [ ] **Step 3: Build gate** — Run: `npm run build`; Expected: `✓ built`.

- [ ] **Step 4: Commit**

```bash
git add src/components/TripView.jsx src/app.css
git commit -m "refactor(frontend): extract TripView (controls + action plan + briefing)"
```

---

## Task 6: WalkView — refactor SpatialTrigger into a tab

Convert the full-screen `SpatialTrigger` overlay into an in-tab surface. **All geolocation/narration side-effect logic is preserved verbatim** — only the outer overlay chrome and inline `styles` become classes.

**Files:**
- Create: `src/components/WalkView.jsx`
- Modify: `src/app.css` (walk classes)
- Delete: `src/components/SpatialTrigger.jsx` (after WalkView builds)

**Interfaces:**
- Consumes (props): `city` (string), `areaLabel` (string|null), `llmTier` (string).
- Produces: `export default function WalkView({ city, areaLabel, llmTier })`. No `onClose` prop (it's a tab, not a modal). Keeps the same imports: `useGeolocation`, `calculateDistance`, `getNodes`/`markNodeVisited`/`resetVisited`, `narrator`, `generateIntro`.

- [ ] **Step 1: Create `src/components/WalkView.jsx`** — copy `SpatialTrigger.jsx:1-174` and adapt:
  - Rename component to `WalkView`; drop the `onClose` param and the close button (SpatialTrigger.jsx:100).
  - Keep verbatim: the `primaryArea`/`showCityLine` derivation (16-22), all `useEffect`s and handlers (`loadNodes`, `handleReset`, distance effect at 43-57, `triggerNarration` 59-90, `stopNarration` 92-95).
  - Replace `styles.overlay`/`styles.container` (the fixed full-screen modal) with a scrollable `.walk-view` container; replace remaining `styles.*` inline objects with the classes in Step 2 (keep the same visual result — same colors).
  - Remove the bottom `const styles = {…}` object (176-250) once all references are converted.

- [ ] **Step 2: Add `src/app.css` walk classes** — `.walk-view` (scrollable padded container, not fixed), `.walk-title`, `.walk-blurb`, `.walk-node-card`, `.walk-badge`, `.walk-nav-btn`, `.walk-btn`, `.walk-stop-btn`, `.walk-distance` (the big `~Nm` readout, `font-size: 36px; color: var(--gold)`), reusing the exact colors from SpatialTrigger's `styles` object.

- [ ] **Step 3: Build gate (WalkView compiles, SpatialTrigger still present)** — Run: `npm run build`; Expected: `✓ built`.

- [ ] **Step 4: Delete the old overlay**

```bash
git rm src/components/SpatialTrigger.jsx
```

- [ ] **Step 5: Build gate after delete**

Run: `npm run build`
Expected: `✓ built`. (If it fails with an unresolved import of `SpatialTrigger`, that import is removed in Task 9; for this task, confirm no file other than `App.jsx` imports it — `grep -rn SpatialTrigger src`. `App.jsx` still imports it here, so temporarily keep the file if the grep shows the App.jsx import is still live. If so, defer the `git rm` to Task 9 Step where the App.jsx import is removed, and note it.)

> Sequencing note: `App.jsx` currently imports `SpatialTrigger` (App.jsx:57) and renders it (765-772). Those references are removed in Task 9. If deleting the file now breaks the build, keep `SpatialTrigger.jsx` in place through Task 6, and perform the `git rm` as the final step of Task 9 instead.

- [ ] **Step 6: Commit**

```bash
git add src/components/WalkView.jsx src/app.css
git commit -m "refactor(frontend): WalkView tab from SpatialTrigger (logic preserved)"
```

---

## Task 7: Sheets — Settings (eval controls + budget), CityHistory, Auth

Three slide-up sheets sharing one presentational wrapper. A tiny `Sheet` primitive gives the backdrop + panel; each sheet supplies content.

**Files:**
- Create: `src/components/sheets/Sheet.jsx` (shared wrapper)
- Create: `src/components/sheets/SettingsSheet.jsx`
- Create: `src/components/sheets/CityHistorySheet.jsx`
- Create: `src/components/sheets/AuthSheet.jsx`
- Modify: `src/app.css` (sheet + backdrop classes)

**Interfaces:**
- `Sheet({ open, onClose, title, children })` — renders `null` when `!open`; otherwise a fixed backdrop + bottom-anchored panel with a title and close button; clicking the backdrop calls `onClose`.
- `SettingsSheet({ open, onClose, llmTier, setLlmTier, promptStrategy, setPromptStrategy, PROMPT_STRATEGIES, userBudget, setUserBudget, saveBudgetPreference })`.
- `CityHistorySheet({ open, onClose, chatHistoryItems, selectedCity, onSelectCity })` where `chatHistoryItems` is `{ city, count, preview }[]` and `onSelectCity(city)` also closes the sheet.
- `AuthSheet({ open, onClose, authUserId, setAuthUserId, userBudget, setUserBudget, onSignIn })` — `onSignIn` is the shell's `signIn`.

- [ ] **Step 1: Create `src/components/sheets/Sheet.jsx`**

```jsx
export default function Sheet({ open, onClose, title, children }) {
  if (!open) return null;
  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet-panel" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <h3>{title}</h3>
          <button className="sheet-close" onClick={onClose}>✕</button>
        </div>
        <div className="sheet-body">{children}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `src/components/sheets/SettingsSheet.jsx`** — model tier + prompt strategy selects (options from App.jsx:833-834 for tier; `Object.entries(PROMPT_STRATEGIES)` for strategy, as App.jsx:844-848) plus a budget field that calls `saveBudgetPreference` on blur.

```jsx
import Sheet from './Sheet';

export default function SettingsSheet({
  open, onClose, llmTier, setLlmTier, promptStrategy, setPromptStrategy,
  PROMPT_STRATEGIES, userBudget, setUserBudget, saveBudgetPreference,
}) {
  return (
    <Sheet open={open} onClose={onClose} title="Settings">
      <label className="field"><span>Model tier</span>
        <select value={llmTier} onChange={(e) => setLlmTier(e.target.value)}>
          <option value="large">Large (nvidia/nemotron-3-nano-30b-a3b:free)</option>
          <option value="small">Small (nvidia/nemotron-nano-9b-v2:free)</option>
        </select>
      </label>
      <label className="field"><span>Prompt strategy</span>
        <select value={promptStrategy} onChange={(e) => setPromptStrategy(e.target.value)}>
          {Object.entries(PROMPT_STRATEGIES).map(([value, cfg]) => (
            <option key={value} value={value}>{cfg.label}</option>
          ))}
        </select>
      </label>
      <label className="field"><span>My budget/day (USD)</span>
        <input type="number" min={0} value={userBudget}
          onChange={(e) => setUserBudget(e.target.value)} onBlur={saveBudgetPreference} placeholder="USD" />
      </label>
    </Sheet>
  );
}
```

- [ ] **Step 3: Create `src/components/sheets/CityHistorySheet.jsx`** — city switcher + the chat-history list (adapt App.jsx:900-915 markup into the sheet, keep `.history-*` classes).

```jsx
import Sheet from './Sheet';

export default function CityHistorySheet({ open, onClose, chatHistoryItems, selectedCity, onSelectCity }) {
  return (
    <Sheet open={open} onClose={onClose} title="Cities & History">
      <div className="history-list">
        {chatHistoryItems.map((item) => (
          <button key={item.city}
            className={`history-item ${item.city === selectedCity ? 'active' : ''}`}
            onClick={() => onSelectCity(item.city)}>
            <div className="history-city">{item.city}</div>
            <div className="history-meta">{item.count} message{item.count === 1 ? '' : 's'}</div>
            <div className="history-preview">{item.preview || 'No messages yet.'}</div>
          </button>
        ))}
      </div>
    </Sheet>
  );
}
```

- [ ] **Step 4: Create `src/components/sheets/AuthSheet.jsx`** — reuse the auth modal fields (App.jsx:745-757) and `onSignIn`.

```jsx
import Sheet from './Sheet';

export default function AuthSheet({ open, onClose, authUserId, setAuthUserId, userBudget, setUserBudget, onSignIn }) {
  return (
    <Sheet open={open} onClose={onClose} title="Sign in to continue">
      <p className="sheet-note">We keep your city-wise chat history, visited places, and budget for 24 hours.</p>
      <input className="sheet-input" placeholder="User ID (e.g., spartan)" value={authUserId} onChange={(e) => setAuthUserId(e.target.value)} />
      <input className="sheet-input" type="number" placeholder="Budget/day (optional)" value={userBudget} onChange={(e) => setUserBudget(e.target.value)} />
      <div className="sheet-actions">
        <button className="btn-ghost" onClick={onClose}>Later</button>
        <button className="btn-primary" onClick={onSignIn}>Sign in</button>
      </div>
    </Sheet>
  );
}
```

- [ ] **Step 5: Add sheet + history + misc classes to `src/app.css`** — `.sheet-backdrop` (`position: fixed; inset: 0; background: rgba(0,0,0,0.65); z-index: 999; display: flex; align-items: flex-end;`), `.sheet-panel` (bottom sheet: `background: var(--surface); border-top: 1px solid #c8a96e55; border-radius: 16px 16px 0 0; width: 100%; max-height: 85vh; overflow-y: auto; padding: 18px 16px calc(18px + env(safe-area-inset-bottom));`), `.sheet-head` (flex row + title in `--gold`, `font-family: var(--font-head)`), `.sheet-close`, `.sheet-body` (`display: flex; flex-direction: column; gap: 14px;`), `.sheet-note`, `.sheet-input` (full-width, ≥44px, `font-size:16px`), `.sheet-actions` (right-aligned row), `.btn-ghost`, and the `.history-list`/`.history-item`/`.history-item.active`/`.history-city`/`.history-meta`/`.history-preview` rules moved from App.jsx:632-640 (drop the `.history-pane` sidebar width; the list is full-width in the sheet).

- [ ] **Step 6: Build gate** — Run: `npm run build`; Expected: `✓ built`.

- [ ] **Step 7: Commit**

```bash
git add src/components/sheets/ src/app.css
git commit -m "refactor(frontend): add Settings, CityHistory, and Auth sheets"
```

---

## Task 8: TopBar + TabBar

The compact top app bar (logo, wordmark, city chip, gear) and the bottom tab bar (Guide / Trip / Walk).

**Files:**
- Create: `src/components/TopBar.jsx`
- Create: `src/components/TabBar.jsx`
- Modify: `src/app.css` (topbar + tabbar classes)

**Interfaces:**
- `TopBar({ selectedCity, onOpenCityHistory, onOpenSettings })`.
- `TabBar({ activeTab, setActiveTab })` where `activeTab` ∈ `'guide' | 'trip' | 'walk'`.
- Produces both as default exports.

- [ ] **Step 1: Create `src/components/TopBar.jsx`**

```jsx
export default function TopBar({ selectedCity, onOpenCityHistory, onOpenSettings }) {
  return (
    <header className="topbar">
      <div className="logo-mark">🗺️</div>
      <div className="brand-wrap">
        <div className="brand">WalkieTalkie</div>
        <div className="tagline">Local Intel · Budget Travel</div>
      </div>
      <button className="city-chip" onClick={onOpenCityHistory}>{selectedCity} ▾</button>
      <button className="icon-btn" title="Settings" onClick={onOpenSettings}>⚙️</button>
    </header>
  );
}
```

- [ ] **Step 2: Create `src/components/TabBar.jsx`**

```jsx
const TABS = [
  { id: 'guide', label: 'Guide', icon: '🗺️' },
  { id: 'trip', label: 'Trip', icon: '🧭' },
  { id: 'walk', label: 'Walk', icon: '🚶' },
];

export default function TabBar({ activeTab, setActiveTab }) {
  return (
    <nav className="tabbar">
      {TABS.map((t) => (
        <button key={t.id}
          className={`tab ${activeTab === t.id ? 'active' : ''}`}
          onClick={() => setActiveTab(t.id)}>
          <span className="tab-icon">{t.icon}</span>
          <span className="tab-label">{t.label}</span>
        </button>
      ))}
    </nav>
  );
}
```

- [ ] **Step 3: Add topbar + tabbar classes to `src/app.css`** — adapt logo/brand/tagline from App.jsx:606-621.

```css
.topbar {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-bottom: 1px solid var(--border);
  background: var(--bg); position: sticky; top: 0; z-index: 10;
  padding-top: calc(10px + env(safe-area-inset-top));
}
.logo-mark { width: 36px; height: 36px; background: var(--gold-gradient); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.brand-wrap { flex: 1; min-width: 0; }
.brand { font-family: var(--font-head); font-size: 19px; font-weight: 700; color: var(--gold); letter-spacing: -0.5px; }
.tagline { font-size: 10px; color: var(--muted-dim); text-transform: uppercase; letter-spacing: 1.5px; }
.city-chip { background: var(--raised); color: var(--cream); border: 1px solid #c8a96e44; padding: 8px 12px; border-radius: 16px; font-size: 13px; font-weight: bold; cursor: pointer; min-height: 40px; }
.icon-btn { background: none; border: none; font-size: 20px; cursor: pointer; padding: 8px; min-width: 44px; min-height: 44px; }
.tabbar {
  display: flex; border-top: 1px solid var(--border); background: var(--bg);
  position: sticky; bottom: 0; z-index: 10;
  padding-bottom: env(safe-area-inset-bottom);
}
.tab { flex: 1; background: none; border: none; color: var(--muted); cursor: pointer; padding: 10px 4px; display: flex; flex-direction: column; align-items: center; gap: 2px; min-height: 56px; }
.tab.active { color: var(--gold); }
.tab-icon { font-size: 20px; }
.tab-label { font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }
```

- [ ] **Step 4: Build gate** — Run: `npm run build`; Expected: `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add src/components/TopBar.jsx src/components/TabBar.jsx src/app.css
git commit -m "refactor(frontend): add TopBar and bottom TabBar"
```

---

## Task 9: App.jsx shell — wire everything, remove old layout

Rewrite `App.jsx` into a slim shell: keep ALL existing state and handlers, delete the old inline `<style>` block and the old JSX layout (header, toolbar, sidebar, chat/holiday area, input area, auth modal, SpatialTrigger overlay), and render `TopBar` + the active tab + `Composer` (Guide only) + `TabBar` + the three sheets.

**Files:**
- Modify: `src/App.jsx` (major)
- Modify: `src/app.css` (add `.app-shell` + `.tab-body` layout)
- Delete: `src/components/SpatialTrigger.jsx` if still present (see Task 6 note)

**Interfaces:**
- Consumes: all components/sheets from Tasks 2–8 and `PROMPT_STRATEGIES` from constants.
- Produces: the running app.

- [ ] **Step 1: Add shell layout classes to `src/app.css`**

```css
.app-shell { display: flex; flex-direction: column; height: 100dvh; overflow: hidden; }
.tab-body { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
```

- [ ] **Step 2: Keep the state + handlers, replace the render tree.** In `App.jsx`:
  - **Keep** (unchanged): all `useState` (add `const [activeTab, setActiveTab] = useState('guide')`; keep `isAuthModalOpen` renamed conceptually to the auth sheet's `open`; keep `activeTab` for sub-tabs but rename that existing one to `activeSubTab` to avoid a clash — the current `activeTab`/`setActiveTab` at App.jsx:100 becomes `activeSubTab`/`setActiveSubTab`), all `useEffect`s, `useGeolocation`, derived values (`messages`, `selectedStrategy`, `chatHistoryItems`, `walkAreaLabel`), and all handlers: `updateCurrentCityMessages`, `getPreviewText`, `signIn`, `saveBudgetPreference`, `handleGenerateItinerary`, `handleMarkCovered`, `handleImageUpload`, `sendMessage`, `handleKey`.
  - **Remove** `tripMode` and its toggle — replace usages: the old `tripMode === 'active'` effects (App.jsx:306-341) should key off `activeTab === 'trip'` instead (so the holiday briefing + node refresh fire when the Trip tab is open). Update those two `useEffect` dependency arrays from `[tripMode]`/`[tripMode, selectedCity, travelDates, numDays]` to `[activeTab]`/`[activeTab, selectedCity, travelDates, numDays]` and change the guards from `tripMode === 'active'`/`!== 'active'` to `activeTab === 'trip'`/`!== 'trip'`.
  - **Remove** the inline `<style>{…}</style>` block (App.jsx:601-737) entirely — styles now live in `app.css`.
  - **Remove** the old imports/usage of `SpatialTrigger`.
  - Add a `onDayCheckIn` handler for the Trip tab (move the inline body from App.jsx:797-800):

```jsx
const handleDayCheckIn = () => {
  const systemPromptMsg = `[SYSTEM AUTOMATION] Time jump simulation: The afternoon is passing quickly and the user still has ${actionPlan.length} places left. Proactively ask how they are doing and suggest either taking a break for a snack or picking up the pace!`;
  sendMessage(systemPromptMsg, true);
};
```

  - New return tree:

```jsx
return (
  <div className="app-shell">
    <TopBar
      selectedCity={selectedCity}
      onOpenCityHistory={() => setCityHistoryOpen(true)}
      onOpenSettings={() => setSettingsOpen(true)}
    />

    <div className="tab-body">
      {activeTab === 'guide' && (
        <>
          <GuideView
            messages={messages}
            loading={loading}
            bottomRef={bottomRef}
            onSuggestion={(text) => sendMessage(text)}
          />
          <Composer
            input={input}
            setInput={setInput}
            onSend={() => sendMessage()}
            onKeyDown={handleKey}
            imagePreview={imagePreview}
            onPickImage={() => fileRef.current?.click()}
            onRemoveImage={() => { setImage(null); setImagePreview(null); }}
            fileRef={fileRef}
            onFileChange={handleImageUpload}
            disabled={loading || (!input.trim() && !image)}
          />
        </>
      )}

      {activeTab === 'trip' && (
        <TripView
          selectedCity={selectedCity} setSelectedCity={setSelectedCity}
          numDaysInput={numDaysInput} setNumDaysInput={setNumDaysInput}
          numDays={numDays} setNumDays={setNumDays}
          userBudget={userBudget} setUserBudget={setUserBudget}
          saveBudgetPreference={saveBudgetPreference}
          travelDates={travelDates} setTravelDates={setTravelDates}
          loading={loading} onGenerate={handleGenerateItinerary}
          actionPlan={actionPlan} itineraryMap={itineraryMap}
          holidayBriefing={holidayBriefing}
          activeSubTab={activeSubTab} setActiveSubTab={setActiveSubTab}
          onMarkCovered={handleMarkCovered} onDayCheckIn={handleDayCheckIn}
        />
      )}

      {activeTab === 'walk' && (
        <WalkView city={selectedCity} areaLabel={walkAreaLabel} llmTier={llmTier} />
      )}
    </div>

    <TabBar activeTab={activeTab} setActiveTab={setActiveTab} />

    <CityHistorySheet
      open={cityHistoryOpen} onClose={() => setCityHistoryOpen(false)}
      chatHistoryItems={chatHistoryItems} selectedCity={selectedCity}
      onSelectCity={(city) => { setSelectedCity(city); setCityHistoryOpen(false); }}
    />
    <SettingsSheet
      open={settingsOpen} onClose={() => setSettingsOpen(false)}
      llmTier={llmTier} setLlmTier={setLlmTier}
      promptStrategy={promptStrategy} setPromptStrategy={setPromptStrategy}
      PROMPT_STRATEGIES={PROMPT_STRATEGIES}
      userBudget={userBudget} setUserBudget={setUserBudget}
      saveBudgetPreference={saveBudgetPreference}
    />
    <AuthSheet
      open={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)}
      authUserId={authUserId} setAuthUserId={setAuthUserId}
      userBudget={userBudget} setUserBudget={setUserBudget}
      onSignIn={async () => { const ok = await signIn(); if (ok) setIsAuthModalOpen(false); }}
    />
  </div>
);
```

  - Add the two new sheet-visibility state vars near the other `useState`s: `const [cityHistoryOpen, setCityHistoryOpen] = useState(false); const [settingsOpen, setSettingsOpen] = useState(false);`
  - Add imports at top: `TopBar`, `TabBar`, `GuideView`, `Composer`, `TripView`, `WalkView`, `SettingsSheet`, `CityHistorySheet`, `AuthSheet`, and `PROMPT_STRATEGIES` (already imported from constants in Task 1).

- [ ] **Step 3: If `SpatialTrigger.jsx` still exists, delete it**

```bash
grep -rn SpatialTrigger src || git rm src/components/SpatialTrigger.jsx
```

- [ ] **Step 4: Build gate**

Run: `npm run build`
Expected: `✓ built`, no unresolved imports.

- [ ] **Step 5: Manual smoke check (the big one)**

Run: `npm run dev`. Verify on a mobile viewport (device emulation):
  - Bottom tab bar switches Guide / Trip / Walk.
  - Guide: welcome + suggestions when empty; sending a message streams a reply; image upload works; typing dots show.
  - City chip opens City & History sheet; selecting a city switches and closes; gear opens Settings with model tier + prompt strategy + budget.
  - Trip: controls stack; Generate itinerary runs; sub-tabs (Places/Eats/Day-to-Day) and weather briefing render; ✓ Covered works; Day check-in posts a nudge.
  - Walk: stop list, distance readout, narration (grant geolocation) still function.
  - Sign-in flow: first send as guest prompts the Auth sheet; signing in persists.
  - No horizontal scroll; composer + tab bar clear the home indicator.

- [ ] **Step 6: Commit**

```bash
git add src/App.jsx src/app.css
git commit -m "refactor(frontend): mobile-first App shell with tabs and sheets"
```

---

## Task 10: Responsive scale-up (≥768px) + final polish

Add the wide-screen layout and do a final theme-parity + build pass.

**Files:**
- Modify: `src/app.css` (media query block)

**Interfaces:** none new.

- [ ] **Step 1: Append a `@media (min-width: 768px)` block to `src/app.css`** — tab bar becomes a left rail; content centers; history docks as a side rail on the Guide tab.

```css
@media (min-width: 768px) {
  .app-shell { flex-direction: row; }
  .topbar {
    position: fixed; top: 0; left: 0; right: 0;
  }
  .tabbar {
    flex-direction: column; border-top: none; border-right: 1px solid var(--border);
    width: 88px; position: sticky; top: 0; bottom: auto; height: 100dvh; padding-top: 72px;
  }
  .tab { flex: 0 0 auto; }
  .tab-body { padding-top: 56px; }
  .chat-area, .trip-view, .walk-view { max-width: 820px; }
  .suggestions { grid-template-columns: 1fr 1fr; }
  .sheet-backdrop { align-items: center; justify-content: center; }
  .sheet-panel { width: min(460px, 92vw); max-height: 80vh; border-radius: 16px; }
}
```

(On desktop the sheets center as dialogs rather than bottom sheets — matching today's centered auth modal. The city/history side-rail can be added here if desired by rendering `CityHistorySheet` content inline for ≥768px; keeping it as a centered dialog is acceptable for v1 per the spec's "responsive scale-up" intent.)

- [ ] **Step 2: Theme-parity check** — `grep -nE '#[0-9a-fA-F]{3,6}' src/app.css` and confirm every color is one of the frozen palette values (or an alpha variant like `#c8a96e44` already used today). No new hues.

- [ ] **Step 3: Build gate** — Run: `npm run build`; Expected: `✓ built`.

- [ ] **Step 4: Lint delta check** — Run: `npm run lint`; Expected: no *new* errors beyond the 9 baseline (in `vite.config.js` and pre-existing hooks). Fix any new errors introduced in the new component files.

- [ ] **Step 5: Manual check at two widths** — `npm run dev`: verify mobile (~390px) and desktop (~1280px) both look intentional; desktop shows the left rail + centered column.

- [ ] **Step 6: Commit**

```bash
git add src/app.css
git commit -m "feat(frontend): responsive scale-up for wide screens + theme parity"
```

---

## Self-Review

**Spec coverage:**
- Bottom tab bar (Guide/Trip/Walk) → Tasks 4, 5, 6, 8, 9. ✓
- Eval controls in Settings sheet → Task 7 (`SettingsSheet`). ✓
- City & History sheet → Task 7. ✓
- Auth sheet → Task 7. ✓
- Theme tokens frozen in `theme.css` → Task 1; parity check Task 10 Step 2. ✓
- Component split per spec file tree → Tasks 2–9. ✓
- `formatText` / streaming / storage / narration preserved → Tasks 2, 6, 9 (logic moved verbatim; endpoints untouched). ✓
- Responsive ≥768px scale-up → Task 10. ✓
- Composer safe-area + ≥44px targets → Tasks 3, 8, 9. ✓
- `index.css` Vite defaults replaced → Task 1. ✓

**Placeholder scan:** The two spans that say "adapt from App.jsx:NNN-NNN" (Task 5 action-plan section, Task 6 style conversion) are precise move-instructions with exact source line ranges and target class names, not vague TODOs — the source is verbatim-movable. All new code (CSS, shell wiring, components, sheets, tab bar) is written in full.

**Type/name consistency:** `activeTab` (shell tab: `'guide'|'trip'|'walk'`) is distinct from the renamed `activeSubTab` (Trip sub-tabs: `'places'|'eats'|'itinerary'`) — the current `activeTab` at App.jsx:100 is explicitly renamed in Task 9 Step 2 to avoid collision. Sheet `open`/`onClose`, `onSelectCity`, `onMarkCovered(nodeId, nodeTitle)`, `onDayCheckIn`, `onGenerate` names match between their producing task and their consumption in Task 9.

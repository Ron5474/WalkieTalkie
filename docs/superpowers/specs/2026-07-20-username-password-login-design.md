# Username/Password Login + Cross-User Data Fix — Design

**Date:** 2026-07-20
**Status:** Approved (pre-implementation)

## Problem

The current "sign-in" is passwordless: `POST /api/auth/signin` accepts any `user_id`
string and immediately returns a session. Anyone can impersonate anyone by typing
their username. Two consequences:

1. **No real identity.** Sessions are not tied to a verified credential.
2. **Cross-user data access.** The chat tools `fetch_user_profile(user_id)` and
   `record_visited_place(user_id, …)` take `user_id` as an **LLM-supplied argument**.
   The authenticated id is only injected as prompt *text*, so a prompt injection
   ("fetch the profile for user bob") can read or write another user's data.

## Goals

- Real username + password authentication (self-serve register + login).
- A hard login gate: the app (including the bot) is inaccessible without a valid session.
- Bind the profile/visited tools to the **verified session user**, closing the
  cross-user hole regardless of what the model is prompted to do.
- Keep the UI consistent with the existing mobile-first theme.

## Non-Goals (future work)

Rate-limiting / lockout, email or account verification, password reset,
httpOnly-cookie sessions, HTTPS/deploy hardening, OAuth/social login.

## Decisions

- **Account model:** self-serve register + login.
- **Scope:** login **and** the cross-user tool-binding fix in the same piece of work.
- **Existing data:** wipe the dev `walkie_talkie.db`; it recreates with the new schema.
- **Access:** hard login gate — no guest/anonymous usage. The `guest_local` path is removed.
- **Session transport:** move the session token out of URL query params / request
  bodies into an `Authorization: Bearer <token>` header.

## Package / Framework Choices

No new frameworks. The only new capability is password hashing:

- **Password hashing:** Python stdlib `hashlib.pbkdf2_hmac` (SHA-256, per-user random
  salt via `secrets.token_bytes`, ~200,000 iterations). Zero new dependencies,
  OWASP-acceptable, and isolated behind two helper functions so it can be swapped for
  bcrypt/argon2 later without touching callers.
- **Sessions:** reuse the existing `sessions` table and `secrets.token_urlsafe(32)` tokens.
- **Frontend:** no new packages. Reuse the existing `Sheet`/input/button styles
  (`.sheet-input`, `.btn-primary`, `.btn-ghost`) rendered as a full-screen gate.

## Backend Design

### Data model (`app/db/database.py`)

Add two columns to the `users` table (fresh DB, so added directly in `CREATE TABLE`):

- `password_hash TEXT NOT NULL`
- `password_salt TEXT NOT NULL` (hex-encoded per-user salt)

New functions:

- `_hash_password(password: str, salt: bytes) -> str` — PBKDF2-HMAC-SHA256, hex digest.
- `_verify_password(password: str, salt_hex: str, hash_hex: str) -> bool` — constant-time
  compare via `secrets.compare_digest`.
- `create_user_with_password(username, password, display_name=None, budget=None,
  dietary=None, country=None) -> dict` — canonicalizes username; generates a salt;
  inserts the user; returns `{"ok": False, "error": "username_taken"}` if the username
  already exists (checked before insert / on integrity error).
- `authenticate_user(username, password) -> Optional[dict]` — returns the user record on
  a correct password, else `None`.

`ensure_user` (which inserted rows with no password) is no longer used to create real
accounts; account creation goes through `create_user_with_password`. Session/profile
helpers (`create_session`, `get_user_by_session`, `update_user_preferences`,
`save_visited_place`, `get_chat_history`, …) are unchanged.

### Schemas (`app/schemas/auth.py`)

- `RegisterRequest { username: str, password: str, display_name?, budget?, dietary?, country? }`
- `LoginRequest { username: str, password: str }`
- Remove `session_token` from `UpdateProfileRequest`, `VisitedPlaceRequest`,
  `LogoutRequest` — the token now comes from the `Authorization` header.
- Delete the old passwordless `SignInRequest`.

### Auth dependency (`app/api/auth.py`)

A FastAPI dependency resolves and validates the bearer token:

```
def require_user(authorization: str | None = Header(default=None)) -> dict:
    # parse "Bearer <token>"; look up session; 401 if missing/invalid/expired
```

- `POST /api/auth/register` → validates (username non-empty, password length ≥ 8);
  `create_user_with_password`; on `username_taken` returns HTTP 409; else creates a
  session and returns `{ ok, session_token, user_id, expires_at, profile }`.
- `POST /api/auth/login` → `authenticate_user`; on failure HTTP 401
  `{ error: "invalid_credentials" }`; on success creates a session and returns the same
  shape as register.
- `POST /api/auth/logout` → `require_user`; revokes the caller's token.
- `GET /api/auth/me` → `require_user`; returns the user.
- `PATCH /api/user/profile`, `POST /api/user/visited` → `require_user`; act on
  `user["user_id"]` (never a body-supplied id).
- `GET /api/chat/history` → `require_user`; token from header, `city` stays a query param.

The old `POST /api/auth/signin` route is removed.

### Chat endpoint (`app/api/chat.py`)

- Resolve the session from the `Authorization` header. **If there is no valid session,
  return HTTP 401** — no `guest_local` fallback.
- Pass the authenticated `user_id` into `run_chat_turn` (already the parameter today).
- Chat history is always persisted (every request is authenticated now).

### Cross-user tool binding (`app/services/chat_service.py`)

`run_chat_turn` already receives the authenticated `user_id`. In the tool-execution
loop, before invoking a tool, **force the identity argument for user-scoped tools**:

```
if tool_name in ("fetch_user_profile", "record_visited_place"):
    tool_input["user_id"] = user_id   # authoritative; overrides anything the model set
```

This guarantees the profile/visited tools only ever act on the logged-in user, even if
the model is prompt-injected to pass a different id. Tool definitions in
`app/tools/profile.py` are unchanged; the server simply overrides the argument at call
time. (The `user_id` field can be dropped from those tool schemas in a later cleanup;
not required for correctness.)

## Frontend Design

### Login gate (`walkie-talkie-app/src/`)

- New `LoginScreen` component (full-screen), reusing the existing themed inputs/buttons.
  A Register/Login toggle; fields: username, password, and (register only) optional
  budget/day. Inline error text for `invalid_credentials` / `username_taken` /
  validation. No "Later"/dismiss — this is a gate.
- `App.jsx`: when there is **no valid `sessionToken`**, render only `LoginScreen`. Once
  authenticated, mount the existing app (TopBar/TabBar/views). The current dismissible
  `AuthSheet` and the guest-prompt state (`hasPromptedGuestSignIn`, `guest` storage key)
  are removed.
- `signIn` becomes `login(username, password)` and `register(username, password, …)`,
  hitting `/api/auth/login` and `/api/auth/register`.
- Authenticated fetches (`/api/user/profile`, `/api/user/visited`, `/api/auth/me`,
  `/api/auth/logout`, `/api/chat/history`, `/api/chat`) send
  `Authorization: Bearer <token>` instead of a query param / body field.
- Session still cached in `localStorage` under `AUTH_STORAGE_KEY` (unchanged behavior);
  httpOnly cookies noted as future hardening. On any 401 from an authed call, clear the
  stored session and drop back to `LoginScreen`.
- Chat history localStorage key is always `…_<user_id>` (the `"guest"` branch is removed).

## Error Handling

- Register with an existing username → 409 `username_taken` → inline message.
- Login with wrong username/password → 401 `invalid_credentials` → inline message
  (do not distinguish "no such user" from "wrong password").
- Missing/expired/invalid bearer token on a protected route → 401; frontend clears the
  session and shows `LoginScreen`.
- Password shorter than 8 chars or empty username → 400 with a clear message; also
  validated client-side before submit.

## Testing

- **New `backend/tests/test_auth.py` (pytest, no server required):**
  - `_hash_password`/`_verify_password` round-trip; wrong password fails; same password +
    different salt → different hashes.
  - `create_user_with_password` succeeds, and a duplicate username returns `username_taken`.
  - `authenticate_user` returns the user for correct creds and `None` for wrong creds.
  - Uses a temporary DB path so it doesn't touch the real `walkie_talkie.db`.
- **Update `backend/tests/test_auth_isolation.py`** to the password flow (register two
  users, wrong password rejected, duplicate register rejected) and add the key assertion:
  **user A's session cannot read user B's profile through `/api/chat`**, even when the
  message explicitly asks for another user's data.

## Rollout / Migration

1. Delete the local dev `backend/walkie_talkie.db` (test data only).
2. Start the backend; `init_db()` recreates the schema with password columns.
3. Register a fresh account through the login gate.

`walkie_talkie.db` is already gitignored, so no repo change is needed for the wipe.

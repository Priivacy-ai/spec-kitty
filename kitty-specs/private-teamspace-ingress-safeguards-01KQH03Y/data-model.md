# Data Model — CLI Private Teamspace Ingress Safeguards

**Mission**: `private-teamspace-ingress-safeguards-01KQH03Y`

This mission does not introduce new persistent data shapes. It depends on existing in-memory and on-disk types from `src/specify_cli/auth/session.py` and adds one piece of in-memory state to `TokenManager`.

---

## Existing types (referenced, not modified)

### `Team` (`src/specify_cli/auth/session.py`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Team identifier — used as `X-Team-Slug` for batch ingress and as ws-token request body |
| `name` | `str` | Display name |
| `slug` | `str` | URL-safe display slug |
| `is_private_teamspace` | `bool` | **Authoritative** field for direct-ingress eligibility |

`Team.from_dict(data)` (existing) parses the SaaS `/api/v1/me` `teams[]` entries.

### `StoredSession` (`src/specify_cli/auth/session.py`)

| Field | Type | Used by this mission |
|-------|------|---------------------|
| `email` | `str` | Negative-cache invalidation key (when this changes between `set_session` calls, cache is cleared) |
| `teams` | `list[Team]` | Read by `require_private_team_id`; rewritten by rehydrate path |
| `default_team_id` | `str` | Read for backward-compatible login/UI default; **never** used by the strict resolver |
| `access_token`, `refresh_token`, etc. | (existing) | Preserved verbatim across rehydrate (rehydrate never touches tokens) |

---

## New in-memory state

### `TokenManager._membership_negative_cache` (`src/specify_cli/auth/token_manager.py`)

| Field | Type | Lifecycle |
|-------|------|-----------|
| `_membership_negative_cache` | `bool` | `False` at construction. Set to `True` when `rehydrate_membership_if_needed` completes a `/api/v1/me` GET that returns no Private Teamspace. Cleared back to `False` when (a) `set_session(new)` is called and `new.email != prior.email`, (b) login flows finish and explicitly call `set_session`, or (c) any caller invokes `rehydrate_membership_if_needed(force=True)` and the GET succeeds with a Private Teamspace. |

The cache is **process-scoped, in-memory only**. It does not persist across CLI invocations. A user who fixes their session on the SaaS side will have it picked up on the next `spec-kitty` command without manual intervention.

---

## Rehydrate outcome (function return shape)

`TokenManager.rehydrate_membership_if_needed(*, force: bool = False) -> bool`:

| Return | Meaning | Side effects |
|--------|---------|--------------|
| `True` | Stored session now contains a Private Teamspace | `StoredSession.teams` and `StoredSession.default_team_id` may have been updated and persisted via `set_session`. Negative cache is cleared. |
| `False` | Stored session still has no Private Teamspace, or rehydrate could not run | Negative cache may have been set to `True` (when GET succeeded but returned no private team). On HTTP/parse failure, cache is **not** flipped — transient errors do not poison the next command. |

---

## Diagnostic line shape (NFR-002 contract)

Every "direct ingress skipped" log line carries these fields:

| Field | Type | Allowed values |
|-------|------|----------------|
| `category` | `str` | `"direct_ingress_missing_private_team"` (only value introduced by this mission) |
| `rehydrate_attempted` | `bool` | `False` if the call site skipped rehydrate (e.g. session is `None`); `True` if rehydrate ran |
| `ingress_sent` | `bool` | Always `False` for skip-ingress events |
| `endpoint` | `str` | One of `"/api/v1/events/batch/"` or `"/api/v1/ws-token"` |

Emitted via `logger.warning("direct ingress skipped: %s", payload, extra=payload)` so both the message string and the structured `extra` dict carry the same fields.

---

## State transitions

### Session lifecycle relative to rehydrate

```
[no session]
    │
    ▼ login
[session, may or may not have private team]
    │
    │ direct-ingress call site asks require_private_team_id(session)
    ▼
[has private team] ──── ingress proceeds ────────────► (continue)
    │ (else)
    ▼
[token_manager.rehydrate_membership_if_needed()]
    │
    ├── lock acquired, session now has private team (raced winner) ──► (continue)
    ├── negative cache hit ──────────────────────────► [skip ingress, log warning]
    ├── GET /api/v1/me, returns private team ───────► [set_session, continue]
    ├── GET /api/v1/me, returns no private team ────► [set _membership_negative_cache=True, skip ingress, log warning]
    └── GET /api/v1/me, HTTP/parse error ────────────► [skip ingress, log warning, cache untouched]
```

### Negative-cache transitions

```
[_membership_negative_cache = False]
    │
    ▼ rehydrate succeeds with no private team
[_membership_negative_cache = True]
    │
    ├── rehydrate_membership_if_needed(force=True) and GET returns private ──► [False]
    ├── set_session(new) where new.email != prior.email ─────────────────────► [False]
    └── login flow completes and calls set_session ──────────────────────────► [False]
```

---

## Tests as data contract

The contract above is enforced by tests listed in `plan.md` §1.7. The data shapes themselves remain inspectable through:

- `StoredSession.teams[*].is_private_teamspace` (read by `require_private_team_id`)
- `caplog.records[-1].extra` (asserted in skip-ingress tests)
- `respx.calls` (asserted to count exactly one `/api/v1/me` per process for shared-only sessions)

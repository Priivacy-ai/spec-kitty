# Data Model: CLI Auth Tranche 2.5 Contract Consumption

## Changed Entities

### `StoredSession` (`auth/session.py`)

Adds one optional field for forward-compatible Tranche 2 token-family lineage support.

**New field** (appended last, with default for backward-compat):

```python
generation: int | None = None
```

**Serialization changes**:

`to_dict()` — add:
```python
"generation": self.generation,
```

`from_dict()` — add:
```python
generation=data.get("generation"),  # None for pre-Tranche-2 sessions
```

**Invariants**:
- `generation` is `None` for any session stored before Tranche 2.5 ships; this is normal and must not trigger any warning or migration.
- `generation` is set only from the server's refresh response. It is never computed or incremented client-side.
- `generation` must not appear in any CLI output (it is internal diagnostic state, not user-facing identity).

---

## New Entities

### `RefreshReplayError` (`auth/errors.py`)

```python
class RefreshReplayError(TokenRefreshError):
    """Raised when the server returns 409 refresh_replay_benign_retry.

    Indicates the presented refresh token was spent within the reuse-grace
    window. The token family is NOT revoked. The caller should reload
    persisted state and retry if a newer token is available.
    """
    def __init__(self, retry_after: int = 0) -> None:
        super().__init__(
            f"Refresh token was just rotated by another process "
            f"(retry_after={retry_after}s)."
        )
        self.retry_after = retry_after
```

**Position in hierarchy**: `RefreshReplayError → TokenRefreshError → AuthenticationError`

---

### `RevokeOutcome` enum (`auth/flows/revoke.py`)

```python
class RevokeOutcome(StrEnum):
    REVOKED = "revoked"
    """Server confirmed revocation (200 + {"revoked": true})."""

    SERVER_FAILURE = "server_failure"
    """Server returned 4xx/5xx or unexpected body. NOT reported as success."""

    NETWORK_ERROR = "network_error"
    """Transport-level failure (DNS, connect, timeout)."""

    NO_REFRESH_TOKEN = "no_refresh_token"
    """No refresh token present in session; revocation could not be attempted."""
```

---

### `RevokeFlow` (`auth/flows/revoke.py`)

```python
class RevokeFlow:
    """RFC 7009-compliant token revocation for spec-kitty auth logout."""

    async def revoke(self, session: StoredSession) -> RevokeOutcome:
        """POST /oauth/revoke with the session's refresh token.

        Never raises. Returns RevokeOutcome describing the server-side
        and transport-level outcome so the caller can produce accurate
        output without re-implementing status logic.
        """
```

**Key behaviors**:
- Uses `token=session.refresh_token`, `token_type_hint=refresh_token` (form-encoded)
- Returns `NO_REFRESH_TOKEN` immediately if `session.refresh_token` is falsy
- Returns `REVOKED` only on HTTP 200 with body containing `revoked: true`
- Returns `SERVER_FAILURE` on 4xx/5xx or unexpected body
- Returns `NETWORK_ERROR` on `httpx.RequestError`
- Any other unexpected exception → `SERVER_FAILURE` + log warning
- Timeout: 10 seconds (matches existing logout timeout)

---

### `ServerSessionStatus` (`cli/commands/_auth_doctor.py`)

```python
@dataclass(frozen=True)
class ServerSessionStatus:
    """Result of an optional server-side session check (auth doctor --server)."""
    active: bool
    session_id: str | None = None  # From server response, safe to display
    error: str | None = None       # Brief human-readable failure reason; no token content
```

**Invariants**:
- `session_id` may be displayed in doctor output (it is not a secret)
- `error` must never contain raw tokens, `token_family_id`, `is_revoked`, or `revocation_reason`
- When `active=True`, `error` is `None`; when `active=False`, `session_id` may be `None`

---

## State Machine Changes

### Refresh Transaction (`refresh_transaction.py`)

The existing `RefreshOutcome` enum and the state machine in `_run_locked` gain one new handling path. No new enum values are added.

**New path** — `RefreshReplayError` catch in `_run_locked`:

```
RefreshReplayError caught
│
├── storage.read() → None
│   └── → LOCK_TIMEOUT_ERROR (session cleared concurrently)
│
├── repersisted.refresh_token == persisted.refresh_token
│   └── → LOCK_TIMEOUT_ERROR (no newer token available; caller may retry later)
│
└── repersisted.refresh_token != persisted.refresh_token  (newer token exists)
    │
    ├── refresh_flow.refresh(repersisted) → success
    │   └── storage.write(updated) → REFRESHED
    │
    └── refresh_flow.refresh(repersisted) → any error (expired, invalid, replay, timeout)
        └── → LOCK_TIMEOUT_ERROR (second attempt failed; do not loop)
```

**Token-not-resent invariant**: The retry call uses `repersisted` (which has a different `refresh_token` from `persisted`). The spent `persisted.refresh_token` is never submitted again. This is enforced structurally: the retry call is `refresh_flow.refresh(repersisted)`, not `refresh_flow.refresh(persisted)`.

### Auth Doctor State (`_auth_doctor.py`)

`doctor_impl` gains a `server` branch that runs after the local report is assembled:

```
doctor_impl called
│
├── server=False (default)
│   └── assemble_report → render → append hint line → return exit_code
│
└── server=True
    ├── assemble_report → render local sections
    ├── asyncio.run(_check_server_session())
    │   ├── get_access_token() → (triggers refresh if needed)
    │   ├── GET /api/v1/session-status
    │   │   ├── 200 → ServerSessionStatus(active=True, session_id=...)
    │   │   ├── 401 → ServerSessionStatus(active=False, error="re-authenticate")
    │   │   └── other → ServerSessionStatus(active=False, error=<brief>)
    │   └── return ServerSessionStatus
    ├── render "Server Session" section
    └── return exit_code
```

### Logout State (`_auth_logout.py`)

```
logout_impl called
│
├── session is None → "Not logged in." exit 0
│
└── session present
    ├── force=True → skip revoke
    └── force=False
        └── RevokeFlow.revoke(session)
            ├── REVOKED        → "Session revoked on server."
            ├── SERVER_FAILURE → "Server revocation not confirmed (server error)."
            ├── NETWORK_ERROR  → "Server revocation not confirmed (network error)."
            └── NO_REFRESH_TOKEN → "Server revocation could not be attempted (no refresh token)."
    │
    └── tm.clear_session()  ← unconditional regardless of revoke outcome
        └── "Local credentials deleted." → exit 0
```

The exit code is always 0 when local cleanup succeeds, regardless of revoke outcome. The revoke outcome affects only the informational output line.

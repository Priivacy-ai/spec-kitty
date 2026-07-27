# Contracts — CLI Private Teamspace Ingress Safeguards

**Mission**: `private-teamspace-ingress-safeguards-01KQH03Y`

This mission introduces no new public CLI surface, no new SaaS endpoints, and no new persisted file formats. The contracts below are internal Python module contracts that direct-ingress code paths must conform to.

---

## 1. Strict private-team resolver

**Module**: `src/specify_cli/auth/session.py`

```python
def require_private_team_id(session: StoredSession) -> str | None:
    """Return the Private Teamspace id for direct sync ingress, else None.

    Pure function. No I/O. No mutation.

    Contract:
      - If any team in session.teams has is_private_teamspace=True, return that team's id.
        When more than one team has is_private_teamspace=True (today: not expected from SaaS),
        the first is returned for determinism.
      - Otherwise, return None.
      - NEVER returns session.default_team_id (even when set).
      - NEVER returns session.teams[0].id as a fallback.
    """
```

**Use sites** (the only callers permitted):
- `src/specify_cli/sync/batch.py`
- `src/specify_cli/sync/client.py`
- `src/specify_cli/sync/queue.py`
- `src/specify_cli/sync/emitter.py`

`pick_default_team_id` and `get_private_team_id` remain available for non-ingress UI/login logic. A docstring guard added to `pick_default_team_id` states: *"Not valid as a fallback for direct sync ingress; use `require_private_team_id` paired with `TokenManager.rehydrate_membership_if_needed()` instead."*

---

## 2. Authenticated `/api/v1/me` fetch

**Module**: `src/specify_cli/auth/http/me_fetch.py` (new)

```python
def fetch_me_payload(
    saas_base_url: str,
    access_token: str,
) -> dict[str, Any]:
    """Sync GET /api/v1/me using the existing sync HTTP entry point.

    Contract:
      - Issues exactly one HTTP GET via request_with_fallback_sync(...).
      - Sends Authorization: Bearer <access_token> as an explicit header.
        Does NOT use OAuthHttpClient (would re-enter TokenManager and deadlock).
      - Raises httpx.HTTPStatusError on non-2xx (caller decides how to handle).
      - Returns the parsed JSON dict. Caller is responsible for extracting teams[].
    """
```

Reference signature for the underlying transport (already exists at
`src/specify_cli/auth/http/transport.py:377`):

```python
def request_with_fallback_sync(
    method: str,
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    client: httpx.Client | None = None,
    **kwargs: Any,
) -> httpx.Response: ...
```

This helper has **no state mutation**. It is the seam between transport and orchestration so the orchestrator (`TokenManager`) can be unit-tested without an HTTP server. It is sync so it can be called from sync direct-ingress paths (`batch.py`, `queue.py`, `emitter.py`) without any event-loop bridging.

---

## 3. Rehydrate orchestrator

**Module**: `src/specify_cli/auth/token_manager.py`

```python
class TokenManager:
    _membership_negative_cache: bool      # initialized False in __init__
    _membership_lock: threading.Lock      # initialized in __init__; SEPARATE from the existing asyncio.Lock

    def rehydrate_membership_if_needed(self, *, force: bool = False) -> bool:
        """SYNC one-shot /api/v1/me rehydrate with single-flight + negative cache.

        Returns True iff, on return, the stored session has a Private Teamspace.

        Contract:
          - Acquires self._membership_lock (threading.Lock) for the entire body.
          - Early-returns False without HTTP if self._session is None.
          - Early-returns True without HTTP if get_private_team_id(self._session.teams) is not None.
          - Early-returns False without HTTP if self._membership_negative_cache and not force.
          - Issues at most one fetch_me_payload(saas_base_url, access_token) GET per call.
          - On 2xx with a private team: builds new StoredSession preserving every existing
            field except `teams` (replaced with the fresh list) and `default_team_id` (recomputed
            via pick_default_team_id(new_teams) — the SaaS does NOT return default_team_id in
            /me, see auth/flows/authorization_code.py:239 comment). Calls self.set_session(new),
            returns True.
          - On 2xx without a private team: sets _membership_negative_cache=True, returns False.
          - On non-2xx / network / parse error: emits a warning log, leaves cache untouched,
            returns False.

        Idempotent: concurrent threads serialize on the threading.Lock; only one HTTP GET is observed.
        Sync-friendly: callable from any sync direct-ingress code path without event-loop bridging.
        """

    def refresh_if_needed(self) -> bool:
        """(EXISTING async method.) Hook addition for this mission:

        After each `self._session = result.session` adoption point (REFRESHED, ADOPTED_NEWER,
        LOCK_TIMEOUT_ADOPTED, STALE_REJECTION_PRESERVED branches inside this method), check
        whether the adopted session has a Private Teamspace. If not, call
        `self.rehydrate_membership_if_needed(force=True)` synchronously before returning.

        force=True is required because token refresh is a state-change boundary; the negative
        cache from earlier in this process must not block recovery.
        """
```

```python
class TokenManager:
    def set_session(self, session: StoredSession) -> None:
        """(Existing) Persists session via SecureStorage and updates in-memory state.

        Contract addition for this mission:
          - Unconditionally resets self._membership_negative_cache to False on every call.
          - Cost: at most one extra /api/v1/me GET on the next ingress in this process.
          - Benefit: every login / repair / identity-change boundary that flows through
            set_session is captured without conditional logic. Same-user re-login is also captured.
        """
```

---

## 4. Direct-ingress call-site contract

**Modules**: `sync/batch.py`, `sync/client.py`, `sync/queue.py`, `sync/emitter.py`

Each direct-ingress call site MUST conform to this control flow before sending an HTTP request whose target is a Private Teamspace. The helper is **sync** so it can be called from sync paths (`batch.py`, `queue.py`, `emitter.py`) directly, and from async paths (`client.py` ws-token provisioning) inline without `await`:

```python
import logging
from specify_cli.auth.session import require_private_team_id

log = logging.getLogger(__name__)


def resolve_private_team_id_for_ingress(
    token_manager,
    *,
    endpoint: str,
) -> str | None:
    """Sync helper. Returns a Private Teamspace id or None."""
    session = token_manager.get_current_session()
    team_id = session and require_private_team_id(session)
    if team_id is not None:
        return team_id

    if session is None:
        # No authenticated session at all; nothing to rehydrate from.
        _log_skip(endpoint, rehydrate_attempted=False)
        return None

    token_manager.rehydrate_membership_if_needed()
    session = token_manager.get_current_session()
    team_id = session and require_private_team_id(session)
    if team_id is not None:
        return team_id

    _log_skip(endpoint, rehydrate_attempted=True)
    return None


def _log_skip(endpoint: str, *, rehydrate_attempted: bool) -> None:
    payload = {
        "category": "direct_ingress_missing_private_team",
        "rehydrate_attempted": rehydrate_attempted,
        "ingress_sent": False,
        "endpoint": endpoint,
    }
    log.warning("direct ingress skipped: %s", payload, extra=payload)
```

A direct-ingress call site that receives `None` from this helper MUST:
1. Return without making any HTTP request to the direct-ingress endpoint.
2. Allow the originating local command (mission create, task update, etc.) to complete normally.

Each call site may live in the relevant module or use a shared helper in `src/specify_cli/sync/_team.py`. Final placement is a tasks-phase decision.

---

## 5. Stdout discipline (FR-009)

**Module**: `src/specify_cli/sync/client.py` (and only this file).

The six existing `print(...)` calls in this module — at lines 141, 146, 178, 184, 186, 193 — become `logger.warning(...)` / `logger.error(...)` / `logger.info(...)`, routing to stderr by default.

**Scope**: No `print()` is permitted in `src/specify_cli/sync/client.py`. Other sync-package modules (`diagnose.py`, `config.py`, `project_identity.py`, `batch.py`, `queue.py`, `emitter.py`) contain legitimate `print`/`console.print` calls for interactive CLI command surfaces (`spec-kitty sync diagnose`, `sync config`, etc.) that run as the user's foreground command — not as background sync during a strict-JSON agent command. Those are explicitly out of scope; widening the invariant to them would be unrelated cleanup.

Mission-scope CI-enforceable invariant:

```bash
# Should return zero matches
grep -nE '\bprint\s*\(' src/specify_cli/sync/client.py
```

A future regression (e.g. a contributor adding a `print()` to `client.py`) fails the test (`tests/sync/test_strict_json_stdout.py::test_no_print_calls_in_sync_client`).

---

## 6. Auth-refresh integration

**Module**: `src/specify_cli/auth/token_manager.py` (NOT `auth/flows/refresh.py`).

`TokenRefreshFlow.refresh(session)` only returns a fresh `StoredSession`; adoption (`self._session = result.session`) and persistence happen inside `TokenManager.refresh_if_needed()` via `run_refresh_transaction`. The hook lives there:

```python
# Inside TokenManager.refresh_if_needed(), after each `self._session = result.session` line:
self._session = result.session
if get_private_team_id(result.session.teams) is None:
    self.rehydrate_membership_if_needed(force=True)
return ...
```

This applies to all four `RefreshOutcome` branches that adopt a session (REFRESHED, ADOPTED_NEWER, LOCK_TIMEOUT_ADOPTED, STALE_REJECTION_PRESERVED).

Why `force=True`: token refresh is a state-change boundary; the negative cache from earlier in this process must not block recovery (the SaaS may have just provisioned the user's Private Teamspace).

The file `src/specify_cli/auth/flows/refresh.py` is **not modified** by this mission.

---

## 7. Test contract

The following test files MUST exist after implementation, with the cases enumerated in `plan.md` §1.7:

- `tests/auth/test_session.py` (new cases for `require_private_team_id`)
- `tests/auth/test_token_manager.py` (new cases for `rehydrate_membership_if_needed`)
- `tests/sync/test_batch_sync.py` (new cases for shared-only-session ingress paths)
- `tests/sync/test_client_integration.py` (new cases for ws-token rehydrate paths)
- `tests/auth/test_refresh_flow.py` (new cases for force-rehydrate-on-refresh)
- `tests/sync/test_strict_json_stdout.py` (new file — strict-JSON regression test)

A run with no `--json` strict regressions and no shared-team ingress requests is the acceptance contract for the mission.

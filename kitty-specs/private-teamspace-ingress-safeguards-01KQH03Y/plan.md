# Implementation Plan: CLI Private Teamspace Ingress Safeguards

**Branch**: `main` | **Date**: 2026-05-01 | **Spec**: [spec.md](./spec.md)
**Mission**: `private-teamspace-ingress-safeguards-01KQH03Y` (`01KQH03YSS4H9PQVJ5YCTGZYMR`)
**Input**: Feature specification from `kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/spec.md`
**Related Issue**: Priivacy-ai/spec-kitty-saas#142

---

## Summary

Introduce a strict private-team resolver in `src/specify_cli/auth/session.py` (`require_private_team_id(session) -> str | None`) that direct-ingress call sites use exclusively for the team identity attached to `/api/v1/events/batch/` and `/api/v1/ws-token`. Add a `TokenManager.rehydrate_membership_if_needed()` orchestrator that performs a single `/api/v1/me` GET, persists the result via `set_session()`, is single-flight via the existing `asyncio.Lock`, and caches the negative outcome for the lifetime of the process. When rehydrate still produces no Private Teamspace, ingress is skipped and the call site emits a structured stderr/log diagnostic; the originating local command (mission create, task update, status read) succeeds. Sync diagnostics that today reach stdout in `--json` mode are routed to stderr so `json.loads(stdout)` always succeeds.

---

## Technical Context

**Language/Version**: Python 3.11+
**CLI Framework**: typer (existing dependency)
**Console Output**: rich (existing dependency)
**HTTP Layer**: existing sync entry point `request_with_fallback_sync(...)` in `src/specify_cli/auth/http/transport.py:377`; reused — no new client introduced. The rehydrate path is sync because the consumers (`batch.py`, `queue.py`, `emitter.py`) are sync (`def batch_sync(...)` at `sync/batch.py:331` uses `requests`/`httpx` synchronously).
**Concurrency**: stdlib `threading.Lock` for rehydrate single-flight (separate from `TokenManager`'s existing `asyncio.Lock` for refresh — the two protect different state and different flow shapes).
**Logging**: existing `logging` module conventions; structured diagnostic lines emit a single dict via `logger.warning(...)` with named fields per NFR-002
**Storage**: existing `SecureStorage`-backed `StoredSession` (no new persistence)
**Testing**: pytest with ≥ 90% line coverage on new modules/functions; mypy --strict for all touched files
**Target Platform**: macOS / Linux (same as existing spec-kitty)
**Performance Goals**: zero added HTTP calls when the session already has a Private Teamspace (Scenario 1); at most one `/api/v1/me` GET per process when the session is shared-only (single-flight + negative cache); rehydrate completes within the existing HTTP transport's default timeout
**Constraints**: no new runtime dependencies; `pick_default_team_id` preserved unchanged; no API/contract change to non-ingress call sites; existing tests for "Private Teamspace wins even when default drifts" must still pass (NFR-004)
**Bulk-edit**: not applicable — this is new helper introduction + targeted call-site updates, not a cross-file rename

---

## Charter Check

*GATE: Must pass before implementation. Re-evaluated after Phase 1 design.*

| Charter Requirement | This Mission | Status |
|---------------------|-------------|--------|
| typer for CLI | No new CLI surface; existing typer commands unchanged | ✅ N/A |
| rich for console output | Existing usage preserved; new diagnostics use `logging` (not `rich`) so they go to stderr/structured logs, not styled console | ✅ PASS |
| ruamel.yaml for YAML | No YAML parsing in this mission | ✅ N/A |
| pytest + ≥ 90% coverage | New `require_private_team_id`, rehydrate path, and stdout-discipline guard are unit + integration tested | ✅ PASS |
| mypy --strict | New helpers fully annotated (`StoredSession -> str | None`, `Coroutine[None, None, str | None]`, etc.) | ✅ PASS |
| Integration tests for CLI commands | `test_batch_sync.py`, `test_client_integration.py`, `test_session.py`, `test_refresh_flow.py`, plus a strict-JSON regression test for `agent mission create --json` | ✅ PASS |

No violations. No complexity justification required.

---

## Phase 0: Research

**Research verdict: required for two narrow items.** See [research.md](./research.md) for full notes.

Targeted research items:

1. **Where on stdout does the `❌ Connection failed: …` line originate?** The message text comes from the SaaS error body; the `❌` prefix is added by the daemon/background sync layer. Need exact source module and write call. Determines the surface the FR-009 fix touches.
2. **Where do `Could not acquire sync lock within 5 s; skipping final sync` lines come from?** Same family — sync daemon shutdown path. Determines whether the FR-009 fix is a single chokepoint or several.
3. **Existing logging conventions for sync/auth diagnostics.** Whether to introduce a child logger or reuse an existing one; the structured-line format expected by NFR-002.

The remaining design questions (rehydrate locality, single-flight semantics, and call-site integration shape) were resolved during Plan interrogation and are recorded in this mission's `decisions/` (DM-01KQH1Y998EFVR48WNZP1FP384, DM-01KQH1YZGKKMJPJ7DGKKSKJ7XS).

---

## Phase 1: Design

### 1.1 — Component map

| Layer | Module | Change |
|-------|--------|--------|
| Pure helper | `src/specify_cli/auth/session.py` | Add `require_private_team_id(session: StoredSession) -> str | None`; tighten docstring on `pick_default_team_id` clarifying it is not valid for direct ingress |
| HTTP fetch | `src/specify_cli/auth/http/me_fetch.py` (new, ~30 LOC) | `def fetch_me_payload(saas_base_url: str, access_token: str) -> dict` — **sync**, uses `request_with_fallback_sync(...)` with explicit `Authorization: Bearer …` header. No `OAuthHttpClient` (would re-enter `TokenManager` and deadlock). |
| Orchestration | `src/specify_cli/auth/token_manager.py` | Add `def rehydrate_membership_if_needed(self, *, force: bool = False) -> bool` (**sync**) and `_membership_negative_cache: bool` field; uses a new `threading.Lock()` field for single-flight (separate from the existing `asyncio.Lock` used by `refresh_if_needed`). Also adds the post-refresh hook directly inside `refresh_if_needed()` (see "Refresh integration" row below). |
| Refresh integration | `src/specify_cli/auth/token_manager.py` (NOT `flows/refresh.py`) | After each `self._session = result.session` adoption point inside `TokenManager.refresh_if_needed()`, when the adopted session lacks a Private Teamspace, call `self.rehydrate_membership_if_needed(force=True)`. The hook lives **inside** `TokenManager` because the `flows/refresh.py` `TokenRefreshFlow.refresh(session)` only returns a fresh session — adoption (`self._session = …`) and persistence happen inside `refresh_if_needed()` via `run_refresh_transaction`. |
| Direct-ingress call site | `src/specify_cli/sync/batch.py` | Replace `session.default_team_id` lookup with `require_private_team_id(session)` after best-effort rehydrate (sync, no `await`); skip request entirely on `None` and emit structured warning |
| Direct-ingress call site | `src/specify_cli/sync/client.py` | Same change for WebSocket token provisioning |
| Direct-ingress call site | `src/specify_cli/sync/queue.py` | Same change for any team-identity metadata attached to direct-ingress |
| Direct-ingress call site | `src/specify_cli/sync/emitter.py` | Same change |
| Stdout discipline | `src/specify_cli/sync/client.py` (the only file whose `print()` calls actually leak into agent-command stdout) | Replace 6 `print()` calls in `sync/client.py:141, 146, 178, 184, 186, 193` with `logger.{warning,info,error}`. Other interactive `print`/`console.print` sites in `sync/diagnose.py`, `sync/config.py`, `sync/project_identity.py`, `sync/batch.py`, `sync/queue.py`, `sync/emitter.py` are out of scope — those are interactive CLI command surfaces, not background-during-agent-cmd surfaces. (`sync/background.py` already uses `logger.warning` correctly.) |

### 1.2 — Strict resolver contract

```python
def require_private_team_id(session: StoredSession) -> str | None:
    """Return the Private Teamspace id for direct sync ingress, else None.

    NEVER returns default_team_id when it points at a shared team.
    NEVER returns teams[0].id as a fallback.
    Pure function: no I/O, no mutation. Pair with TokenManager.rehydrate_membership_if_needed()
    to attempt recovery before falling back to "no ingress".
    """
```

### 1.3 — Rehydrate orchestrator contract

```python
class TokenManager:
    _membership_negative_cache: bool      # True ⇒ /api/v1/me already returned no private team this run
    _membership_lock: threading.Lock      # Sync single-flight (separate from the asyncio.Lock used by refresh_if_needed)

    def rehydrate_membership_if_needed(self, *, force: bool = False) -> bool:
        """Sync one-shot /api/v1/me rehydrate with single-flight + negative cache.

        Behavior:
          - Acquire self._membership_lock (threading.Lock) for the entire body.
          - If self._session is None: return False without HTTP.
          - If get_private_team_id(self._session.teams) is not None: return True without HTTP.
          - If self._membership_negative_cache and not force: return False without HTTP.
          - GET /api/v1/me via auth/http/me_fetch.fetch_me_payload(saas_base_url, access_token).
          - On 2xx with a Private Teamspace: build new StoredSession preserving every existing
            field except teams + default_team_id; recompute default_team_id via
            pick_default_team_id(new_teams). The SaaS does NOT return default_team_id in
            /api/v1/me (see auth/flows/authorization_code.py:239 comment); it must be derived
            from the fresh teams list, mirroring what auth login does. Call self.set_session(new),
            return True.
          - On 2xx with no Private Teamspace: set self._membership_negative_cache = True,
            return False.
          - On non-2xx / network / parse error: log structured warning to stderr,
            leave cache untouched, return False (transient network errors can be retried
            on the next process invocation).
        """
```

Why a separate `threading.Lock` and not the existing `asyncio.Lock`:
- Direct-ingress call sites (`batch.py`, `queue.py`, `emitter.py`) are sync — `def batch_sync(...)` at `sync/batch.py:331` uses `requests`/`httpx` synchronously. An `asyncio.Lock` cannot be acquired from a sync function without re-entering the event loop.
- The `asyncio.Lock` already on `TokenManager` protects the OAuth refresh flow (which IS async, via `run_refresh_transaction`). Refresh and rehydrate touch different state (`access_token` vs `teams`) so two locks are correct, not duplication.
- The websocket call site (`client.py`) is inside an async function but the resolver call itself is sync — the async caller simply invokes the sync helper inline. No event-loop bridging needed.

Negative-cache invalidation:
- `set_session(new_session)` clears `_membership_negative_cache` on **every** call, unconditionally. Cost: at most one extra `/api/v1/me` GET on the next ingress in this process. Benefit: every login / repair / identity-change boundary that flows through `set_session` is captured without conditional logic.
- Auth-doctor / repair paths can also call `rehydrate_membership_if_needed(force=True)` directly to bypass the cache without persisting a new session first.

Refresh-flow integration (where the hook actually lives):
- `auth/flows/refresh.py`'s `TokenRefreshFlow.refresh(session)` is **not** the adoption boundary — it only returns a fresh `StoredSession`. Adoption (`self._session = result.session`) and persistence happen inside `TokenManager.refresh_if_needed()` via `run_refresh_transaction`.
- The hook therefore lives in `TokenManager.refresh_if_needed()`, immediately after each `self._session = result.session` line (REFRESHED, ADOPTED_NEWER, LOCK_TIMEOUT_ADOPTED, STALE_REJECTION_PRESERVED branches). It is a sync call: when the adopted session lacks a Private Teamspace, call `self.rehydrate_membership_if_needed(force=True)`.
- This is why **WP02 owns the refresh hook**: WP02 owns `token_manager.py`. WP03 owns the integration tests.

### 1.4 — Call-site integration shape

Each of the four direct-ingress call sites collapses to the same five-line block. The helper and rehydrate are **sync**, so no `await` is needed — call sites can be sync (`batch.py`, `queue.py`, `emitter.py`) or async (`client.py` calling inline) without ceremony:

```python
session = token_manager.get_current_session()
team_id = session and require_private_team_id(session)
if team_id is None:
    if session is not None:
        token_manager.rehydrate_membership_if_needed()
        session = token_manager.get_current_session()
        team_id = session and require_private_team_id(session)
if team_id is None:
    log.warning(
        "direct ingress skipped",
        extra={
            "category": "direct_ingress_missing_private_team",
            "rehydrate_attempted": session is not None,
            "ingress_sent": False,
            "endpoint": <"/api/v1/events/batch/" or "/api/v1/ws-token">,
        },
    )
    return  # skip ingress; let local command succeed
# proceed with team_id as Private Teamspace id
```

This shape satisfies FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, NFR-002, and FR-010 in one place per call site, and keeps the diff per call site small.

### 1.5 — Stdout discipline (FR-009)

The two known offenders observed during the specify phase:

```
❌ Connection failed: Forbidden: Direct sync ingress must target Private Teamspace.
Could not acquire sync lock within 5 s; skipping final sync
```

Phase-0 research (R-01) located the `❌ Connection failed: …` source: six `print()` calls in `src/specify_cli/sync/client.py:141, 146, 178, 184, 186, 193`. The `Could not acquire sync lock …` line is already routed through `logger.warning` in `sync/background.py:182`.

The mission's stdout-discipline scope is therefore **`src/specify_cli/sync/client.py` only**. The 60-odd other `print`/`console.print` calls in `sync/diagnose.py`, `sync/config.py`, `sync/project_identity.py`, `sync/batch.py`, `sync/queue.py`, and `sync/emitter.py` are interactive CLI command surfaces (e.g., `spec-kitty sync diagnose` runs as the user's foreground command, not as background sync during a `--json` agent command). Touching them would expand scope without a contract reason. They are explicitly out of scope for this mission and the no-print invariant test (T024) does **not** check them.

The fix routes the 6 `client.py` prints through the existing `logging` surface (`logger.warning`/`logger.info`/`logger.error`) so they go to stderr by default. A test harness in `tests/sync/test_strict_json_stdout.py` wraps `spec-kitty agent mission create --json` end-to-end with a forced sync failure injection and asserts `json.loads(captured_stdout)` succeeds.

### 1.6 — Refresh flow integration

The hook lives **inside `TokenManager.refresh_if_needed()`**, NOT in `auth/flows/refresh.py`. Reason: `TokenRefreshFlow.refresh(session)` only returns a fresh `StoredSession`; it does not adopt or persist. Adoption (`self._session = result.session`) happens inside `refresh_if_needed()` for each `RefreshOutcome` branch (REFRESHED, ADOPTED_NEWER, LOCK_TIMEOUT_ADOPTED, STALE_REJECTION_PRESERVED). That is the only place where the just-adopted session can be checked for Private Teamspace and a forced rehydrate triggered.

After each `self._session = result.session` line in `refresh_if_needed()`:

```python
self._session = result.session
if get_private_team_id(result.session.teams) is None:
    self.rehydrate_membership_if_needed(force=True)
return ...
```

The hook uses `force=True` because token refresh is itself a state-change boundary — the negative cache from earlier in this process must not block recovery (the SaaS may have just provisioned the user's Private Teamspace at the moment refresh ran).

WP ownership: **WP02** owns the hook code (already owns `token_manager.py`). **WP03** owns the integration tests in `tests/auth/test_refresh_flow.py`. The file `auth/flows/refresh.py` is **not modified** by this mission.

### 1.7 — Test plan

| Test file | New cases |
|-----------|-----------|
| `tests/auth/test_session.py` | (a) `require_private_team_id` returns the Private Teamspace id when present; (b) returns `None` when no team has `is_private_teamspace=True`; (c) returns `None` even when `default_team_id` is set; (d) returns the Private Teamspace even when `default_team_id` points at a shared team (regression for "private wins even when default drifts"); (e) docstring assertion that `pick_default_team_id` is not valid for direct ingress |
| `tests/auth/test_token_manager.py` (new test cases) | `rehydrate_membership_if_needed` (sync): (a) early-return when session already has private; (b) sends one GET to `/api/v1/me` and persists when private team is returned, with `default_team_id` recomputed via `pick_default_team_id(new_teams)` (NOT preserved from old session); (c) sets negative cache and returns False when rehydrate response has no private team; (d) second call with negative cache set issues no HTTP; (e) `force=True` bypasses the cache; (f) concurrent threads serialize through the `threading.Lock` and only one HTTP GET is observed; (g) `set_session(new)` clears the negative cache unconditionally; (h) post-refresh hook in `refresh_if_needed()` triggers `rehydrate_membership_if_needed(force=True)` when the adopted session lacks a Private Teamspace |
| `tests/sync/test_batch_sync.py` | (a) shared-only session triggers exactly one `/api/v1/me` GET; (b) on rehydrate success, ingress is sent with private `X-Team-Slug`; (c) on rehydrate failure, no `/api/v1/events/batch/` request is sent; (d) negative cache is honored across batches in the same process |
| `tests/sync/test_client_integration.py` | WebSocket provisioning rehydrates before token resolution; never posts shared id to `/api/v1/ws-token`; on rehydrate failure, skips provisioning instead of sending shared id |
| `tests/auth/test_refresh_flow.py` | Refresh updates stale team membership when current session lacks private identity; force-rehydrate path is taken; refreshed session returned to caller has private team when SaaS makes one available |
| `tests/sync/test_strict_json_stdout.py` (new) | `spec-kitty agent mission create --json` produces strict-JSON-parseable stdout when the daemon would otherwise print `Connection failed: …` and `Could not acquire sync lock`; both messages observed on stderr; both endpoint families (batch + ws-token) failure simulation covered |

Coverage target: ≥ 90% line coverage on new code per Charter.

### 1.8 — Risk register / premortem

| Risk | Mitigation |
|------|------------|
| A non-ingress code path silently relies on `pick_default_team_id` for what is actually direct ingress | Pre-implementation grep for `default_team_id` callers (already done — 5 sites identified). Add a docstring guard on `pick_default_team_id` and a comment block in `session.py` listing legitimate vs. illegitimate uses. |
| Concurrent call sites (batch, websocket, queue, emitter) all hit `rehydrate_membership_if_needed` simultaneously and serialize on the lock, slowing healthy commands | Early-return when session already has private — healthy path takes the lock for ~µs only. |
| Negative cache stays sticky across `auth login` in a long-lived REPL/daemon process | Bust the cache in `set_session()` when session identity changes; bust on explicit `auth login` flow completion. |
| Refresh-flow rehydrate adds a second HTTP call to a hot path that previously did one | Only triggers when private team is missing OR server signals newer membership. Healthy refresh remains a single round trip. |
| Stdout discipline regression — a future `print()` slips back into the daemon | Strict-JSON test in CI (`test_strict_json_stdout.py`) executes the real `agent mission create --json` and parses with `json.loads`; any future regression fails CI. |
| Tests assume request order; concurrent rehydrate could send GET before the lock is acquired in test fixtures | Use `respx` / mocked transport with deterministic recording so the test asserts call count, not ordering. |
| `auth-doctor` or repair flows want fresh data and the negative cache hides newly-fixed sessions | `rehydrate_membership_if_needed` accepts `force=True`; document that auth-doctor/repair paths must pass it. |

### 1.9 — Bulk-edit posture

Not applicable. This mission introduces new APIs and updates explicit named call sites; it does not rename strings across many files. `change_mode` remains the default. No `occurrence_map.yaml` is produced.

### 1.10 — Out-of-scope confirmations

- Tracker-provider read paths and shared-team UI surfaces are not modified (C-001, C-002).
- `pick_default_team_id` is not renamed or removed (C-004).
- No new auth/HTTP client is introduced; the existing transport is reused (C-005).
- The companion SaaS-side change in `Priivacy-ai/spec-kitty-saas#142` is not part of this mission.

---

## Charter Check (post-design)

Re-evaluating after Phase 1:

| Requirement | Status |
|-------------|--------|
| Approach respects DIRECTIVE_003 (Decision Documentation) | ✅ Two architecture decisions captured in `decisions/` with full rationale |
| Approach respects DIRECTIVE_010 (Specification Fidelity) | ✅ Each FR/NFR maps to a named module + test; AC-001..AC-009 each have a corresponding test |
| typer / rich / ruamel / pytest / mypy contracts | ✅ Unchanged |
| 90% coverage on new code | ✅ Test plan covers all new helpers and call-site changes |

No new gate failures introduced by the design. Ready for `/spec-kitty.tasks`.

---

## Branch Contract (re-stated)

- Current branch at plan start: `main`
- Planning/base branch: `main`
- Final merge target: `main`
- `branch_matches_target`: ✓ true

---

## Artifacts produced by this command

- [plan.md](./plan.md) (this file)
- [research.md](./research.md) — Phase 0 research notes (stdout discipline source modules, logging conventions)
- [data-model.md](./data-model.md) — `StoredSession`, `Team`, `RehydrateOutcome`, negative-cache lifecycle
- [contracts/](./contracts/) — function signatures and the structured-log line shape
- [quickstart.md](./quickstart.md) — operator-facing runbook for verifying the fix locally
- `decisions/DM-01KQH1Y998EFVR48WNZP1FP384.md` — rehydrate module location
- `decisions/DM-01KQH1YZGKKMJPJ7DGKKSKJ7XS.md` — single-flight + negative cache

---

**Next**: run `/spec-kitty.tasks` to materialize work packages.

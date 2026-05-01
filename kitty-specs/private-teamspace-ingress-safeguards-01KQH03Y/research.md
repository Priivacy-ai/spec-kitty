# Phase 0 — Research Notes

**Mission**: `private-teamspace-ingress-safeguards-01KQH03Y`
**Date**: 2026-05-01

This document records the targeted research decisions taken during Phase 0. Most architecture (rehydrate locality, single-flight, negative cache) was settled in Plan interrogation and lives in `decisions/`. The remaining unknowns were narrow:

---

## R-01 — Where do the stdout-violating sync diagnostics originate?

**Decision**: Six `print()` calls in `src/specify_cli/sync/client.py` (websocket client) are the only stdout-violating sync diagnostics in the codebase today.

**Rationale**: A repository-wide grep for `Connection failed`, `skipping final sync`, and `Could not acquire sync lock` produced exactly two source modules:

- `src/specify_cli/sync/client.py` — six `print()` calls at lines 141, 146, 178, 184, 186, 193:
  ```
  print(f"❌ Token refresh failed: {exc}")
  print(f"❌ Connection failed: {exc}")
  print("✅ Connected to sync server")
  print("❌ WebSocket rejected token. Please re-authenticate.")
  print(f"❌ Connection failed: HTTP {e.response.status_code}")
  print(f"❌ Connection failed: {e}")
  ```
  These are the source of the `❌ Connection failed: Forbidden: Direct sync ingress must target Private Teamspace.` line that appeared on stdout during this mission's specify and plan phases.

- `src/specify_cli/sync/background.py:179, 182` — already using `logger.debug` / `logger.warning` correctly. These lines reach stderr through Python's default logging handler, which is acceptable per FR-009 (stderr or structured logs is the contract; only stdout is forbidden).

**Alternatives considered**:
- Searching for any sync-side `print()` more broadly: confirmed only `client.py` violates. `background.py`, `daemon.py`, `batch.py`, `emitter.py`, `queue.py` already use `logger.*` for diagnostics.
- Replacing `print()` with `rich.print` to keep the green/red coloring: rejected because `rich.print` still writes to stdout by default and would re-introduce the same bug. The fix routes these messages through `logging` (stderr) and accepts the loss of console color for sync diagnostics; users who want to see them can set log level via existing env vars.

**Implication for the plan**: FR-009 is a single-file mechanical fix in `sync/client.py` (six lines). No daemon-level rework needed.

---

## R-02 — Logging conventions for new diagnostics

**Decision**: Use a per-module `logger = logging.getLogger(__name__)` and `logger.warning(...)` for the structured "direct ingress skipped" diagnostic. Pass structured fields via the `extra=` keyword so log aggregators can pick them up; serialize the dict explicitly into the message string for human readers as well.

**Rationale**:
- `src/specify_cli/sync/background.py` already uses `logger = logging.getLogger(__name__)` with `logger.warning(...)` and `logger.debug(...)`. That is the dominant convention in the sync package. Mirroring it keeps log routing predictable.
- `extra={...}` is the stdlib's idiomatic way to attach structured fields; existing log aggregators in the codebase consume it.
- For NFR-002 ("category, rehydrate_attempted, ingress_sent must be derivable from the line"), embedding the dict in the human-readable portion of the message ensures the fields are also visible when only the message string is displayed.

**Alternatives considered**:
- `structlog` or `loguru`: rejected — neither is currently a project dependency; introducing one violates Charter ("no new runtime dependencies for this mission").
- A bespoke JSON-line log handler: rejected — overkill for the single new structured-warning shape this mission introduces.

**Implication for the plan**: New diagnostic emission shape:

```python
log = logging.getLogger(__name__)
log.warning(
    "direct ingress skipped: %s",
    {
        "category": "direct_ingress_missing_private_team",
        "rehydrate_attempted": True,
        "ingress_sent": False,
        "endpoint": "/api/v1/events/batch/",
    },
    extra={
        "category": "direct_ingress_missing_private_team",
        "rehydrate_attempted": True,
        "ingress_sent": False,
        "endpoint": "/api/v1/events/batch/",
    },
)
```

Tests assert both the category string and the dict shape via caplog.

---

## R-03 — `/api/v1/me` payload shape (already known from existing flows)

**Decision**: Reuse the existing parse path used by `auth/flows/authorization_code.py:245+` and `auth/flows/device_code.py:252+`. Both already construct a `Team` list from `me["teams"]` and read `is_private_teamspace`, `id`, `name`, `slug`, etc. The new `me_fetch.fetch_me_payload` returns the raw dict; the team list construction is delegated to a small `Team.from_dict` helper that already exists in `auth/session.py:54`.

**Rationale**: No research needed; the contract has been stable since the auth flows were introduced. We are simply lifting one HTTP call out of two flow modules into a shared helper. No schema research required.

**Implication for the plan**: `me_fetch.py` is roughly:

```python
async def fetch_me_payload(transport: HTTPTransport, access_token: str) -> dict:
    response = await transport.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    return response.json()
```

Followed by `[Team.from_dict(t) for t in payload["teams"]]` in the caller.

---

## R-04 — Concurrent rehydrate semantics (decision recorded, not researched)

Settled in Plan interrogation. See `decisions/DM-01KQH1YZGKKMJPJ7DGKKSKJ7XS.md`. Both: `asyncio.Lock` in `TokenManager` for single-flight, plus a process-lifetime negative cache invalidated by session-identity change, fresh login, or `force=True`.

---

## R-05 — Test fixture availability

**Decision**: Existing fixtures in `tests/auth/conftest.py` and `tests/sync/conftest.py` provide enough scaffolding. Specifically:

- `tests/auth/conftest.py` already has factories for `StoredSession` / `Team` and a mocked `SecureStorage`.
- `tests/sync/conftest.py` already has fixtures that build a `TokenManager` + transport pair.
- `respx` (already a project test dep) handles `/api/v1/me`, `/api/v1/events/batch/`, and `/api/v1/ws-token` mock routing.

No fixture refactor required.

**Alternatives considered**: introducing a new top-level `tests/conftest.py` fixture for a "shared-only session" — rejected as redundant; per-test factory parameterization is sufficient.

---

## Out of Scope for Research

The following items were explicitly **not researched** because they belong to the SaaS-side companion change or future missions:

- The exact field name on `/api/v1/me` that signals "newer membership generation" (R-06 was deferred — for this mission, when local `is_private_teamspace` is missing we always probe; we do not depend on a server-side hint).
- Behavior changes to non-ingress shared-team UI/tracker reads (out of scope per spec C-001, C-002).
- The SaaS-side prevention of shared-only authenticated sessions (out of scope per spec; tracked in `Priivacy-ai/spec-kitty-saas#142`).

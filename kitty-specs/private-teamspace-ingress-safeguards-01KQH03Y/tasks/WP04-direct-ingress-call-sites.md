---
work_package_id: WP04
title: Direct-Ingress Call Sites — Shared Helper, batch.py, queue.py, emitter.py
dependencies:
- WP01
- WP02
requirement_refs:
- FR-002
- FR-004
- FR-005
- FR-007
- FR-010
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-05-01T06:33:00+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
agent: "codex:gpt-5:reviewer-renata:reviewer"
shell_pid: "40593"
history:
- date: '2026-05-01'
  author: spec-kitty.tasks
  note: Initial WP generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/sync/_team.py
- src/specify_cli/sync/batch.py
- src/specify_cli/sync/queue.py
- src/specify_cli/sync/emitter.py
- tests/sync/test_batch_sync.py
- tests/sync/test_team_ingress_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load the assigned agent profile so your behavior, tone, and boundaries match what this work package expects:

```
/ad-hoc-profile-load python-pedro
```

This sets your role to `implementer`, scopes your editing surface to the `owned_files` declared in the frontmatter above, and applies the Python-specialist authoring standards. Do not skip this step.

## Objective

Introduce a single shared helper, `src/specify_cli/sync/_team.py`, that direct-ingress call sites use to derive the team id for `/api/v1/events/batch/` requests and any team-id metadata attached to ingress events. Rewrite the team-resolution logic in `sync/batch.py`, `sync/queue.py`, and `sync/emitter.py` to delegate to that helper. On rehydrate failure, every call site skips the request entirely and emits a structured warning per NFR-002. The originating local command (mission create, task update, status read) still succeeds with exit code 0.

The websocket call site (`sync/client.py`) is intentionally **not** part of this WP — it lives in WP05 along with the stdout-discipline cleanup that touches the same file.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP04 --agent <name>`; do not guess the worktree path

## Context

### Why this exists

Today, every direct-ingress call site has its own ad-hoc team-id resolution:

- `sync/batch.py:54` — iterates `session.teams`, prefers `default_team_id`, falls back implicitly.
- `sync/queue.py:209+` — uses `session.default_team_id`, then walks teams looking for `is_private_teamspace`.
- `sync/emitter.py:611` — checks `team.id == session.default_team_id`.

All three can resolve a shared team id when the session lacks a Private Teamspace, then send `X-Team-Slug: <shared-id>` to the SaaS, which rejects the request. After this WP:

- One shared helper is the only surface that resolves an ingress team id.
- Every shared-only ingress attempt issues at most one `/api/v1/me` rehydrate.
- On failure, a structured warning is logged and the HTTP request is **not** sent.
- The originating local command still completes normally (FR-010).

### Existing code surface

- `sync/batch.py:54` — current shared-team resolution.
- `sync/batch.py:394` — `headers["X-Team-Slug"] = team_slug` (the ingress send site).
- `sync/queue.py:209` — current logic.
- `sync/emitter.py:611` — current logic.
- `auth/session.require_private_team_id` — delivered in WP01.
- `TokenManager.rehydrate_membership_if_needed` — delivered in WP02.
- The structured-log shape is defined in `contracts/api.md` §4 and `data-model.md`.

### Spec references

- `kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/spec.md` — FR-002, FR-004, FR-005, FR-007, FR-010, NFR-002
- `kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/contracts/api.md` §4
- `kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/plan.md` §1.4

## Scope guardrail (binding)

This WP MUST NOT:

- Touch `sync/client.py` — that is WP05's surface.
- Modify `auth/session.py` (WP01) or `auth/token_manager.py` (WP02).
- Change non-ingress code paths in the touched files (e.g. control-plane reads, doctor commands) unless they are proven to perform direct sync ingress.
- Alter request shapes, retry logic, or backoff in `batch.py` beyond replacing the team-id resolution and the skip-on-None branch.

This WP MUST:

- Keep `mypy --strict` green for all touched files.
- Maintain ≥ 90% line coverage on new code.
- Make the structured warning shape match `contracts/api.md` §4 exactly.

## Subtasks

### T014 — Create `sync/_team.py` shared helper

**Purpose**: Single chokepoint for ingress team-id resolution + structured warning.

**Steps**:

1. Create `src/specify_cli/sync/_team.py` with:

   ```python
   """Shared direct-ingress team-id resolver. NEVER fall back to a shared team.

   This module is sync because the consumers (batch.py, queue.py, emitter.py) are sync;
   the websocket call site (client.py) is inside an async function but invokes this
   helper synchronously, no event-loop bridging needed.

   See kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/contracts/api.md §4.
   """

   from __future__ import annotations

   import logging
   from typing import Final

   from specify_cli.auth.session import require_private_team_id
   from specify_cli.auth.token_manager import TokenManager

   _LOG = logging.getLogger(__name__)

   CATEGORY_MISSING_PRIVATE_TEAM: Final[str] = "direct_ingress_missing_private_team"


   def resolve_private_team_id_for_ingress(
       token_manager: TokenManager,
       *,
       endpoint: str,
   ) -> str | None:
       """Return the Private Teamspace id for a direct-ingress request, else None. SYNC.

       Performs at most one /api/v1/me rehydrate per CLI process for shared-only sessions
       (single-flight + negative-cache enforced inside TokenManager). On a None return,
       emits a structured warning and the caller MUST NOT send the ingress request.

       Parameters
       ----------
       token_manager:
           The shared TokenManager instance.
       endpoint:
           The direct-ingress endpoint that triggered the resolution attempt.
           Recorded in the structured warning. Use exactly the path-only string
           (e.g. "/api/v1/events/batch/" or "/api/v1/ws-token").

       Returns
       -------
       str | None
           A Private Teamspace id when one is available, otherwise None.
       """
       session = token_manager.get_current_session()
       team_id = require_private_team_id(session) if session is not None else None
       if team_id is not None:
           return team_id

       rehydrate_attempted = session is not None
       if rehydrate_attempted:
           token_manager.rehydrate_membership_if_needed()  # SYNC, no await
           session = token_manager.get_current_session()
           team_id = require_private_team_id(session) if session is not None else None
           if team_id is not None:
               return team_id

       payload = {
           "category": CATEGORY_MISSING_PRIVATE_TEAM,
           "rehydrate_attempted": rehydrate_attempted,
           "ingress_sent": False,
           "endpoint": endpoint,
       }
       _LOG.warning("direct ingress skipped: %s", payload, extra=payload)
       return None
   ```

2. Note the function name is `resolve_private_team_id_for_ingress`, **sync** (no `async`/`await`). Tests assert against this exact name and shape.

**Files**:

- `src/specify_cli/sync/_team.py` (new file, ~55 LOC).

**Validation**:

- [ ] Module imports cleanly.
- [ ] `mypy --strict src/specify_cli/sync/_team.py` passes.
- [ ] No call sites have been modified yet — that is T015–T017.

---

### T015 — Update `sync/batch.py` to use the shared helper

**Purpose**: Replace the current shared-team-permitting resolution with the strict path; skip the request entirely on `None`.

**Steps**:

1. Read `src/specify_cli/sync/batch.py:30..80` to understand how the current code derives the slug variable that ends up at line 394 in `headers["X-Team-Slug"] = team_slug`.
2. Replace the current `_current_team_slug()` body (and any other ingress-team-id derivation) with a call to the sync helper. `batch_sync(...)` at line 331 is sync — no `await`:

   ```python
   from specify_cli.sync._team import resolve_private_team_id_for_ingress

   def _current_team_slug() -> str | None:
       """Resolve the ingress team slug via the strict shared helper. SYNC."""
       try:
           from specify_cli.auth import get_token_manager
           return resolve_private_team_id_for_ingress(
               get_token_manager(),
               endpoint="/api/v1/events/batch/",
           )
       except Exception:
           return None
   ```

3. In `batch_sync(...)`, when the resolved slug is `None`, skip setting `X-Team-Slug` AND skip the request entirely (do not POST to `/api/v1/events/batch/` with no slug — that violates AC-001). The structured warning has already been logged inside the helper.

   ```python
   team_slug = _current_team_slug()
   if team_slug is None:
       return BatchSyncResult(...)  # zero-event no-op result; existing dataclass shape
   headers["X-Team-Slug"] = team_slug
   # ... rest of batch_sync unchanged
   ```

4. Confirm: no remaining reference to `session.default_team_id` exists for ingress purposes in `batch.py`. (`pick_default_team_id` may still be referenced elsewhere — leave non-ingress uses alone.)

**Files**:

- `src/specify_cli/sync/batch.py` — modify the ingress resolution block only.

**Validation**:

- [ ] `grep -n "default_team_id" src/specify_cli/sync/batch.py` returns zero matches in ingress code paths.
- [ ] `mypy --strict` passes.

---

### T016 — Update `sync/queue.py` to use the shared helper

**Purpose**: Same change for the queue's ingress team metadata.

**Steps**:

1. Read `src/specify_cli/sync/queue.py:200..230` to find the current lines (200–212 region) that derive a team id from the session.
2. Replace with the same `resolve_private_team_id_for_ingress(...)` pattern.
3. If queue.py only attaches team metadata to events that are about to be ingressed, the skip-on-None path means those events are not sent. Keep the offline durability semantics (the events stay in the queue) — do not delete events on ingress skip.

**Files**:

- `src/specify_cli/sync/queue.py` — modify the ingress team-id derivation only.

**Validation**:

- [ ] `mypy --strict` passes.
- [ ] Offline queue persistence behavior unchanged on the skip path.

---

### T017 — Update `sync/emitter.py` to use the shared helper

**Purpose**: Same change for the emitter.

**Steps**:

1. Read `src/specify_cli/sync/emitter.py:600..620` (the line 611 region) to see how the team comparison is currently structured.
2. Replace any ingress-bound team-id derivation with `resolve_private_team_id_for_ingress(...)`. Skip emission of any event that requires an ingress team-id when the helper returns `None`.

**Files**:

- `src/specify_cli/sync/emitter.py` — modify the ingress team-id derivation only.

**Validation**:

- [ ] `mypy --strict` passes.
- [ ] No emitter code path other than ingress is affected.

---

### T018 — Tests in `tests/sync/test_batch_sync.py`

**Purpose**: Lock in the four AC-mapped assertions for batch.py.

**Steps**:

1. Add to `tests/sync/test_batch_sync.py`:

   ```python
   @respx.mock
   def test_batch_shared_only_session_triggers_one_me_rehydrate(token_manager_with_shared_only_session):
       """AC-002: shared-only session triggers exactly one /api/v1/me rehydrate."""
       me_route = respx.get("https://saas/api/v1/me").mock(
           return_value=httpx.Response(
               200,
               json={
                   "email": "u@example.com",
                   "teams": [{"id": "t-private", "is_private_teamspace": True}],
               },
           )
       )
       batch_route = respx.post("https://saas/api/v1/events/batch/").mock(
           return_value=httpx.Response(202)
       )

       flush_some_events(token_manager_with_shared_only_session)

       assert me_route.call_count == 1
       assert batch_route.call_count == 1
       assert batch_route.calls[0].request.headers["X-Team-Slug"] == "t-private"


   @respx.mock
   def test_batch_skips_ingress_when_rehydrate_yields_no_private(token_manager_with_shared_only_session, caplog):
       """AC-001 + AC-004: shared-only session, rehydrate returns no private => no batch POST."""
       respx.get("https://saas/api/v1/me").mock(
           return_value=httpx.Response(
               200,
               json={"email": "u@example.com", "teams": [{"id": "t-shared", "is_private_teamspace": False}]},
           )
       )
       batch_route = respx.post("https://saas/api/v1/events/batch/").mock(
           return_value=httpx.Response(202)
       )

       flush_some_events(token_manager_with_shared_only_session)

       assert batch_route.call_count == 0
       assert any(
           "direct_ingress_missing_private_team" in record.getMessage()
           for record in caplog.records
       )


   @respx.mock
   def test_batch_negative_cache_honored_across_calls(token_manager_with_shared_only_session):
       """NFR-001: at most one /api/v1/me GET per process for a shared-only session."""
       me_route = respx.get("https://saas/api/v1/me").mock(
           return_value=httpx.Response(
               200,
               json={"email": "u@example.com", "teams": [{"id": "t-shared", "is_private_teamspace": False}]},
           )
       )

       flush_some_events(token_manager_with_shared_only_session)
       flush_some_events(token_manager_with_shared_only_session)
       flush_some_events(token_manager_with_shared_only_session)

       assert me_route.call_count == 1


   @respx.mock
   def test_batch_healthy_session_no_rehydrate(token_manager_with_private_session):
       """Scenario 1 regression: session with private team => no /api/v1/me call."""
       me_route = respx.get("https://saas/api/v1/me").mock(return_value=httpx.Response(200, json={}))
       batch_route = respx.post("https://saas/api/v1/events/batch/").mock(return_value=httpx.Response(202))

       flush_some_events(token_manager_with_private_session)

       assert me_route.call_count == 0
       assert batch_route.call_count == 1
   ```

2. `flush_some_events(...)` is a sync helper that triggers the existing batch flush. Reuse the existing test helper if one exists; otherwise call `batch_sync(...)` directly with a small fixture event list. Sync, no `await`.

**Files**:

- `tests/sync/test_batch_sync.py` — add 4 test functions.

**Validation**:

- [ ] All four tests pass.
- [ ] Coverage on `batch.py`'s modified region is ≥ 90%.

---

### T019 — Tests for queue + emitter ingress paths

**Purpose**: Mirror the batch coverage for the queue and emitter call sites, using the shared helper as the unit under test so the assertions stay focused.

**Steps**:

1. Create a new test file at **`tests/sync/test_team_ingress_resolver.py`**. This is the dedicated home for queue+emitter ingress assertions; do NOT modify the existing `test_offline_queue.py`, `test_queue_resilience.py`, `test_emitter_mission_id.py`, `test_emitter_origin.py`, or `test_runtime_event_emitter.py` — they are out of scope for this WP.

2. Add four tests, two per call site (queue + emitter), each pair covering:
   - rehydrate succeeds → ingress proceeds; private team id is observable in the request the call site sends
   - rehydrate fails → no ingress request; structured warning observed via caplog

   Example shape:

   ```python
   @respx.mock
   def test_queue_ingress_rehydrates_and_sends_private(token_manager_with_shared_only_session):
       # set up /api/v1/me to return a private team
       # set up /api/v1/events/batch/ to capture
       # invoke the queue's ingress flush path (use the smallest entry point that triggers the helper)
       # assert: one /api/v1/me call, one batch call with the private X-Team-Slug


   @respx.mock
   def test_queue_ingress_skipped_on_no_private_team(token_manager_with_shared_only_session, caplog):
       # /api/v1/me returns shared-only
       # invoke the queue's ingress flush
       # assert: zero batch calls, caplog has structured warning with endpoint="/api/v1/events/batch/"


   @respx.mock
   def test_emitter_ingress_rehydrates_and_sends_private(token_manager_with_shared_only_session):
       # parallel of the queue case for the emitter ingress path


   @respx.mock
   def test_emitter_ingress_skipped_on_no_private_team(token_manager_with_shared_only_session, caplog):
       # parallel skip-path for the emitter
   ```

3. Each negative test asserts the structured warning carries `category="direct_ingress_missing_private_team"`, `rehydrate_attempted: True`, `ingress_sent: False`, and the correct `endpoint` string for that call site.

**Files**:

- `tests/sync/test_team_ingress_resolver.py` — new file with 4 test functions.

**Validation**:

- [ ] All four tests pass.
- [ ] Each negative test asserts the structured warning's `endpoint` field matches the actual ingress endpoint.
- [ ] No existing test file under `tests/sync/` was modified by this subtask (those are out of WP04's owned_files).

---

## Definition of Done

- [ ] `src/specify_cli/sync/_team.py` exists with `resolve_private_team_id_for_ingress(token_manager, *, endpoint)`.
- [ ] `batch.py`, `queue.py`, `emitter.py` use the shared helper for ingress team-id derivation; no call site references `default_team_id` for ingress.
- [ ] On `None` from the helper, each call site does **not** send the ingress request.
- [ ] Structured warning emitted exactly once per failed ingress attempt with the four required fields.
- [ ] All new tests pass; no pre-existing tests in `tests/sync/` regress.
- [ ] `mypy --strict` green for all touched files.
- [ ] `ruff check` green.
- [ ] Coverage on new code ≥ 90%.

## Risks & reviewer guidance

| Risk | Mitigation |
|------|------------|
| A non-ingress code path was relying on `default_team_id` for what was effectively ingress | Per-WP grep for `default_team_id`; preserve all non-ingress callers untouched. Reviewer should diff each modified file and confirm only ingress paths changed. |
| Skipping ingress drops events permanently | The skip path leaves events in the durable offline queue. They get drained on the next process invocation when (hopefully) the SaaS-side fix has provisioned a Private Teamspace. |
| Structured warning shape drifts between call sites | The shared helper is the single emitter; call sites do **not** emit their own warning lines. Reviewer should grep for `direct ingress skipped` and confirm exactly one source: `sync/_team.py`. |
| Concurrent batch + queue + emitter all hit the helper at once | The helper delegates to `TokenManager.rehydrate_membership_if_needed`, which has the `asyncio.Lock` (WP02). Test in WP02 (T010) already proves single-flight; no extra coordination needed here. |
| Queue/emitter changes break offline durability semantics | Tests must explicitly check that on skip-ingress, queued events are not deleted from durable storage. |

**Reviewer should verify**:

- The structured warning carries `ingress_sent: false` (lower-case bool in the dict, but JSON-serializable as `false`).
- `endpoint` strings are the path-only form (`/api/v1/events/batch/` not `https://...`).
- No `print()` was introduced anywhere in this WP; all diagnostics go through the shared helper's `logger.warning`.

---

## Implementation command (after dependencies satisfied)

```bash
spec-kitty agent action implement WP04 --agent <name>
```

This WP depends on **WP01** (`require_private_team_id`) and **WP02** (`rehydrate_membership_if_needed`).

## Activity Log

- 2026-05-01T09:58:30Z – claude:sonnet:python-pedro:implementer – shell_pid=76414 – Started implementation via action command
- 2026-05-01T10:21:45Z – claude:sonnet:python-pedro:implementer – shell_pid=76414 – Ready for review: WP04 implementation finalized by orchestrator after subagent stalled mid-validation. 29/29 sync tests pass (4 new + 25 existing); mypy --strict on _team.py green; ruff clean.
- 2026-05-01T10:22:03Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=51646 – Started review via action command
- 2026-05-01T10:26:38Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=51646 – Moved to planned
- 2026-05-01T10:29:03Z – claude:sonnet:python-pedro:implementer – shell_pid=77125 – Started implementation via action command
- 2026-05-01T10:56:40Z – claude:sonnet:python-pedro:implementer – shell_pid=77125 – Cycle 1 fix: emitter no longer falls back to 'local' on None; batch.py print removed on skip path.
- 2026-05-01T10:57:18Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=36990 – Started review via action command
- 2026-05-01T11:03:14Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=36990 – Moved to planned
- 2026-05-01T11:04:41Z – claude:sonnet:python-pedro:implementer – shell_pid=40312 – Started implementation via action command
- 2026-05-01T11:06:27Z – claude:sonnet:python-pedro:implementer – shell_pid=40312 – Cycle 2 fix: queue.py now uses get_token_manager() singleton instead of constructing fresh TokenManager per call, preserving negative cache + threading.Lock state across queue-scope reads (NFR-001 fix).
- 2026-05-01T11:06:43Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=40593 – Started review via action command
- 2026-05-01T11:11:13Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=40593 – Review passed: queue.py now uses the process-wide TokenManager singleton, direct-ingress call sites use the shared private-team resolver, skip paths avoid ingress, and targeted tests/static checks pass

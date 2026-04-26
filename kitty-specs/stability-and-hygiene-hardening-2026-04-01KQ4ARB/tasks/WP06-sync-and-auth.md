---
work_package_id: WP06
title: Sync / Offline Queue / Centralized Auth
dependencies:
- WP05
requirement_refs:
- FR-027
- FR-028
- FR-029
- FR-030
- FR-031
- NFR-007
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
- T034
- T035
- T036
- T037
- T038
agent: "claude:opus-4-7:implementer:implementer"
shell_pid: "16385"
history:
- at: 2026-04-26T07:36:00Z
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
authoritative_surface: src/specify_cli/auth/
execution_mode: code_change
mission_id: 01KQ4ARB0P4SFB0KCDMVZ6BXC8
mission_slug: stability-and-hygiene-hardening-2026-04-01KQ4ARB
owned_files:
- src/specify_cli/auth/**
- src/specify_cli/sync/queue.py
- src/specify_cli/sync/replay.py
- src/specify_cli/sync/tracker_client_glue.py
- tests/architectural/test_auth_transport_singleton.py
- tests/integration/test_offline_queue_overflow.py
- tests/integration/test_replay_tenant_collision.py
- tests/integration/test_token_refresh_dedup.py
- tests/integration/test_tracker_bidirectional_retry.py
- architecture/2.x/adr/2026-04-26-2-auth-transport-boundary.md
tags: []
---

# WP06 — Sync / Offline Queue / Centralized Auth

## Objective

A single `AuthenticatedClient` for sync / tracker / websocket clients;
deduplicated token-refresh failure logging; `OfflineQueueFull` and a
drain-to-file recovery path; deterministic replay collision handling;
bounded tracker bidirectional retries; ADR.

## Context

This WP **requires `SPEC_KITTY_ENABLE_SAAS_SYNC=1`** for any test that
exercises real SaaS / tracker / sync flows on this machine (C-002).
Decisions in `research.md` D9, D10, D11, D12.
Contract surface in
[`contracts/tracker-public-imports.md`](../contracts/tracker-public-imports.md).

WP06 depends on WP05 because the centralized auth transport sits at the
public boundary of the cross-repo package set.

## Branch strategy

- **Planning base**: WP05 tip.
- **Final merge target**: `main`.
- **Lane workspace**: assigned by `finalize-tasks`. Use
  `spec-kitty agent action implement WP06 --agent <name>`.

## Subtasks

### T032 — Centralized `AuthenticatedClient`

**Purpose**: One transport, one refresh, one log line.

**Steps**:

1. Create `src/specify_cli/auth/transport.py:AuthenticatedClient`:
   - Wraps `httpx.Client` (and an `AsyncClient` analog if needed).
   - Holds a `TokenStore` reading `.kittify/auth/credentials.json`.
   - Holds a `RefreshLock` mutex coalescing concurrent 401 → refresh
     → retry.
   - On 401: acquire lock, refresh once, retry the original request.
   - On refresh failure: raise `AuthRefreshFailed` with cause chain.
2. Migrate sync, tracker, websocket clients to use this client. Do not
   instantiate `httpx.Client` directly in those subsystems.
3. Add a process-scoped singleton accessor:
   `auth.transport.get_client() -> AuthenticatedClient`.

**Validation**:
- All affected clients route through `AuthenticatedClient`.
- Manual test: simulate a 401 with `httpx.MockTransport`; assert one
  refresh and one retry.

### T033 — Architectural test: transport singleton

**Purpose**: Pin FR-030.

**Steps**:

1. Add `tests/architectural/test_auth_transport_singleton.py`:
   - Walk `src/specify_cli/sync/`, `src/specify_cli/...tracker_client_glue.py`,
     and any websocket module under spec-kitty.
   - Use `ast` to find all `Call` nodes; assert no
     `httpx.Client(...)` / `httpx.AsyncClient(...)` invocations
     outside `src/specify_cli/auth/transport.py`.
   - The transport file is the only exception (allowlist).

**Validation**:
- Test passes.
- Reintroducing a direct `httpx.Client(...)` call in any other module
  fails the test.

### T034 — Token-refresh log dedup

**Purpose**: ≤ 1 user-facing token-refresh failure line per command
invocation.

**Steps**:

1. In `AuthenticatedClient`, add `_user_facing_failure_emitted: bool`
   that resets per process. The first refresh failure prints once;
   subsequent failures within the same invocation accumulate to a
   debug log only.
2. Add `tests/integration/test_token_refresh_dedup.py`:
   - Fixture: an `AuthenticatedClient` whose refresh always fails.
   - Issue 5 authenticated requests in a single command; assert exactly
     1 user-facing line on stderr (NFR-007).

**Validation**:
- Test passes.
- Debug logs still capture the additional failures (operators can
  enable verbose mode and see all of them).

### T035 — `OfflineQueueFull` + drain helper

**Purpose**: A full queue does not silently drop new events.

**Steps**:

1. In `src/specify_cli/sync/queue.py`, modify `OfflineQueue.append()`:
   - If appending would exceed `sync.queue_max_events` (default
     10_000), raise `OfflineQueueFull`.
2. Add `OfflineQueue.drain_to_file(path: Path) -> int` that copies all
   events to a JSONL file and clears the queue. Return event count.
3. In the CLI surface (sync / saas-sync command path), catch
   `OfflineQueueFull` and:
   - Print a single recoverable line on stderr.
   - Offer to drain to
     `.kittify/sync/overflow-<utc-iso>.jsonl` (with `--auto-drain` to
     skip prompt).
   - Exit non-zero unless drained.
4. Add `tests/integration/test_offline_queue_overflow.py`:
   - Pre-fill queue to cap.
   - Attempt one more append; assert `OfflineQueueFull` raised.
   - Trigger drain with `--auto-drain`; assert overflow file exists,
     queue is empty, and the drained file is replay-able.

**Validation**:
- Test passes.
- 0 events silently dropped under load.

### T036 — Replay tenant/project collision

**Purpose**: Deterministic replay semantics.

**Steps**:

1. In `src/specify_cli/sync/replay.py`, in the per-event apply
   function, consult `(tenant_id, project_id)`:
   - Both match local target → idempotent apply.
   - `tenant_id` mismatches → raise `TenantMismatch`, log conflict,
     skip event.
   - `tenant_id` matches, `project_id` mismatches → raise
     `ProjectMismatch`, log conflict, skip event.
2. Add `tests/integration/test_replay_tenant_collision.py`:
   - Build paired event streams covering match, tenant-mismatch, and
     project-mismatch cases.
   - Drive `replay()` and assert the exact exception type per case
     and that idempotent apply does not write twice.

**Validation**:
- Test passes.
- Logs include structured conflict records (machine-readable).

### T037 — Tracker bidirectional sync retry semantics

**Purpose**: Bounded retries, structured failure, no silent infinite
retry.

**Steps**:

1. In `src/specify_cli/sync/tracker_client_glue.py` (or wherever the
   spec-kitty side of `spec-kitty-tracker.bidirectional_sync()` is
   invoked), wrap calls in a bounded retry loop:
   - `tracker.sync_max_retries` (default 5).
   - Exponential backoff capped at
     `tracker.sync_max_backoff_seconds` (default 30).
   - Total wall-clock cap `tracker.sync_total_timeout_seconds`
     (default 300).
   - On exhausted retries, raise `TrackerSyncFailed` with structured
     cause chain (HTTP status, body excerpt up to 2 KB, retry
     history).
   - Single user-facing failure line (paired with FR-029 dedup).
2. Add `tests/integration/test_tracker_bidirectional_retry.py`:
   - Mock the tracker server to fail 3 times then succeed; assert
     success.
   - Mock to fail forever; assert `TrackerSyncFailed` after retries.

**Validation**:
- Test passes.
- Logs show structured retry history.

### T038 — ADR-2026-04-26-2: Centralized auth transport boundary

**Purpose**: Document the decision (DIRECTIVE_003).

**Steps**:

1. Create `architecture/2.x/adr/2026-04-26-2-auth-transport-boundary.md`:
   - Context: per-client auth implementations; duplicated refresh; log
     spam.
   - Decision: single `AuthenticatedClient` in
     `src/specify_cli/auth/transport.py`; architectural test pins.
   - Consequences: every new HTTP-using subsystem must adopt the
     client; the architectural test will fail-on-regression.
2. Cross-reference from `research.md` D9 and the tracker contract
   markdown.

**Validation**:
- ADR file exists, sections complete, cross-references resolve.

## Definition of Done

- All seven subtasks complete.
- `pytest tests/architectural/test_auth_transport_singleton.py` green.
- `pytest tests/integration/ -k 'offline_queue or replay_tenant or token_refresh or tracker_bidirectional'`
  green (with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`).
- ADR committed.

## Risks

- T032's migration touches several callers; missing one breaks T033's
  architectural test, which is intentional. Use the test failure to
  drive completeness.
- T034 dedup state must reset per command — module-level boolean is
  fine for short-lived CLI processes; long-running daemons would need
  per-request scoping (out of scope here).
- T035 drain file growth: many small drain files over time. Document
  in `docs/explanation/sync.md` that operators rotate manually; we do
  not auto-clean to avoid hiding evidence.
- T037 cap defaults must not be too aggressive; 300s total wall-clock
  is the operator's safety net, not their throughput target.

## Reviewer guidance

1. T032: read the `AuthenticatedClient` for the refresh-then-retry
   path. The mutex must be acquired BEFORE the refresh API call,
   released AFTER the retry completes (or fails).
2. T033: run the test against `main` to confirm it passes
   pre-migration only because no callers exist yet, then re-run after
   migration to confirm it still passes (sanity check).
3. T035: the drain file must be valid JSONL, replay-able by
   `replay()`. The integration test should re-import the drained
   events and assert they apply.
4. T036: the test must exercise both `TenantMismatch` and
   `ProjectMismatch` paths separately; do not collapse into one
   assertion.

## Activity Log

- 2026-04-26T09:12:15Z – claude:opus-4-7:implementer:implementer – shell_pid=16385 – Started implementation via action command

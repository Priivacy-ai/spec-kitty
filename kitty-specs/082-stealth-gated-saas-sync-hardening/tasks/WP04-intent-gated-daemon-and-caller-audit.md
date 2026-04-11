---
work_package_id: WP04
title: Intent-gated daemon and caller audit
dependencies:
- WP01
- WP03
requirement_refs:
- FR-005
- FR-006
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
history:
- at: '2026-04-11T06:22:58Z'
  actor: claude:/spec-kitty.tasks
  event: created
  note: Generated from data-model.md §§7–9, contracts/background_daemon_policy.md, and research R-005.
authoritative_surface: src/specify_cli/sync/daemon.py
execution_mode: code_change
feature_slug: 082-stealth-gated-saas-sync-hardening
owned_files:
- src/specify_cli/sync/daemon.py
- src/specify_cli/sync/events.py
- src/specify_cli/dashboard/server.py
- src/specify_cli/dashboard/handlers/api.py
- tests/sync/test_daemon_intent_gate.py
priority: P1
tags: []
---

# WP04 — Intent-gated daemon and caller audit

## Objective

Convert `ensure_sync_daemon_running()` from an unconditional auto-start into an **intent-gated** startup function governed by the new `DaemonIntent` enum (this WP) and the `BackgroundDaemonPolicy` config (from WP03). Audit every existing caller in the codebase and update it to pass an explicit intent. Ensure the daemon never starts from help or local-only code paths even on enabled machines (NFR-003). Ship a decision-matrix test plus a grep-based audit guard that scans the repo and fails CI if a new call site slips in without being added to the allowlist.

## Context

Today `ensure_sync_daemon_running()` is called from three code paths (research R-005 baseline map):

| File | Current behavior | Needed behavior |
|---|---|---|
| `src/specify_cli/dashboard/server.py` | Always starts the daemon when the dashboard process boots | `LOCAL_ONLY` — the dashboard reads local state; remote sync is a separate explicit action |
| `src/specify_cli/dashboard/handlers/api.py` | Starts the daemon on every API hit (including read endpoints) | `LOCAL_ONLY` for read endpoints; `REMOTE_REQUIRED` only on the explicit "sync now" endpoint |
| `src/specify_cli/sync/events.py` | Starts the daemon when an event is emitted and needs uploading | `REMOTE_REQUIRED` — events are the canonical signal that hosted sync is required |

This is exactly the set of call sites that should be touched. Any additional caller would be a bug — the audit-grep guard in T020 makes that a CI failure, not a silent regression.

The decision matrix (restated from `contracts/background_daemon_policy.md`):

| `is_saas_sync_enabled()` | `intent` | `policy` | `started` | `skipped_reason` |
|---|---|---|---|---|
| `False` | any | any | `False` | `"rollout_disabled"` |
| `True` | `LOCAL_ONLY` | any | `False` | `"intent_local_only"` |
| `True` | `REMOTE_REQUIRED` | `MANUAL` | `False` | `"policy_manual"` |
| `True` | `REMOTE_REQUIRED` | `AUTO` | `True` (on success) | `None` |
| `True` | `REMOTE_REQUIRED` | `AUTO` | `False` | `"start_failed: <reason>"` |

**Branch strategy**: Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main. Execution worktrees are allocated per computed lane from `lanes.json`; this WP depends on WP01 (rollout gate) and WP03 (BackgroundDaemonPolicy) and lives in Lane B after WP03.

## Files touched

| File | Action | Notes |
|---|---|---|
| `src/specify_cli/sync/daemon.py` | **modify** | Add `DaemonIntent`, `DaemonStartOutcome`; rewrite `ensure_sync_daemon_running()` signature and decision matrix. |
| `src/specify_cli/sync/events.py` | **modify** | Update daemon call site(s) to pass `intent=REMOTE_REQUIRED`. |
| `src/specify_cli/dashboard/server.py` | **modify** | Update daemon call site to pass `intent=LOCAL_ONLY`. |
| `src/specify_cli/dashboard/handlers/api.py` | **modify** | Update read-endpoint callers to `LOCAL_ONLY`; explicit sync-now to `REMOTE_REQUIRED`. |
| `tests/sync/test_daemon_intent_gate.py` | **create** | Decision matrix; missing-intent TypeError; audit-grep guard. |

## Subtasks

### T015 — Add `DaemonIntent` enum and `DaemonStartOutcome` dataclass

**Purpose**: Introduce the typed vocabulary for intent and the structured return type for the daemon startup function.

**Steps**:

1. Near the top of `src/specify_cli/sync/daemon.py` (alongside `DAEMON_STATE_FILE` and `DAEMON_LOCK_FILE` constants at lines 30–32), add:

   ```python
   from enum import Enum
   from dataclasses import dataclass


   class DaemonIntent(str, Enum):
       LOCAL_ONLY = "local_only"
       REMOTE_REQUIRED = "remote_required"


   @dataclass(frozen=True)
   class DaemonStartOutcome:
       started: bool
       skipped_reason: str | None
       pid: int | None
   ```

2. Export them from `sync/daemon.py`'s `__all__` (or module scope if `__all__` is not used).
3. Do not change `DAEMON_STATE_FILE`, `DAEMON_LOCK_FILE`, or `SyncDaemonStatus` at lines 55–69.

**Files**: `src/specify_cli/sync/daemon.py` (insertions, ~25 lines)

**Validation**: `python -c "from specify_cli.sync.daemon import DaemonIntent, DaemonStartOutcome"` works. mypy --strict clean.

### T016 — Refactor `ensure_sync_daemon_running()` to the decision matrix

**Purpose**: Apply the full decision matrix per `contracts/background_daemon_policy.md`.

**Steps**:

1. Change the signature of the existing `ensure_sync_daemon_running()` at `src/specify_cli/sync/daemon.py:150+` to:

   ```python
   def ensure_sync_daemon_running(
       *,
       intent: DaemonIntent,
       config: SyncConfig | None = None,
   ) -> DaemonStartOutcome:
   ```

   `intent` is **keyword-only and mandatory**. There is no default.

2. At the top of the function body, load the config if not supplied:
   ```python
   if config is None:
       config = SyncConfig.load()  # or whatever the current loader pattern is
   ```

3. Apply the decision matrix in order:
   - Rollout disabled → return `DaemonStartOutcome(started=False, skipped_reason="rollout_disabled", pid=None)`
   - `intent == LOCAL_ONLY` → return `DaemonStartOutcome(started=False, skipped_reason="intent_local_only", pid=None)`
   - `config.background_daemon == MANUAL` → return `DaemonStartOutcome(started=False, skipped_reason="policy_manual", pid=None)`
   - Otherwise → delegate to the existing start logic, returning `DaemonStartOutcome(started=True, skipped_reason=None, pid=<actual_pid>)` on success or `DaemonStartOutcome(started=False, skipped_reason=f"start_failed: {reason}", pid=None)` on failure.

4. Do **not** rewrite the inner "actually start the daemon" logic — preserve the existing PID lifecycle and state-file handling. This WP only gates the entry.

5. Any legacy positional-arg callers will now fail with TypeError. That is **intentional** — the audit pass in T017–T019 updates them.

**Files**: `src/specify_cli/sync/daemon.py` (modifications to the existing function, ~50 lines of net change)

**Validation**: T020 tests assert every matrix row. mypy --strict clean.

### T017 — Update `src/specify_cli/dashboard/server.py` caller → `LOCAL_ONLY`

**Purpose**: The dashboard process should not start the sync daemon just because it booted. Dashboard renders from the on-disk state file; remote sync is a separate, explicit action.

**Steps**:

1. Grep the file for `ensure_sync_daemon_running(` and update every call to pass `intent=DaemonIntent.LOCAL_ONLY`.
2. Confirm the dashboard's status rendering already reads from `DAEMON_STATE_FILE` (the daemon's on-disk state). If not — **stop and report back to the reviewer**; do not refactor the dashboard's data source in this mission.
3. On a `LOCAL_ONLY` outcome, the call site simply discards the `DaemonStartOutcome` or logs it at DEBUG level. It is not an error.

**Files**: `src/specify_cli/dashboard/server.py` (small modifications)

**Validation**: `spec-kitty dashboard` starts without spawning `sync-daemon` (verify manually: `ls ~/.spec-kitty/sync-daemon.lock` before and after).

### T018 — Update `src/specify_cli/dashboard/handlers/api.py` callers

**Purpose**: Read endpoints never start the daemon. Only the explicit "sync now" endpoint passes `REMOTE_REQUIRED`.

**Steps**:

1. Grep the file for `ensure_sync_daemon_running(` and classify each call site:
   - Read endpoints (anything that renders state back to the client) → `intent=DaemonIntent.LOCAL_ONLY`
   - An explicit "sync now" handler (if one exists) → `intent=DaemonIntent.REMOTE_REQUIRED`
2. If you cannot confidently classify a handler, default to `LOCAL_ONLY` and leave a `# TODO(082): classify` comment for the reviewer. Under-starting is safer than over-starting.
3. For `LOCAL_ONLY` outcomes, handlers return their state payload normally. For `REMOTE_REQUIRED` + `policy_manual` or `rollout_disabled` outcomes, the handler logs at INFO level with `skipped_reason` and returns a success response with a `"manual_mode": true` marker (or equivalent signaling) if the client cares.

**Files**: `src/specify_cli/dashboard/handlers/api.py` (modifications per call site)

**Validation**: Dashboard API read endpoints continue to return local state. The "sync now" endpoint, if present, correctly triggers the daemon on `AUTO` and reports manual-mode on `MANUAL`.

### T019 — Update `src/specify_cli/sync/events.py` caller → `REMOTE_REQUIRED`

**Purpose**: Event emission is the canonical trigger for remote sync. This is the one call site that legitimately wants the daemon up.

**Steps**:

1. Grep the file for `ensure_sync_daemon_running(` and update every call to pass `intent=DaemonIntent.REMOTE_REQUIRED`.
2. Handle each possible `DaemonStartOutcome`:
   - `started=True` → continue as today
   - `started=False, skipped_reason="rollout_disabled"` → silently swallow; events should be local-only when the gate is off. (NFR-001 fail-closed requirement.)
   - `started=False, skipped_reason="policy_manual"` → log at INFO level; events accumulate in the local queue for the next manual `spec-kitty sync run`.
   - `started=False, skipped_reason="start_failed: ..."` → preserve current error path (whatever the existing code does today).
3. Do not introduce retry loops — that is a separate concern.

**Files**: `src/specify_cli/sync/events.py` (modifications per call site)

**Validation**: Event emission still works when `AUTO`; silently skips daemon start when `MANUAL` or rollout-disabled; preserves error handling on genuine start failures.

### T020 — Tests: `tests/sync/test_daemon_intent_gate.py`

**Purpose**: Lock every row of the decision matrix plus the audit-grep guard.

**Steps**:

1. Create the new test module.
2. Decision matrix tests — one test per matrix row (5 total):
   - `rollout_disabled + any_intent + any_policy → outcome.skipped_reason == "rollout_disabled"`
   - `rollout_enabled + LOCAL_ONLY + any_policy → outcome.skipped_reason == "intent_local_only"`
   - `rollout_enabled + REMOTE_REQUIRED + MANUAL → outcome.skipped_reason == "policy_manual"`
   - `rollout_enabled + REMOTE_REQUIRED + AUTO → outcome.started == True` (use a mock that stubs the inner start logic to return a fake PID)
   - `rollout_enabled + REMOTE_REQUIRED + AUTO + inner_start_raises → outcome.started == False and skipped_reason.startswith("start_failed:")`

3. TypeError regression test:
   ```python
   def test_intent_is_mandatory_keyword_only():
       with pytest.raises(TypeError):
           ensure_sync_daemon_running()  # missing intent=
       with pytest.raises(TypeError):
           ensure_sync_daemon_running(DaemonIntent.LOCAL_ONLY)  # positional, not keyword
   ```

4. **Audit-grep guard** — the critical CI guard:

   ```python
   REPO_ROOT = Path(__file__).resolve().parents[2]  # adjust as needed
   SRC_ROOT = REPO_ROOT / "src" / "specify_cli"

   ALLOWED_CALL_SITES = {
       "src/specify_cli/dashboard/server.py",
       "src/specify_cli/dashboard/handlers/api.py",
       "src/specify_cli/sync/events.py",
       "src/specify_cli/sync/daemon.py",  # the definition itself
       "src/specify_cli/cli/commands/tracker.py",  # added by WP05
   }

   def test_no_unauthorized_daemon_call_sites():
       hits: set[str] = set()
       for path in SRC_ROOT.rglob("*.py"):
           text = path.read_text()
           if "ensure_sync_daemon_running(" in text:
               rel = str(path.relative_to(REPO_ROOT))
               hits.add(rel)
       unauthorized = hits - ALLOWED_CALL_SITES
       assert not unauthorized, (
           f"Unauthorized callers of ensure_sync_daemon_running: {unauthorized}. "
           f"Add to ALLOWED_CALL_SITES and to tasks/WP04 caller audit if this is intentional."
       )
   ```

   **Note**: This test will currently flag `src/specify_cli/cli/commands/tracker.py` if WP05 has not landed yet. That is expected — when WP05 is the lane tip, both WPs go in together and the test passes. The allowlist entry for `tracker.py` is pre-declared here so the two WPs don't have a merge ordering problem.

5. Parametrize the matrix tests over both rollout modes using the fixtures from `tests/saas/conftest.py` (`rollout_enabled`/`rollout_disabled`) — or if the `saas/` conftest is not in scope for `tests/sync/`, create a minimal local conftest that duplicates only those two fixtures.

**Files**: `tests/sync/test_daemon_intent_gate.py` (~200 lines)

**Validation**: Every matrix row tested; TypeError regression tested; audit-grep guard passes with exactly the allowlisted call sites. `pytest tests/sync/test_daemon_intent_gate.py -q` green.

## Test Strategy

Unit/integration tests cover the decision matrix (every row). The TypeError regression test prevents the mandatory-intent contract from eroding. The audit-grep guard is the defense against silent call-site proliferation — any new caller must be added to both the allowlist and the matrix tests, forcing a design conversation.

## Definition of Done

- [ ] `DaemonIntent` and `DaemonStartOutcome` defined in `sync/daemon.py` and importable.
- [ ] `ensure_sync_daemon_running()` has the new keyword-only signature and applies the decision matrix.
- [ ] All three call sites updated with explicit intent, per the caller audit table.
- [ ] `tests/sync/test_daemon_intent_gate.py` exists and passes.
- [ ] Audit-grep guard reports no unauthorized call sites (against the pre-declared allowlist).
- [ ] Full `pytest -q` green.
- [ ] `mypy --strict src/specify_cli/sync/daemon.py src/specify_cli/dashboard/ src/specify_cli/sync/events.py` clean.
- [ ] `spec-kitty dashboard` does not spawn `sync-daemon.lock` on startup (manual smoke test).
- [ ] No files outside `owned_files` modified.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Dashboard loses status data because the daemon no longer starts | Confirmed in context: dashboard should read from `DAEMON_STATE_FILE` not a live handle. If that turns out to be wrong, stop and report back; don't silently refactor. |
| Legacy caller slips through the audit | The grep guard in T020 fails CI if any unlisted module calls `ensure_sync_daemon_running(`. |
| WP05 has not landed yet when WP04 merges; grep guard flags tracker.py | Allowlist pre-declares `tracker.py`. The test still passes because the allowlist is checked against **actual** call sites found, not the other way around. |
| `SyncConfig.load()` reads user config and may fail in CI without `~/.spec-kitty/` | The decision-matrix tests should pass `config=SyncConfig(...)` explicitly, not rely on `load()`. |
| Existing callers pass positional arguments that silently get eaten | Mandatory keyword-only parameter forces TypeError — this is the intent. |

## Reviewer Guidance

- Verify every row of the decision matrix has a test and every test asserts the exact `skipped_reason` value.
- Manually smoke-test the dashboard: `spec-kitty dashboard` should not create `~/.spec-kitty/sync-daemon.lock` on boot.
- Manually smoke-test `MANUAL` mode: set `[sync].background_daemon = "manual"`, emit a sync event (if possible from a local test), verify no daemon spawns.
- Confirm the grep guard allowlist is a set (not a list) and assertion error message is actionable.
- Confirm `DaemonStartOutcome` is frozen.
- Confirm no call site passes `intent` positionally.

## Implementation command

```bash
spec-kitty agent action implement WP04 --agent <name>
```

---
work_package_id: WP07
title: Dashboard boundary regression matrix
dependencies:
- WP01
- WP03
- WP04
- WP06
requirement_refs:
- C-002
- C-003
- NFR-001
- NFR-002
- NFR-003
- NFR-005
tracker_refs: []
planning_base_branch: fix/sync-daemon-orphan-cleanup
merge_target_branch: fix/sync-daemon-orphan-cleanup
branch_strategy: Planning artifacts for this mission were generated on fix/sync-daemon-orphan-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-daemon-orphan-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
phase: Phase 4 - Regression
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "26864"
history:
- at: '2026-06-30T11:18:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/sync/test_daemon_cleanup_boundary.py
create_intent:
- tests/sync/test_daemon_cleanup_boundary.py
execution_mode: code_change
model: ''
owned_files:
- tests/sync/test_daemon_cleanup_boundary.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Dashboard boundary regression matrix

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter **before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is set, run `spec-kitty agent profile list` and pick the best match for `task_type: implement` on `authoritative_surface: tests/sync/`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks (```python`, ```bash`).

---

## Objective

Prove the sync↔dashboard **boundary** is airtight: sync cleanup never touches dashboard or third-party listeners (and vice-versa) across **all four cleanup entrypoints**, including first/last/just-outside boundary ports, and `spec-kitty dashboard` startup still uses `DaemonIntent.LOCAL_ONLY` without forcing hosted sync. This is the regression net for NFR-001/002/003 and C-002/C-003.

## Context & Constraints

Read before editing:
- [spec.md](../spec.md) NFR-001, NFR-002, NFR-003, C-002, C-003, AS-6, AS-7; [research.md](../research.md) premortem (cross-family kill).
- The four entrypoints to exercise: sync startup reaper (`reap_orphan_daemons`, `sync/owner.py:707`), auth-doctor port sweep (`sweep_orphans`, `sync/orphan_sweep.py:333`), broad `cleanup_orphan_sync_daemons` (`sync/daemon.py:1369-1411`), dashboard `_cleanup_orphaned_dashboards_in_range` (`dashboard/lifecycle.py:199-256`).
- Ranges: sync `[9400,9450)`; dashboard `[9237,9337)`. `DaemonIntent.LOCAL_ONLY` (`sync/daemon.py:181-186`); dashboard passes it at `dashboard/server.py:81-85`.
- Reuse the shared `tests/sync/_daemon_harness.py` from WP06 (`spawn_daemon`, `spawn_plain`, port helpers).

**Negative scope**: tests only — do NOT edit `src/` or the dashboard modules. Use isolated port slices and run serial.

## Branch Strategy

- **Strategy**: lane-per-WP (from `lanes.json`)
- **Planning base branch**: `fix/sync-daemon-orphan-cleanup`
- **Merge target branch**: `fix/sync-daemon-orphan-cleanup`

> Depends on WP01/WP03/WP04 (behavior) and WP06 (shared harness).

## Subtasks & Detailed Guidance

### Subtask T031 – Boundary harness setup

- **Purpose**: Stand up the three listener families for the matrix.
- **Files**: `tests/sync/test_daemon_cleanup_boundary.py` (new).
- **Steps**: Using the WP06 harness, provide fixtures that stand up: a sync daemon in `[9400,9450)`, a dashboard-shaped listener in `[9237,9337)` (a `spawn_plain` server answering `/api/health` with `project_path`+`status` so `_is_spec_kitty_dashboard` recognizes it), and a third-party listener (answers nothing recognizable). Parametrize over the four entrypoints.
- **Notes**: Keep dashboard and sync slices disjoint and away from any real dev daemon.

### Subtask T032 – Dashboard survives every sync cleanup path (C-002, NFR-002/003)

- **Files**: `tests/sync/test_daemon_cleanup_boundary.py`.
- **Steps**: For each sync entrypoint (reaper, sweep, broad cleanup), run it with a live dashboard listener present and assert the dashboard listener is **still listening** afterward (0 kills). Assert no sync cleanup ever scans/signals a port in `[9237,9337)`.
- **Notes**: This is the explicit guard WP03 added (T012) proven end-to-end.

### Subtask T033 – Sync survives dashboard cleanup; third-party survives both (NFR-003, C-004)

- **Files**: `tests/sync/test_daemon_cleanup_boundary.py`.
- **Steps**: Run `_cleanup_orphaned_dashboards_in_range` with a live sync daemon present → sync daemon survives. Run every entrypoint with a third-party listener in each range → third-party survives all (C-004: never kill on port-presence alone).
- **Notes**: Third-party = no SK self-report, no spawn signature → `never_touch`.

### Subtask T034 – Boundary ports (NFR-001/002)

- **Files**: `tests/sync/test_daemon_cleanup_boundary.py`.
- **Steps**: Exercise first/last/just-outside ports for both ranges: sync `9400` (first), `9449` (last), `9450`/`9399` (just-outside → never acted on); dashboard `9237` (first), `9336` (last), `9337`/`9236` (just-outside). Assert in-range are considered and just-outside are ignored.
- **Notes**: Just-outside ports prove the half-open interval boundaries exactly.

### Subtask T035 – Dashboard intent unchanged (AS-7, C-003)

- **Files**: `tests/sync/test_daemon_cleanup_boundary.py`.
- **Steps**: Assert that starting the dashboard path passes `DaemonIntent.LOCAL_ONLY` and does not force hosted sync (it must not auto-start the sync daemon). Patch/inspect `ensure_sync_daemon_running` to confirm the `LOCAL_ONLY` early-return is hit (`daemon.py:961`).
- **Notes**: This can be a focused unit-style assertion (no real dashboard server needed) — verify the intent argument, not a full UI boot.

## Test Strategy

- `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_daemon_cleanup_boundary.py -n0 -q` (serial, real ports).
- `.venv/bin/ruff check tests/sync/test_daemon_cleanup_boundary.py` — zero issues.

## Risks & Mitigations

- **Cross-range collision with a dev daemon**: pick slices away from defaults; the harness allocates free ports within the slice.
- **Dashboard fingerprint drift**: the dashboard listener must answer `/api/health` with `project_path`+`status` to be recognized by `_is_spec_kitty_dashboard`; otherwise it reads as third-party (still must survive sync cleanup).
- **Flakiness (NFR-006)**: serial `-n0`, `wait_until_*` polling, teardown escalation.

## Review Guidance

- Verify all **four** entrypoints are exercised (reaper, auth-doctor sweep, broad cleanup, dashboard cleanup).
- Verify dashboard + third-party survive 100% of sync cleanups, sync + third-party survive dashboard cleanup (0 wrongful kills).
- Verify first/last/just-outside boundary ports for **both** ranges.
- Verify the `DaemonIntent.LOCAL_ONLY` assertion (C-003).

## Activity Log

- 2026-06-30T11:18:31Z – system – Prompt created.
- 2026-06-30T13:41:40Z – claude:sonnet:python-pedro:implementer – shell_pid=18547 – Assigned agent via action command
- 2026-06-30T13:59:32Z – claude:sonnet:python-pedro:implementer – shell_pid=18547 – Boundary matrix: dashboard+third-party survive ALL sync cleanups, sync+third-party survive dashboard cleanup, first/last/just-outside ports for both ranges, DaemonIntent.LOCAL_ONLY unchanged; real listeners, serial -n0, no leaks; mypy+ruff clean
- 2026-06-30T14:00:21Z – claude:opus:reviewer-renata:reviewer – shell_pid=26864 – Started review via action command
- 2026-06-30T14:04:16Z – user – shell_pid=26864 – Review passed: 4 cleanup entrypoints x real dashboard/third-party/sync listeners; dashboard+third-party survive all sync cleanups, sync survives dashboard cleanup, boundary+just-outside ports for both ranges, DaemonIntent.LOCAL_ONLY confirmed; no leaks; mypy+ruff clean

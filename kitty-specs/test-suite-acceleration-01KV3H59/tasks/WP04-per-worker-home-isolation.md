---
work_package_id: WP04
title: Per-worker HOME and state isolation
dependencies: []
requirement_refs:
- FR-002
tracker_refs: []
planning_base_branch: feat/test-suite-acceleration
merge_target_branch: feat/test-suite-acceleration
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-acceleration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-acceleration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-suite-acceleration-01KV3H59-01KV3H59
base_commit: 3aaf618fd051440a2dab99582995d25d346a39d9
created_at: '2026-06-14T17:29:41.753317+00:00'
subtasks:
- T013
- T014
- T015
- T016
phase: Phase 1 - Master enabler
agent: claude
shell_pid: '71599'
history:
- at: '2026-06-14T17:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/conftest.py
create_intent:
- tests/test_worker_home_isolation.py
execution_mode: code_change
model: ''
owned_files:
- tests/conftest.py
- tests/agent/conftest.py
- tests/test_worker_home_isolation.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Per-worker HOME and state isolation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Recommended review profile for this architecture-sensitive enabler: **architect-alphonso**.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

This is the **master enabler**. Give every xdist worker its own home/config/state directory so parallel workers never share or truncate the real `~/.spec-kitty/queue.db`. It costs nothing in coverage and unblocks WP05, WP06, WP07 and the safe local parallel run.

**Done when**: a regression test proves two worker-ids resolve distinct homes and the real `~/.spec-kitty` is untouched after a parallel run; the existing intra-worker queue-wipe fixtures still run; `ruff`/`mypy --strict` clean.

## Context & Constraints

- Evidence: `architecture/test-suite-acceleration-plan.md` (A2/PP-05). The hazard is verified: `tests/agent/conftest.py:15-41` autouse-truncates `Path.home()/".spec-kitty"` (`tests/conftest.py:119`).
- **Pattern to copy**: `tests/sync/test_sync_boundary_preflight.py:66-79` (already isolates home correctly).
- Constraints: C-005 (cross-platform: HOME/USERPROFILE/LOCALAPPDATA/XDG), keep loopback/daemon semantics intact.
- This WP owns the ROOT `tests/conftest.py`. Do not let isolation break the session-scoped `test_venv`/wheel fixtures (they must keep working — isolate home, not the venv build dir unless it is home-derived).

## Branch Strategy

- **Planning base branch**: feat/test-suite-acceleration
- **Merge target branch**: feat/test-suite-acceleration

## Subtasks & Detailed Guidance

### Subtask T013 – Per-worker HOME/XDG isolation autouse fixture

- **Purpose**: Redirect each worker’s home to a worker-unique temp dir.
- **Steps**:
  1. In `tests/conftest.py`, add an autouse fixture keyed off the xdist worker id (`request.config.workerinput["workerid"]` when present, else `"master"`).
  2. Create a per-worker base under `tmp_path_factory` and monkeypatch `Path.home` to return it, plus set env `HOME`, `USERPROFILE`, `LOCALAPPDATA`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME` to subdirs of it.
  3. Ensure serial mode (`master`) ALSO gets an isolated home — never the developer’s real one.
  4. Scope it function- or worker-level — **never session-only** (all workers would re-collide on one home; this re-introduces the hazard — see the rejected-ideas list in the audit).
- **Files**: `tests/conftest.py`.

### Subtask T014 – Compose existing queue-wipe fixtures under isolated home

- **Purpose**: Keep intra-worker isolation; do not delete the queue-wipe fixtures.
- **Steps**:
  1. Confirm the existing `reset_spec_kitty_queue_state`/`clean_spec_kitty_queue` (`tests/conftest.py:93-173`) and the agent autouse (`tests/agent/conftest.py:15-41`) now operate against the isolated home (they should, transitively, once `Path.home` is patched).
  2. Order fixtures so home isolation applies before any queue access.
- **Files**: `tests/conftest.py`, `tests/agent/conftest.py`.

### Subtask T015 – Regression test: distinct homes, real home untouched

- **Purpose**: Lock the guarantee (SC-006).
- **Steps**:
  1. Create `tests/test_worker_home_isolation.py` proving (a) two simulated worker-ids resolve distinct `Path.home()` values, and (b) a parallel run does not create/modify the real `~/.spec-kitty` (record absence/mtime before, assert unchanged after).
  2. Pair this with WP02’s `test_real_home_isolation_guard.py` (that guard flips from skip to active once this fixture exists).
- **Files**: `tests/test_worker_home_isolation.py`.

### Subtask T016 – Audit import-time `SPEC_KITTY_DIR` reads

- **Purpose**: Catch code that resolves the home/state dir at import time (before the fixture patches it).
- **Steps**:
  1. Grep for `SPEC_KITTY_DIR` / `Path.home()` reads at module import (e.g. `daemon.py:94`).
  2. For any that bind at import, document the risk in the Activity Log and, if it affects test isolation, set the env var early (e.g. via `pytest_configure`) so import-time reads also land in the isolated home.
- **Files**: `tests/conftest.py` (any early env setup); record findings in the Activity Log.

## Test Strategy

- `.venv/bin/pytest tests/test_worker_home_isolation.py -q` green.
- Run a small parallel slice: `.venv/bin/pytest tests/agent -n auto --dist loadfile -q` and confirm no real-home mutation.

## Risks & Mitigations

- **Risk**: session-only scope re-collides workers. **Mitigation**: key off worker id; function/worker scope.
- **Risk**: import-time home binding bypasses the fixture. **Mitigation**: set env in `pytest_configure` before collection.
- **Risk**: breaking the session `test_venv` fixture. **Mitigation**: isolate home only; leave the venv build dir resolution intact unless home-derived.

## Review Guidance

- Confirm worker-id keying (not session-only).
- Confirm the real `~/.spec-kitty` is provably untouched under `-n auto`.

## Activity Log

- 2026-06-14T17:10:00Z – system – Prompt created.

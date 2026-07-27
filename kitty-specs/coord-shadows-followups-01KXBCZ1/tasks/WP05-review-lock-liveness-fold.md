---
work_package_id: WP05
title: Review-lock liveness fold
dependencies:
- WP02
requirement_refs:
- FR-010
- NFR-001
tracker_refs: []
planning_base_branch: rework/coord-shadows-followups
merge_target_branch: rework/coord-shadows-followups
branch_strategy: Planning artifacts for this mission were generated on rework/coord-shadows-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rework/coord-shadows-followups unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
phase: Phase 5 - Liveness consolidation
assignee: ''
agent: "claude"
shell_pid: "902646"
history:
- at: '2026-07-12T15:14:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/lock.py
create_intent:
- tests/specify_cli/review/test_lock_liveness_fold.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/lock.py
- tests/specify_cli/review/test_lock_liveness_fold.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Review-lock liveness fold

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (role: implementer) before parsing the rest of this prompt.

## Objectives & Success Criteria

Closes **#2568**. Fold `review/lock.is_stale` onto the canonical `core/process_liveness.is_process_alive` (`return not is_process_alive(pid)`), removing the last stray `os.kill(pid,0)` liveness probe.

Done when:
- `is_stale` returns `not is_process_alive(self.pid)`; the liveness `os.kill(pid,0)` is removed.
- Branch-equivalence (live / dead / permission-denied) preserved, pinned by a characterization test.
- `os.getpid()` at acquire is retained; no orphaned imports; `ruff` + `mypy` clean.

## Context & Constraints

- **Equivalence verified branch-by-branch:** `is_stale() == not is_process_alive(pid)` for live (False), `ProcessLookupError`↔`NoSuchProcess` (True), `PermissionError`↔`AccessDenied` (False), other `OSError`↔`Exception` (True). Mechanical fold, zero semantic mismatch.
- **Scope guard:** equivalence-only. Do NOT add PID-reuse hardening to the review lock (it would require the lock to persist a create-time baseline — out of scope; WP02 owns reuse-hardening for the `shell_pid` claim path, not the review lock's own pid).
- Keep `os.getpid()` at `review/lock.py:153` (acquire) — only the liveness `os.kill` is removed.
- **C-003**: consume `core/process_liveness.is_process_alive`; no improvised probe.

## Subtasks

- [ ] T029 Fold `review/lock.py::is_stale` → `return not is_process_alive(self.pid)`; remove the liveness `os.kill`.
- [ ] T030 [P] Characterization test (`tests/specify_cli/review/test_lock_liveness_fold.py`): 3-branch equivalence (live / dead / permission-denied).
- [ ] T031 Verify no orphaned imports (dead-code gate); `ruff` + `mypy` clean.

## Definition of Done

All 3 subtasks checked; `pytest tests/specify_cli/review/ -q` green; `is_process_alive` consumed (not re-implemented); `os.getpid()` retained; `ruff` + `mypy` clean.

## Dependencies

Depends on WP02 (consumes the `is_process_alive(pid)->bool` signature; sequence after it settles).

## Activity Log

- 2026-07-12T16:22:31Z – claude – shell_pid=902646 – Assigned agent via action command

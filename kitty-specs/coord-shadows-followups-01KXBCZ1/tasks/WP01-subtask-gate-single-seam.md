---
work_package_id: WP01
title: Subtask-gate single seam
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-001
- NFR-002
- C-002
- C-003
tracker_refs: []
planning_base_branch: rework/coord-shadows-followups
merge_target_branch: rework/coord-shadows-followups
branch_strategy: Planning artifacts for this mission were generated on rework/coord-shadows-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rework/coord-shadows-followups unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Canonical-source consolidation
assignee: ''
agent: "claude"
shell_pid: "696616"
history:
- at: '2026-07-12T15:14:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/_read_path_resolver.py
create_intent:
- tests/specify_cli/status/test_subtasks_gate_dir_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/status/emit.py
- src/specify_cli/status/aggregate.py
- src/specify_cli/coordination/status_transition.py
- tests/specify_cli/status/test_subtasks_gate_dir_seam.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Subtask-gate single seam

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (role: implementer) before parsing the rest of this prompt.

## Objectives & Success Criteria

Closes **#2574**. Consolidate the triplicated "resolve PRIMARY TASKS_INDEX dir for the subtask gate" adapter into ONE canonical helper, and grant the weak site the strong git-ancestry fallback so no call site gates on a coordination husk.

Done when:
- `resolve_subtasks_gate_dir(feature_dir, repo_root, mission_slug) -> Path` exists in `missions/_read_path_resolver.py`.
- All three call sites consume it; `status/emit.py::_resolve_primary_subtasks_dir` is **deleted** and both its callers (L581, L737) repointed.
- The previously-weak `coordination/status_transition.py::_prepare_event` now recovers the PRIMARY dir when `repo_root=None` on a git-rooted mission (red-first test green).
- Dead-code gate clean; `ruff` + `mypy` zero new findings.

## Context & Constraints

- Canonical contract = emit.py's **superset**: `repo_root` → else `resolve_canonical_root(feature_dir)` → else `feature_dir` only on `WorkspaceRootNotFound`. See plan D1.
- **C-002**: carry the `cast(Path, resolve_planning_read_dir(...))` verbatim into the new helper — it is load-bearing under per-file `follow_imports=skip`. Do NOT remove it to quiet whole-repo mypy "redundant-cast" advisory noise.
- **C-003**: reuse `resolve_planning_read_dir(kind=MissionArtifactKind.TASKS_INDEX)`; do not improvise.
- Home is `missions/_read_path_resolver.py` because all three sites already import `resolve_planning_read_dir` from there (no new import edge; acyclic — the module never imports from `status/`).
- **NFR-001**: the two already-strong sites (emit, aggregate) must resolve byte-identically to today for pre-existing inputs.

## Subtasks

- [ ] T001 [P] Red-first test (`tests/specify_cli/status/test_subtasks_gate_dir_seam.py`): on a git-rooted coord-topology fixture, `_prepare_event` with `repo_root=None` currently reads the coord husk — assert the intended PRIMARY resolution (fails before T005).
- [ ] T002 Add `resolve_subtasks_gate_dir` to `missions/_read_path_resolver.py` (superset contract; carry `cast(Path, ...)`).
- [ ] T003 `status/emit.py`: delete `_resolve_primary_subtasks_dir`, repoint callers at L581 + L737 to the seam.
- [ ] T004 `status/aggregate.py::_resolve_review_gate_inputs`: replace inline resolver with the seam.
- [ ] T005 `coordination/status_transition.py::_prepare_event`: replace the weak inline (`repo_root None → feature_dir`) with the seam → makes T001 green.
- [ ] T006 [P] Characterization test: emit + aggregate byte-identical for pre-existing inputs; non-git `tmp_path` → `feature_dir`.
- [ ] T007 Dead-code gate + `ruff` + `mypy` clean.

## Campsite & Coverage Notes (post-tasks squad — fold into the listed subtasks)

- **Coverage (fold into T006):** add a DIRECT 3-branch unit test of `resolve_subtasks_gate_dir` — (a) explicit `repo_root` → passthrough; (b) `repo_root=None` + git-rooted → recovers primary; (c) `repo_root=None` + bare `tmp_path` → `WorkspaceRootNotFound` → returns `feature_dir`. The seam is otherwise only covered through call sites; pin the contract directly.
- **Don't-clean:** do NOT propagate the `# noqa: PLC0415` deferred-import pattern into the new helper's home — `_read_path_resolver.py` has no `status/` import cycle, so the helper uses module-level imports. The load-bearing `PLC0415` deferrals at the CALL sites (`emit.py:328`, `aggregate.py:723`, `status_transition.py:454`) stay as-is.
- Complexity delta is negative (collapses a triplicated resolver; `_prepare_event` drops ~2 branches) — no extraction needed.

## Definition of Done

All 7 subtasks checked (T006 includes the direct seam 3-branch test); T001 green after T005; dead-code gate reports no orphan; `pytest tests/specify_cli/status/ -q` green; `ruff check .` + `mypy` clean on owned files.

## Dependencies

None.

## Activity Log

- 2026-07-12T15:27:36Z – claude – shell_pid=696616 – Assigned agent via action command
- 2026-07-12T15:59:11Z – claude – shell_pid=696616 – Ready: canonical resolve_subtasks_gate_dir seam + strong fallback; red-first verified; 365+280+40+22 passed, dead-code clean
- 2026-07-12T16:04:41Z – user – shell_pid=696616 – APPROVED by reviewer-renata (opus): 8/8 checks; A/B repro confirms coord-husk fix; dead-code clean; mypy net-zero-new; NFR-001 byte-identical

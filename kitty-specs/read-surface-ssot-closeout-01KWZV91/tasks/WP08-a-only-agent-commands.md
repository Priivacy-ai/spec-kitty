---
work_package_id: WP08
title: 'A-only routing cluster 1: agent/* commands + status'
dependencies: []
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3131691"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/agent/tasks_finalize.py
- src/specify_cli/cli/commands/agent/tasks_dependency_graph.py
- src/specify_cli/agent_tasks_ports.py
- src/specify_cli/agent_utils/status.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-001, FR-003), `plan.md`.
**Append to `traces/*.md`.**

## Objective

Route the Thread-A-only feature_dir reads in the `agent/*` command cluster onto `read_dir(kind)`.
These files have no inline-meta collision (Thread-A-only).

## Context

- Route `resolve_feature_dir_for_mission` reads in `tasks.py`, `tasks_finalize.py`,
  `tasks_dependency_graph.py`, `agent_utils/status.py` onto `placement_seam(...).read_dir(kind)`,
  kind-correct (NFR-001 — the kind-correct surface, not the old coord husk).
- **`agent_tasks_ports.py:322`** (`feature_write_dir`) is a **by-design WRITE** (FR-003) — do NOT
  route it. It is owned here only to keep the never-route note co-located; WP11 reclassifies it in
  the gate. If the file has any OTHER genuine read site, route that; @322 stays.
- `agent_tasks_ports.py` @244/@250 already call `resolve_planning_read_dir` (seam-backed) — leave them.

## Subtasks

### T027 — agent/* command reads
Route the feature_dir reads in `tasks.py`, `tasks_finalize.py`, `tasks_dependency_graph.py` onto
`read_dir(kind)` per-kind.

### T028 — status + ports
Route `agent_utils/status.py`'s feature_dir read onto `read_dir(kind)`. In `agent_tasks_ports.py`,
leave @322 (by-design write) unchanged and record the never-route rationale in
`traces/design-decisions.md`.

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP08 --agent <name>`.

## Definition of Done
- [ ] agent/* + status reads route via `read_dir(kind)` (kind-correct).
- [ ] agent_tasks_ports.py:322 left unchanged (never-route); ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
Confirm @322 was NOT routed. Verify kind-correct routing across the cluster.

## Activity Log

- 2026-07-08T08:11:40Z – claude:sonnet:python-pedro:implementer – shell_pid=2804699 – Assigned agent via action command
- 2026-07-08T08:52:57Z – claude:sonnet:python-pedro:implementer – shell_pid=2804699 – Ready: agent/* + status reads routed kind-correct; agent_tasks_ports.py:322 left as by-design write
- 2026-07-08T08:53:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=3131691 – Started review via action command
- 2026-07-08T09:09:35Z – user – shell_pid=3131691 – Review passed: 5 STATUS-partition reads routed kind-correct (each feeds event-log/lane-state read_events/reduce/compute_incomplete_dependents/bootstrap_canonical_state; every site keeps a SEPARATE PRIMARY resolution for tasks/identity), ports.py:322 untouched (absent from diff), tasks.py re-export retired with no remaining caller/importer, test stubs mechanical (seam-swap + strengthened read_dir(STATUS_STATE) assertions, pre30 stub-drop mirrors WP05), no gate edits, 796 arch green, ruff/mypy clean. 12 move_task failures are pre-existing (reproduce identically on base, file not owned by WP08).

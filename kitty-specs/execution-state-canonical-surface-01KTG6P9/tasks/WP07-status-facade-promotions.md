---
work_package_id: WP07
title: Status facade promote/demote + __all__
dependencies:
- WP06
requirement_refs:
- FR-013
- C-007
tracker_refs: []
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on
  feat/execution-state-strangler. During /spec-kitty.implement this WP may
  branch from a dependency-specific base, but completed changes must merge back
  into feat/execution-state-strangler unless the human explicitly redirects the
  landing branch.
subtasks:
- T026
- T027
- T028
phase: Phase 4 - Facade
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2864666"
history:
- at: '2026-06-07T05:16:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/__init__.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/__init__.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Status facade promote/demote + __all__

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below).

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objectives & Success Criteria

Finalize per-submodule promote/demote/route decisions and update `status/__init__.py` `__all__`, so the facade exposes exactly the symbols external consumers legitimately need.

> **Post-FSM-rebase note (2026-06-08):** `COORD_OWNED_STATUS_FILES` is **already promoted** into `status/__init__.py` `__all__` (derived from `EVENTS_FILENAME`/`SNAPSHOT_FILENAME`) by the FSM reduction pass — record it as done in the inventory, do **not** re-promote it.

- FR-013. C-007 (`__all__` convention). Enables WP08.

## Context & Constraints

- Decisions framework: [occurrence_map.yaml](../occurrence_map.yaml) (25 submodules; resolve all `REVIEW` entries here). Contract: [contracts/status_boundary.md](../contracts/status_boundary.md).
- PROMOTE = add to facade `__all__`; ROUTE = consumer will use `MissionStatus` (WP08/WP10); PRIVATE = `_`-prefix, no external import.

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T026 – Finalize per-submodule decisions
- **Steps**: For each submodule in the occurrence map (esp. the `REVIEW` ones: `wp_metadata`, `wp_state`, `adapters`, `locking`, `identity_audit`, `bootstrap`, `uninitialized_hint`, `preflight`, `event_log_merge`, `transition_context`, `doctor`), inspect real consumers and set PROMOTE/ROUTE/PRIVATE. Record the final decision back into the occurrence map.
- **Files**: `occurrence_map.yaml`.

### Subtask T027 – Update `__all__`
- **Steps**: Add promoted symbols to `src/specify_cli/status/__init__.py` `__all__`; `_`-prefix demoted symbols.
- **Files**: `src/specify_cli/status/__init__.py`, demoted modules.

### Subtask T028 – Fix internal references for renames
- **Steps**: Update intra-`status/` references to any `_`-prefixed names.

## Test Strategy

- `status/` unit tests green; `python -c "import specify_cli.status as s; [getattr(s,n) for n in s.__all__]"` succeeds.

## Risks & Mitigations

- Over-promotion → confirm each promoted symbol has a genuine external consumer; otherwise PRIVATE.

## Review Guidance — **Persona IC: Paula Patterns**

- Reviewer profile: `paula-patterns`. Verify the facade surface is minimal and intentional; no internal/plumbing symbol promoted to dodge the boundary. Confirm the occurrence-map decisions are complete (no `REVIEW` left).

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
- 2026-06-08T09:05:50Z – claude:opus:python-pedro:implementer – shell_pid=2844466 – Started implementation via action command
- 2026-06-08T09:10:28Z – claude:opus:python-pedro:implementer – shell_pid=2844466 – Ready for review: finalized 11 REVIEW submodule decisions (8 PROMOTE, 2 ROUTE, 1 PRIVATE-no-rename); added 17 symbols to status/__init__.py __all__ (now 95). Facade import OK, ruff+mypy clean, 2739 status tests green.
- 2026-06-08T09:13:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=2854112 – Started review via action command
- 2026-06-08T09:17:37Z – user – shell_pid=2854112 – Moved to planned
- 2026-06-08T09:18:26Z – claude:sonnet:python-pedro:implementer – shell_pid=2861361 – Started implementation via action command
- 2026-06-08T09:20:11Z – claude:sonnet:python-pedro:implementer – shell_pid=2861361 – Cycle 2: demoted filter_dossier_snapshots (test-only over-promotion); still importable from status.preflight
- 2026-06-08T09:20:36Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2864666 – Started review via action command

---
work_package_id: WP05
title: Canonical State — Event Log Authority
lane: "for_review"
dependencies: [WP02]
requirement_refs:
- C-004
- FR-008
- FR-009
- NFR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: 057-canonical-context-architecture-cleanup-WP02
base_commit: 9233794cfbff4d8da4d0f8e0da1582c44d84aeed
created_at: '2026-03-27T18:33:03.107843+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
phase: Phase B - State
assignee: ''
agent: coordinator
shell_pid: '31099'
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-27T17:23:39Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Canonical State — Event Log Authority

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`

---

## Objectives & Success Criteria

- Event log is the sole authority for mutable WP state. No other file is consulted for lane, progress, or review status.
- `status/legacy_bridge.py`, `status/phase.py`, `status/reconcile.py`, `status/migrate.py` are deleted.
- `emit_status_transition()` writes only to the event log — no dual-write.
- No frontmatter lane/review_status/reviewed_by reads or writes remain anywhere in the codebase.
- `spec-kitty status` displays board state computed entirely from event log.

## Context & Constraints

- **Spec**: FR-008 (canonical event log), FR-009 (remove mutable frontmatter), C-004 (no dual-authority)
- **Plan**: Move 3 — Canonical State section
- **Key files to simplify**: `src/specify_cli/status/emit.py`, `src/specify_cli/status/reducer.py`
- **Key files to delete**: `legacy_bridge.py` (~300 lines), `phase.py` (~150 lines), `reconcile.py` (~200 lines), `migrate.py` (~150 lines)
- **Key constraint**: After this WP, no runtime path consults both event log and frontmatter for mutable state.

## Subtasks & Detailed Guidance

### Subtask T023 – Simplify status/emit.py

- **Purpose**: Remove dual-write path, phase checks, and frontmatter update calls from the emission pipeline.
- **Steps**:
  1. Read `src/specify_cli/status/emit.py` thoroughly — understand `emit_status_transition()`
  2. Remove all calls to `update_frontmatter_views()` or any frontmatter writing
  3. Remove all `resolve_phase()` calls and phase-conditional logic
  4. Remove any `legacy_bridge` imports
  5. The simplified flow: validate transition → append event to JSONL → done
  6. Keep the validation logic (transition matrix, guards) — that's still needed
  7. Keep the event construction (StatusEvent with all fields) — that's still needed
  8. The function should be ~30-40 lines after simplification (down from potentially 100+)
- **Files**: `src/specify_cli/status/emit.py` (modify, significant simplification)

### Subtask T024 – Create status/views.py

- **Purpose**: Generate derived views (status.json, board summaries) from event log. This replaces the output-generating functionality of legacy_bridge.
- **Steps**:
  1. Create `src/specify_cli/status/views.py`
  2. Implement `generate_status_view(feature_dir: Path) -> dict`:
     - Read events via `read_events(feature_dir)`
     - Reduce to snapshot via `reduce(events)`
     - Return snapshot as dict for JSON serialization
  3. Implement `write_derived_views(feature_dir: Path, derived_dir: Path) -> None`:
     - Generate status.json from snapshot
     - Generate board-summary.json (lane counts, WP lists per lane)
     - Write to `derived_dir/<feature_slug>/`
     - Use atomic writes
  4. These views are output-only — never read as authority
- **Files**: `src/specify_cli/status/views.py` (new, ~80 lines)

### Subtask T025 – Delete status/legacy_bridge.py

- **Purpose**: Remove the entire dual-write bridge.
- **Steps**:
  1. Delete `src/specify_cli/status/legacy_bridge.py` (~300 lines)
  2. Remove from `src/specify_cli/status/__init__.py` exports
  3. Search for all imports: `from specify_cli.status.legacy_bridge import`, `from specify_cli.status import.*legacy`
  4. Update all callers — they should now use `views.py` or nothing (if they were reading)
- **Files**: Delete `legacy_bridge.py`, update `__init__.py` and callers
- **Parallel?**: Yes — can proceed alongside T023

### Subtask T026 – Delete phase.py, reconcile.py, migrate.py

- **Purpose**: Remove the three-phase model, drift detection, and frontmatter-based migration.
- **Steps**:
  1. Delete `src/specify_cli/status/phase.py` (~150 lines)
  2. Delete `src/specify_cli/status/reconcile.py` (~200 lines)
  3. Delete `src/specify_cli/status/migrate.py` (~150 lines)
  4. Remove from `__init__.py` exports
  5. Remove `resolve_phase()` calls from entire codebase
  6. Remove `reconcile` imports and calls
  7. State migration functionality moves to the one-shot migration module (WP13)
- **Files**: Delete 3 files, update exports and callers
- **Parallel?**: Yes — independent of T023-T025

### Subtask T027 – Strip mutable frontmatter from entire codebase

- **Purpose**: Remove ALL reads and writes of mutable status fields in WP frontmatter.
- **Steps**:
  1. Grep the entire codebase for these frontmatter field accesses:
     - `lane` (as a frontmatter key, not the Lane enum)
     - `review_status`
     - `reviewed_by`
     - `review_feedback`
     - `progress` (as a frontmatter field)
  2. For each occurrence:
     - If it's a write: remove entirely (status comes from event log now)
     - If it's a read for display: replace with event log query via `reduce()`
     - If it's a read for logic (e.g., `if wp.lane == "done"`): replace with snapshot lookup
  3. Update `move-task` command: it should now only emit events, not update frontmatter
  4. Update any kanban/board display code to read from snapshot
  5. Verify: `grep -rn "review_status\|reviewed_by\|review_feedback" src/` returns zero in non-migration code
  6. Verify: no code reads `lane` from frontmatter (only from snapshot)
- **Files**: ~10-20 files across `src/specify_cli/`
- **Notes**: This is a codebase-wide sweep. Be thorough. The `lane` field in the WP prompt template frontmatter (task-prompt-template.md) should also be removed from the template.

### Subtask T028 – Tests for simplified status module

- **Purpose**: Verify the event-log-only model works correctly.
- **Steps**:
  1. Update tests in `tests/specify_cli/status/`
  2. Delete tests for `legacy_bridge.py`, `phase.py`, `reconcile.py`, `migrate.py`
  3. Add/update tests for `emit.py`: verify emit writes ONLY to event log, no frontmatter
  4. Add tests for `views.py`: verify derived views match snapshot state
  5. Add test: verify `spec-kitty status` output matches event log (not frontmatter)
  6. Add negative test: verify no code path reads lane from frontmatter
- **Files**: `tests/specify_cli/status/` (modify + delete, net ~100 lines changed)
- **Parallel?**: Yes

## Risks & Mitigations

- **Missed frontmatter reads**: Some code may read `lane` indirectly (e.g., via a YAML loader that returns all fields). Use grep AND run full test suite.
- **Status display regression**: Before deleting, snapshot the output of `spec-kitty status` on a test project. After changes, verify identical output.
- **move-task backwards compatibility**: The `move-task` command must still work but now emits events instead of editing frontmatter.

## Review Guidance

- `grep -rn "update_frontmatter_views\|resolve_phase\|legacy_bridge" src/` — zero results
- `grep -rn "reconcile\|migrate" src/specify_cli/status/` — zero results (except __init__.py cleanup)
- Verify `emit_status_transition()` has no frontmatter write calls
- Verify `move-task` emits event without touching frontmatter
- Run full test suite — no failures from missing status modules

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.
- 2026-03-27T18:33:03Z – coordinator – shell_pid=31099 – lane=doing – Assigned agent via workflow command
- 2026-03-27T19:42:16Z – coordinator – shell_pid=31099 – lane=for_review – Event log is sole authority. Deleted: legacy_bridge, phase, reconcile, migrate. Fixed implement.py NameError in single-dep path. 988 tests pass, 3 pre-existing failures in test_implement_multi_parent_integration.py unrelated to WP05.

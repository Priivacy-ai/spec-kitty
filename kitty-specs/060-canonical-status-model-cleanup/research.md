# Research: Canonical Status Model Cleanup

## R-001: Change Sequencing Strategy

**Decision**: Bootstrap-first (add canonical state before removing fallbacks).

**Rationale**: The repo has ~2000+ tests. Removing fallbacks first would cause a wide, noisy failure surface. Adding canonical bootstrap to finalize-tasks first ensures canonical state exists everywhere before the safety net is removed.

**Sequence**: (1) finalize-tasks bootstrap → (2) convert generators/tests → (3) remove fallbacks → (4) fence migration paths.

**Alternatives considered**: Remove-first (clean-room approach) — rejected because it creates maximum churn before the codebase has a consistent way to establish canonical state.

## R-002: Frontmatter Lane Read Sites

**Decision**: 4 active runtime read sites need fallback removal in Phase C.

**Findings**:
- `tasks_support.py:293` — `WorkPackage.lane` property (hybrid: event log first, frontmatter fallback)
- `dashboard/scanner.py:322` — `_count_wps_by_lane_frontmatter()` (hybrid fallback)
- `mission_v1/guards.py:169` — `_read_lane_from_frontmatter()` (direct frontmatter read)
- `next/runtime_bridge.py:117` — `wp_state.get("lane", "planned")` (frontmatter source)

**Already clean**: `status/lane_reader.py` is event-log-only. `move_task()` lane WRITE path is already event-log-only via `emit_status_transition()`.

## R-003: Frontmatter Lane Write Sites

**Decision**: 3 write sites become migration-only in Phase D. No active runtime code writes lane to frontmatter.

**Findings**:
- `task_metadata_validation.py:123` — `repair_lane_mismatch()` (writes frontmatter lane)
- `m_2_0_6_consistency_sweep.py:203` — normalizes frontmatter lane values
- `m_0_9_1_complete_lane_migration.py:331` — `_ensure_lane_in_frontmatter()` (creates frontmatter lane)

All three are either migration code or validation/repair code that should be migration-only.

## R-004: Bootstrap/Sync Logic

**Decision**: Delete the `move_task()` bootstrap block (tasks.py:1088-1115) in Phase C.

**Findings**: The bootstrap block in `move_task()` detects when canonical event lane doesn't match frontmatter lane and seeds/syncs a canonical event from frontmatter. After Phase A adds finalize-tasks bootstrap, this fallback path is unnecessary. Deleting it enforces the hard-fail contract.

**Alternatives considered**: Keep as a "recovery" path — rejected per spec C-005 (no fallback logic).

## R-005: Template Cleanup Scope

**Decision**: 6 template files need lane field and lane activity log removal.

**Findings**:
- `missions/software-dev/templates/tasks-template.md` — lane field docs
- `missions/software-dev/templates/task-prompt-template.md` — lane activity log examples
- `missions/research/templates/task-prompt-template.md` — same
- `missions/documentation/templates/task-prompt-template.md` — same
- `missions/software-dev/command-templates/tasks.md` — WP examples with frontmatter lane
- `missions/software-dev/command-templates/tasks-packages.md` — same

## R-006: Shared Helper for Finalize-Tasks Bootstrap

**Decision**: Factor canonical bootstrap into a shared helper importable by both finalize-tasks entrypoints.

**Rationale**: Both `feature.py` and `tasks.py` define `finalize_tasks`. The canonical bootstrap logic (scan WPs → check event log → emit initial events → materialize) must be identical in both. A shared helper in `specify_cli/status/` or a new `specify_cli/tasks_bootstrap.py` avoids duplication.

**Dependencies**: Uses existing `emit_status_transition()` and `materialize()` from `specify_cli/status/`.

## R-007: Partial Canonical State Handling

**Decision**: Distinguish "event log absent" (hard-fail) from "event log exists, WP missing" (show uninitialized for reads, hard-fail for mutations).

**Rationale**: Per spec FR-009 and FR-009a, a missing event log is a global failure (feature not finalized), while a missing WP entry is a specific gap (one WP wasn't finalized). Read-only commands can still render the known WPs and flag the gap.

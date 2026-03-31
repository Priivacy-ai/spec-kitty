# Research: Canonical Status Model Cleanup

## R-001: Change Sequencing Strategy

**Decision**: Bootstrap-first (add canonical state before removing fallbacks).

**Rationale**: The repo has ~2000+ tests. Removing fallbacks first would cause a wide, noisy failure surface. Adding canonical bootstrap to finalize-tasks first ensures canonical state exists everywhere before the safety net is removed.

**Sequence**: (1) finalize-tasks bootstrap → (2) convert generators/tests → (3) remove fallbacks → (4) fence migration paths.

**Alternatives considered**: Remove-first (clean-room approach) — rejected because it creates maximum churn before the codebase has a consistent way to establish canonical state.

## R-002: Frontmatter Lane Read Sites

**Decision**: 8 active runtime read sites + 1 bootstrap site need fallback removal in Phase C.

**Findings**:
- `tasks_support.py:293` — `WorkPackage.lane` property (hybrid: event log first, frontmatter fallback)
- `dashboard/scanner.py:322` — `_count_wps_by_lane_frontmatter()` (hybrid fallback)
- `dashboard/scanner.py:454` — additional dashboard fallback to `frontmatter.get("lane", default_lane)` when event log empty
- `mission_v1/guards.py:169` — `_read_lane_from_frontmatter()` (direct frontmatter read)
- `next/runtime_bridge.py:117` — `wp_state.get("lane", "planned")` (frontmatter source)
- `cli/commands/agent/workflow.py:390` — `implement` command frontmatter lane fallback via `extract_scalar(wp.frontmatter, "lane")`
- `cli/commands/agent/workflow.py:954` — `review` command same fallback pattern
- `cli/commands/merge.py:72` — merge preflight reads `frontmatter.get("lane")` with fallback
- `cli/commands/agent/tasks.py:1088-1115` — `move_task()` bootstrap/sync block seeds event from frontmatter

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

## R-005: Template + Generator Cleanup Scope

**Decision**: 12+ template/generator sites need lane cleanup, across specify_cli templates, doctrine templates, command templates, and README generators.

**Findings** (specify_cli mission templates):
- `missions/software-dev/templates/tasks-template.md` — lane field docs
- `missions/software-dev/templates/task-prompt-template.md` — lane frontmatter + activity log examples
- `missions/research/templates/task-prompt-template.md` — same
- `missions/documentation/templates/task-prompt-template.md` — same
- `missions/software-dev/command-templates/tasks.md` — WP examples with frontmatter lane
- `missions/software-dev/command-templates/tasks-packages.md` — same

**Findings** (doctrine templates — active, not archival):
- `doctrine/templates/task-prompt-template.md` — teaches `lane:` in frontmatter
- `doctrine/missions/software-dev/templates/task-prompt-template.md` — same
- `doctrine/missions/research/templates/task-prompt-template.md` — same
- `doctrine/missions/documentation/templates/task-prompt-template.md` — same

**Findings** (README generators):
- `core/worktree.py:384` — generates README documenting `lane:` in WP frontmatter
- `cli/commands/agent/feature.py:640` — generates README documenting `lane:` in WP frontmatter

**Findings** (runtime body-note writers — still emit `lane=` in activity logs):
- `cli/commands/agent/tasks.py:1169` — `move_task()` body note with `lane={target_lane}`
- `cli/commands/agent/tasks.py:1572` — `add_note()` body note with `lane={current_lane}`
- `cli/commands/agent/workflow.py:476` — `implement` body note with `lane=doing`
- `cli/commands/agent/workflow.py:1010` — `review` body note with `lane=...`

## R-005a: History Parser Disposition

**Decision**: Demote `status/history_parser.py` to migration-only in Phase D.

**Rationale**: The history parser reconstructs transition chains from frontmatter `history[]` arrays. After canonical status is the sole authority, this module is only needed by explicit migration commands that bootstrap event logs from legacy frontmatter. It should not be called from active runtime paths.

## R-005b: Regression Guard Strategy

**Decision**: Use targeted patterns for regression guards, not broad `["lane"]` matching.

**Rationale**: Legitimate canonical-status consumers already use `wp["lane"]` and `state.get("lane")` against reducer/materialized state (e.g., `agent_utils/status.py:125`, `status/views.py:99`). A broad guard matching any `["lane"]` pattern would false-positive on valid code.

**Guard strategy**:
- Template guard: scan for `lane:` in YAML frontmatter position + `lane=` in activity log format strings
- Runtime guard: scan for `frontmatter.get("lane")`, `extract_scalar(..., "lane")`, `frontmatter["lane"]` — patterns that specifically access frontmatter lane, not reducer/snapshot lane
- Exclusion list: `upgrade/migrations/`, `migration/`, `status/history_parser.py` (migration-only modules)

## R-006: Shared Helper for Finalize-Tasks Bootstrap

**Decision**: Factor canonical bootstrap into a shared helper importable by both finalize-tasks entrypoints.

**Rationale**: Both `feature.py` and `tasks.py` define `finalize_tasks`. The canonical bootstrap logic (scan WPs → check event log → emit initial events → materialize) must be identical in both. A shared helper in `specify_cli/status/` or a new `specify_cli/tasks_bootstrap.py` avoids duplication.

**Dependencies**: Uses existing `emit_status_transition()` and `materialize()` from `specify_cli/status/`.

## R-007: Partial Canonical State Handling

**Decision**: Distinguish "event log absent" (hard-fail) from "event log exists, WP missing" (show uninitialized for reads, hard-fail for mutations).

**Rationale**: Per spec FR-009 and FR-009a, a missing event log is a global failure (feature not finalized), while a missing WP entry is a specific gap (one WP wasn't finalized). Read-only commands can still render the known WPs and flag the gap.

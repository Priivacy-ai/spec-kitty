---
work_package_id: WP06
title: Weighted Progress and Materialization
lane: "for_review"
dependencies: [WP05]
requirement_refs:
- FR-010
- FR-011
- FR-022
- FR-023
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: 057-canonical-context-architecture-cleanup-WP05
base_commit: 7ccd2228ac14a48836a544379477d5c32336ef07
created_at: '2026-03-27T19:42:45.543325+00:00'
subtasks:
- T029
- T030
- T031
- T032
- T033
phase: Phase B - State
assignee: ''
agent: coordinator
shell_pid: '91906'
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

# Work Package Prompt: WP06 – Weighted Progress and Materialization

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`

---

## Objectives & Success Criteria

- Weighted progress computation exists as a shared library usable by CLI and future SaaS.
- `spec-kitty materialize` regenerates all derived views from event log.
- CLI commands lazily regenerate derived artifacts when stale.
- `.kittify/derived/` directory structure exists and is gitignored.
- Machine-readable JSON schemas are stable and documented for SaaS consumption.

## Context & Constraints

- **Spec**: FR-010, FR-011, FR-022, FR-023
- **Plan**: Move 3 — Weighted Progress section, Filesystem Layout
- **Depends on**: WP05 (simplified status module)

## Subtasks & Detailed Guidance

### Subtask T029 – Create status/progress.py

- **Purpose**: Single shared implementation of weighted progress.
- **Steps**:
  1. Create `src/specify_cli/status/progress.py`
  2. Implement `compute_weighted_progress(snapshot: StatusSnapshot, wp_weights: dict[str, float] | None = None, lane_weights: dict[str, float] | None = None) -> ProgressResult`:
     - Default lane weights: `{"planned": 0.0, "claimed": 0.05, "in_progress": 0.3, "for_review": 0.6, "approved": 0.8, "done": 1.0, "blocked": 0.0, "canceled": 0.0}`
     - Default WP weight: equal per WP (1.0 each)
     - Compute: `sum(wp_weight * lane_weight[wp.lane] for each WP) / sum(wp_weight for each WP) * 100`
     - This is a lane-weighted model, NOT done-only. A mission with all WPs in `in_progress` shows ~30%, not 0%.
     - Return `ProgressResult` dataclass with: percentage, per_lane_counts, per_wp breakdown (wp_code, lane, fractional_progress), done_count, total_count
  3. `ProgressResult` must be JSON-serializable for machine consumption
  4. Implement `generate_progress_json(feature_dir: Path, derived_dir: Path) -> None`:
     - Materialize snapshot → compute progress → write to `derived_dir/<slug>/progress.json`
- **Files**: `src/specify_cli/status/progress.py` (new, ~70 lines)

### Subtask T030 – Create `spec-kitty materialize` command

- **Purpose**: Explicit command for CI/debugging/external consumers to force-regenerate all derived views.
- **Steps**:
  1. Create `src/specify_cli/cli/commands/materialize.py`
  2. Implement `materialize` command:
     - Parameters: `--feature <slug>` (optional — all features if omitted), `--json` (output summary)
     - For each feature: regenerate status.json, progress.json, board-summary.json to `.kittify/derived/<slug>/`
     - Use `views.write_derived_views()` from WP05 and `generate_progress_json()` from T029
     - Report: features processed, files written, timestamps
  3. Register in CLI app
- **Files**: `src/specify_cli/cli/commands/materialize.py` (new, ~50 lines)
- **Parallel?**: Yes — can proceed alongside T029

### Subtask T031 – Add lazy regeneration

- **Purpose**: CLI commands that read derived state should auto-regenerate when stale.
- **Steps**:
  1. Implement `materialize_if_stale(feature_dir: Path, repo_root: Path) -> StatusSnapshot`:
     - Check if derived status.json exists
     - Check if event log mtime > derived file mtime (or derived missing)
     - If stale: regenerate via `views.write_derived_views()` + `generate_progress_json()`
     - Return the current snapshot
  2. Add this call to `spec-kitty status` and any other command that displays board state
  3. Place in `src/specify_cli/status/views.py` or a new `src/specify_cli/status/cache.py`
- **Files**: Status module (modify, ~30 lines added)

### Subtask T032 – Create `.kittify/derived/` structure and update .gitignore

- **Purpose**: Ensure the derived directory exists and is properly gitignored.
- **Steps**:
  1. Add `.kittify/derived/` to `.gitignore`
  2. Add `.kittify/runtime/` to `.gitignore` (if not already present)
  3. Ensure the materialize command creates `.kittify/derived/<slug>/` directories as needed
  4. Remove any existing `.gitignore` entries for tracked `status.json` files that should now be derived
  5. Verify: `kitty-specs/*/status.json` is no longer tracked (may need `git rm --cached` in migration)
- **Files**: `.gitignore` (modify), possibly `src/specify_cli/status/views.py` (directory creation)
- **Parallel?**: Yes — independent of progress computation

### Subtask T033 – Tests for progress and materialization

- **Purpose**: 90%+ coverage on progress computation and materialization.
- **Steps**:
  1. Create `tests/specify_cli/status/test_progress.py`:
     - Equal weight: 3 done out of 5 → 60%
     - Custom weights: verify weighted calculation
     - Zero WPs: handle gracefully
     - All done: 100%
  2. Create `tests/specify_cli/cli/commands/test_materialize.py`:
     - Materialize writes correct files to `.kittify/derived/`
     - Materialize with `--json` outputs summary
  3. Test lazy regeneration: stale detection, auto-regeneration
- **Files**: New test files (~100 lines total)
- **Parallel?**: Yes

## Risks & Mitigations

- **Stale file race condition**: Two concurrent processes checking staleness. Use file locking or accept eventual consistency.
- **Missing event log**: New features may not have events yet. Handle empty event log gracefully (0% progress, empty board).

## Review Guidance

- Verify progress computation is a pure function (no side effects, no file reads inside)
- Verify materialize creates all expected files in `.kittify/derived/`
- Verify lazy regeneration triggers on stale but not on fresh

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.
- 2026-03-27T19:42:45Z – coordinator – shell_pid=91906 – lane=doing – Assigned agent via workflow command
- 2026-03-27T19:50:32Z – coordinator – shell_pid=91906 – lane=for_review – Lane-weighted progress and materialization complete: status/progress.py (pure function, DEFAULT_LANE_WEIGHTS), spec-kitty materialize CLI command, materialize_if_stale lazy regen, .kittify/derived/ gitignored, 34 tests all passing

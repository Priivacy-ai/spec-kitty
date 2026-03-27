---
work_package_id: WP14
title: Integration Tests and Final Cleanup
lane: "for_review"
dependencies:
- WP08
requirement_refs:
- C-001
- NFR-004
- NFR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: 057-canonical-context-architecture-cleanup-WP08
base_commit: f2d753d911f2665de2df271b31db1224460801f9
created_at: '2026-03-27T20:13:36.966640+00:00'
subtasks:
- T070
- T071
- T072
- T073
- T074
phase: Phase D - Surface and Migration
assignee: ''
agent: coordinator
shell_pid: '17109'
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

# Work Package Prompt: WP14 – Integration Tests and Final Cleanup

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`

---

## Objectives & Success Criteria

- End-to-end integration tests pass for all three major flows: context lifecycle, migration, merge engine.
- No stale imports, dead code references, or orphan test fixtures remain.
- `mypy --strict` passes on all new modules.
- `pytest` coverage > 90% on new code.
- The big-bang release is validated as coherent.

## Context & Constraints

- **Spec**: NFR-004 (test coverage), NFR-006 (backward deletion), C-001 (big-bang release)
- **Plan**: All moves must be complete before this WP
- **Depends on**: WP08, WP10, WP13 — all architectural moves and migration must be done

## Subtasks & Detailed Guidance

### Subtask T070 – E2E test: full WP lifecycle with context tokens

- **Purpose**: Verify SC-001: agent completes full lifecycle using only `--context <token>`.
- **Steps**:
  1. Create `tests/specify_cli/integration/test_context_lifecycle.py`
  2. Test scenario:
     - Initialize a test project with `spec-kitty init`
     - Create a feature with `create-feature`
     - Create WP files with realistic frontmatter (including work_package_id, execution_mode, owned_files)
     - Resolve context: `agent context resolve --wp WP01 --feature <slug>` → get token
     - Implement: use token with implement command
     - Move task: `agent tasks move-task --context <token> --to for_review`
     - Review: use token with review command
     - Accept: use token with accept command
     - At no point should heuristic detection be triggered
  3. Verify: no `detect_feature()` calls in the callstack (mock and assert not called)
  4. Use real git repos (tmp_path fixture + git init)
- **Files**: `tests/specify_cli/integration/test_context_lifecycle.py` (new, ~150 lines)
- **Parallel?**: Yes — independent of T071, T072

### Subtask T071 – E2E test: legacy project migration

- **Purpose**: Verify SC-005: migration converts legacy project with zero status loss.
- **Steps**:
  1. Create `tests/specify_cli/integration/test_migration_e2e.py`
  2. Create fixture: legacy project with:
     - 10+ features in mixed states (planned, in-progress, for_review, done)
     - Features with event logs, features without
     - Features with status.json, features without
     - WPs in various lane states
     - Agent command files with old template content
  3. Capture pre-migration state: board snapshot for each feature
  4. Run migration: `spec-kitty upgrade`
  5. Verify post-migration:
     - All features have mission_id in meta.json
     - All WPs have work_package_id, wp_code, execution_mode, owned_files
     - No mutable frontmatter fields remain
     - Event log exists for every feature with events matching pre-migration state
     - Board state computed from event log matches pre-migration board state
     - Agent command files are thin shims
     - schema_version == 3
  6. Verify: any command works after migration (e.g., `spec-kitty status`)
- **Files**: `tests/specify_cli/integration/test_migration_e2e.py` (new, ~200 lines)
- **Parallel?**: Yes — independent of T070, T072

### Subtask T072 – E2E test: merge engine v2 with resume

- **Purpose**: Verify SC-004: merge is deterministic, resumable, and handles conflicts.
- **Steps**:
  1. Create `tests/specify_cli/integration/test_merge_e2e.py`
  2. Create fixture: project with a feature having 3 WPs, each with a branch and commits
  3. Test full merge: all 3 WPs merge successfully
  4. Test resume: simulate interruption after WP01, resume from WP02
  5. Test conflict: create a spec-kitty-owned file conflict (event log), verify auto-resolution
  6. Test determinism: merge from different main repo checkout states, verify same result
  7. Verify: main repo checkout unchanged after merge
  8. Use real git repos with actual branches and commits
- **Files**: `tests/specify_cli/integration/test_merge_e2e.py` (new, ~200 lines)
- **Parallel?**: Yes — independent of T070, T071

### Subtask T073 – Dead code sweep

- **Purpose**: Remove any remaining references to deleted modules, functions, or patterns.
- **Steps**:
  1. Search for ALL deleted module names:
     ```
     grep -rn "feature_detection\|legacy_bridge\|phase\.py\|reconcile\|executor\|forecast\|status_resolver\|agent_context" src/ tests/
     ```
  2. Search for deleted function names:
     ```
     grep -rn "detect_feature\|resolve_phase\|update_frontmatter_views\|update_agent_context" src/ tests/
     ```
  3. Search for deleted class names:
     ```
     grep -rn "FeatureContext\|VersionDetector" src/ tests/
     ```
     (VersionDetector is rewritten, not deleted, but old usage patterns should be gone)
  4. Search for stale imports: run `python -c "import specify_cli"` to check for import errors
  5. Search for orphan test fixtures that set up deleted scenarios
  6. Fix any remaining references
- **Files**: Various files across `src/` and `tests/`

### Subtask T074 – Final validation

- **Purpose**: Confirm quality gates pass for the entire new codebase.
- **Steps**:
  1. Run `mypy --strict src/specify_cli/context/ src/specify_cli/ownership/ src/specify_cli/shims/ src/specify_cli/migration/`
     - Fix any type errors
  2. Run `mypy --strict` on modified files in `src/specify_cli/status/`, `src/specify_cli/merge/`, `src/specify_cli/core/`
     - Fix any type errors introduced by changes
  3. Run `pytest` with coverage:
     ```bash
     pytest tests/ --cov=src/specify_cli/context --cov=src/specify_cli/ownership --cov=src/specify_cli/shims --cov=src/specify_cli/migration --cov-report=term-missing
     ```
     - Verify 90%+ coverage on each new module
  4. Run `ruff check src/` — fix any lint issues
  5. Run full test suite: `pytest tests/` — everything passes
- **Files**: Various files (type annotation fixes, lint fixes)

## Risks & Mitigations

- **Integration test flakiness**: Use deterministic timestamps and ULIDs in fixtures. Avoid time-dependent assertions.
- **Coverage gaps**: Use coverage report to identify untested paths. Focus on error paths and edge cases.

## Review Guidance

- All three E2E tests must pass in CI
- `mypy --strict` must pass on all new modules
- Coverage report shows 90%+ on new code
- Dead code sweep grep returns zero results
- Full test suite passes (no regressions from old tests)

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.
- 2026-03-27T20:13:37Z – coordinator – shell_pid=17109 – lane=doing – Assigned agent via workflow command
- 2026-03-27T21:54:18Z – coordinator – shell_pid=17109 – lane=for_review – All tasks complete: T070 (23 context lifecycle tests), T071 (13 migration E2E tests), T072 (36 merge engine tests), T073 (dead code sweep across 10 test files), T074 (ruff clean, mypy passes on new modules). Committed as ecef34f5.

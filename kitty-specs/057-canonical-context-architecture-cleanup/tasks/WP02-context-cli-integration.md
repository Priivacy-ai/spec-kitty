---
work_package_id: WP02
title: Context CLI Integration
lane: planned
dependencies: [WP01]
requirement_refs:
- FR-002
- FR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
phase: Phase A - Foundation
assignee: ''
agent: ''
shell_pid: ''
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

# Work Package Prompt: WP02 – Context CLI Integration

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual worktree base may differ later**: `/spec-kitty.implement` populates frontmatter `base_branch` when the worktree is created. For stacked WPs it may point at another WP branch.

---

## Objectives & Success Criteria

- Wire context tokens into the CLI: `resolve` and `show` commands work end-to-end.
- Every workflow command accepts `--context <token>`.
- `feature_detection.py` (668 lines) is deleted entirely. Zero callers of `detect_feature()` remain.
- Commands fail fast with actionable errors when context is missing.

## Context & Constraints

- **Spec**: FR-002 (context token CLI), FR-003 (fail-fast on missing context)
- **Plan**: Move 1 — Context CLI Integration section
- **WP01 dependency**: context/models.py, store.py, resolver.py, middleware.py must exist
- **Key constraint**: This is the most invasive WP — touching many CLI command files. Grep exhaustively before marking complete.

## Subtasks & Detailed Guidance

### Subtask T007 – Create CLI commands for context resolve and show

- **Purpose**: Provide the entry points for agents to resolve and inspect context tokens.
- **Steps**:
  1. Create `src/specify_cli/cli/commands/context.py`
  2. Implement `resolve` command:
     - Parameters: `--wp <wp_code>` (required), `--feature <feature_slug>` (optional), `--agent <agent_name>` (optional, default "unknown")
     - Calls `resolve_context()` from context/resolver.py
     - Outputs: token string on stdout, plus JSON summary if `--json` flag
     - Example output: `ctx-01HVXYZ...` (just the token for piping)
     - With `--json`: `{"token": "ctx-01HV...", "mission_id": "...", "wp_code": "WP03", ...}`
  3. Implement `show` command:
     - Parameters: `--context <token>` (required)
     - Calls `load_context()` from context/store.py
     - Pretty-prints all bound fields using rich Table
     - With `--json`: outputs raw JSON
  4. Register commands in the agent CLI group
- **Files**: `src/specify_cli/cli/commands/context.py` (new, ~80 lines)

### Subtask T008 – Add `--context` parameter to all workflow commands

- **Purpose**: Every command that operates on a feature/WP must accept the context token.
- **Steps**:
  1. Identify all workflow commands that currently call `detect_feature()` or accept `--feature`/`--wp` args. At minimum:
     - `implement`, `review`, `accept`, `merge`, `status`
     - `agent tasks move-task`, `agent tasks status`
     - `agent feature check-prerequisites`, `agent feature setup-plan`
  2. Add `--context` parameter (type: `Optional[str]`, default: `None`) to each
  3. Add middleware callback that processes `--context` before command body runs
  4. When `--context` is provided, the command uses `load_context()` instead of any other resolution
  5. When `--context` is not provided, fall back to fail-fast error (after T009/T010 remove old detection)
- **Files**: Multiple CLI command files under `src/specify_cli/cli/commands/` (~15 files, 2-5 lines each)
- **Parallel?**: Yes — can proceed alongside T007

### Subtask T009 – Delete `feature_detection.py`

- **Purpose**: Remove the entire 668-line heuristic detection module.
- **Steps**:
  1. Delete `src/specify_cli/core/feature_detection.py`
  2. Delete `tests/specify_cli/core/test_feature_detection.py` (if exists)
  3. Remove from `src/specify_cli/core/__init__.py` exports (if any)
  4. This will cause import errors in many files — T010 fixes those
- **Files**: `src/specify_cli/core/feature_detection.py` (delete, 668 lines)
- **Notes**: Do NOT try to fix callers in this subtask. T010 handles that. Delete the file, note all broken imports for T010.

### Subtask T010 – Update all callers of detect_feature()

- **Purpose**: Replace every usage of the deleted detection module with context middleware.
- **Steps**:
  1. Search entire codebase for these patterns:
     - `from specify_cli.core.feature_detection import`
     - `from specify_cli.core import feature_detection`
     - `detect_feature(`
     - `FeatureContext`
     - `_resolve_numeric_feature_slug`
     - `_detect_from_git_branch`
     - `_detect_from_cwd`
     - `is_feature_complete`
     - `get_feature_target_branch`
     - `SPECIFY_FEATURE` env var usage
  2. For each caller:
     - If the command now has `--context` (from T008): use `get_context(ctx)` from middleware
     - If the code needs feature_slug but not a full WP context: read from `meta.json` directly
     - If the code uses `is_feature_complete()`: replace with event log query via status/reducer
  3. Verify: `grep -r "feature_detection\|detect_feature\|FeatureContext" src/` returns zero results
  4. Verify: all imports are clean, no `ImportError` at module load time
- **Files**: ~15-20 files across `src/specify_cli/cli/commands/` and `src/specify_cli/core/`
- **Notes**: This is the most labor-intensive subtask. Be thorough. Every missed caller is a runtime crash.

### Subtask T011 – Tests for context CLI integration

- **Purpose**: Verify end-to-end flow: resolve → show → use token in workflow commands.
- **Steps**:
  1. Create `tests/specify_cli/cli/commands/test_context.py`
  2. Test `resolve` command: creates token, returns valid JSON, token file exists
  3. Test `show` command: loads and displays correct bound fields
  4. Test workflow command with `--context`: verify context is loaded, no detection triggered
  5. Test workflow command without `--context`: verify fail-fast error
  6. Test with invalid token: verify clear error message
  7. Use `typer.testing.CliRunner` for CLI tests
- **Files**: `tests/specify_cli/cli/commands/test_context.py` (new, ~100 lines)
- **Parallel?**: Yes — can proceed alongside T007-T010

## Risks & Mitigations

- **Missing callers**: The biggest risk. Use `grep -rn` exhaustively and also run the full test suite to catch runtime ImportErrors.
- **Breaking existing tests**: Many existing tests use `detect_feature()` or mock it. Update or delete those test fixtures.
- **Gradual migration**: Consider leaving `detect_feature()` as a thin wrapper that raises DeprecationError during development, then delete in a final pass.

## Review Guidance

- Run `grep -r "feature_detection\|detect_feature\|FeatureContext" src/` — must return zero results
- Run `grep -r "SPECIFY_FEATURE" src/` — must return zero results (except in migration code)
- Run full test suite — no ImportErrors
- Verify `--context` parameter exists on every workflow command

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.

# Quickstart: Runtime Recovery And Audit Safety

**Mission**: 067-runtime-recovery-and-audit-safety
**Date**: 2026-04-06

## Getting Started

### Prerequisites

```bash
# Ensure spec-kitty is installed and up to date
pipx install --force --pip-args="--pre" spec-kitty-cli

# Verify version
spec-kitty --version  # Should be 3.1.0a6+

# Run tests to confirm baseline
cd /private/tmp/betterify/spec-kitty
pytest tests/ -x -q
```

### Execution Order

Start with WP05 (lowest risk, highest impact), then work in parallel:

```
1. WP05 — Wire existing progress module (~1 day)
2. WP03 + WP01 — Shim removal + merge recovery (parallel, ~2 days each)
3. WP02 — Implementation recovery (~2 days, after WP01)
4. WP04a + WP04b — Audit scope + occurrence classification (parallel, ~1 day each)
```

### Per-WP Quickstart

#### WP05: Canonical Progress Reporting

**Start here** — entry point files and what to change:

1. Read the correct module: `src/specify_cli/status/progress.py:81-162`
2. Read one broken callsite: `src/specify_cli/agent_utils/status.py:132-138`
3. Pattern: replace `done_count / total * 100` with `compute_weighted_progress(snapshot).percentage`
4. Scanner fix: `src/specify_cli/dashboard/scanner.py` — call `compute_weighted_progress()` and add `weighted_percentage` to the emitted JSON
5. Dashboard JS: `src/specify_cli/dashboard/static/dashboard/dashboard.js:319,401` — read `weighted_percentage` from data instead of computing from raw counts
6. Run existing tests: `pytest tests/specify_cli/status/test_progress.py -v`

#### WP03: Canonical Execution Surface Cleanup

**Key files to read first**:

1. Current shim generation: `src/specify_cli/shims/generator.py:53-77`
2. Shim registry (reference): `src/specify_cli/shims/registry.py:58-85`
3. Rewrite function: `src/specify_cli/migration/rewrite_shims.py:149-252`
4. ActionName definition: `src/specify_cli/core/execution_context.py:21-28`

**Change sequence**:
1. Rewrite `generate_shim_content()` to emit direct CLI commands
2. Add `"accept"` to `ActionName` Literal
3. Delete `src/specify_cli/shims/entrypoints.py`
4. Delete `src/specify_cli/cli/commands/shim.py`
5. Remove shim CLI registration from `src/specify_cli/cli/commands/agent/__init__.py:24`
6. Update `rewrite_agent_shims()` to use new generator
7. Write migration to rewrite all existing agent files
8. Test: check `.claude/commands/spec-kitty.implement.md` contains direct command

#### WP01: Merge Interruption and Recovery

**Key files to read first**:

1. MergeState: `src/specify_cli/merge/state.py:66-121`
2. CLI merge command: `src/specify_cli/cli/commands/merge.py:237-444`
3. Mark done function: `src/specify_cli/cli/commands/merge.py:28-117`
4. Cleanup function: `src/specify_cli/merge/workspace.py:68-96`

**Change sequence**:
1. In `_run_lane_based_merge()`: create or load MergeState at function entry (note: this function currently has ZERO MergeState usage — all state management must be added). If loaded state has `completed_wps`, skip those WPs.
2. Before each WP merge: set `current_wp` and save state. After each WP merge+done: add to `completed_wps` and save state.
3. Call `clear_state()` only after ALL merges complete AND cleanup succeeds.
4. In `cleanup_merge_workspace()` at `merge/workspace.py:68-96`: replace `shutil.rmtree(runtime_dir)` with selective deletion that removes the worktree and temp files but **exempts state.json**. The state file must survive cleanup so recovery can consult it on re-entry.
5. In `_mark_wp_merged_done()`: add event_id dedup check before emitting
6. Re-enable resume path: replace error message at line 359-361
7. Add macOS FSEvents delay in worktree removal loop

#### WP02: Implementation Crash Recovery

**Key files to read first**:

1. Workspace context: `src/specify_cli/workspace_context.py:36-87,345-362`
2. Implement command: `src/specify_cli/cli/commands/implement.py`
3. Worktree allocator: `src/specify_cli/lanes/worktree_allocator.py:105-153`
4. Implement support: `src/specify_cli/lanes/implement_support.py:76-95`

**Change sequence**:
1. Add `--recover` flag to implement command
2. Build recovery scan: list branches, match workspace contexts, check status events
3. Handle branch-exists case: use `git worktree add <path> <existing-branch>` (no `-b`)
4. Reconcile workspace context: create/update context files to match reality
5. Emit missing status transitions based on branch state

#### WP04a: Audit-Mode WP Scope

**Key files to read first**:

1. Frontmatter fields: `src/specify_cli/frontmatter.py:41-58`
2. Ownership validation: `src/specify_cli/ownership/validation.py:81-200`
3. Ownership models: `src/specify_cli/ownership/models.py:14-23`

**Change sequence**:
1. Add `"scope"` to `WP_FIELD_ORDER` in frontmatter.py
2. In `validate_no_overlap()`: skip WPs with `scope: codebase-wide`
3. In `validate_authoritative_surface()`: skip WPs with `scope: codebase-wide`
4. Define audit template target paths (constants or config)
5. Add finalize-time validation for template/doc coverage

#### WP04b: Occurrence Classification

**Key files to read first**:

1. Text replacement: `src/specify_cli/upgrade/skill_update.py:117-142`
2. Mission templates: `src/specify_cli/missions/software-dev/command-templates/`

**Change sequence**:
1. Add classification template step to relevant mission command templates
2. Add post-edit verification template step
3. Optionally add `context_filter` parameter to `apply_text_replacements()`

### Testing

```bash
# Run all tests
pytest tests/ -x -q

# Run specific WP-related tests
pytest tests/specify_cli/status/test_progress.py -v           # WP05
pytest tests/specify_cli/shims/ -v                             # WP03
pytest tests/specify_cli/merge/ -v                             # WP01
pytest tests/runtime/test_workspace_context_unit.py -v         # WP02
pytest tests/specify_cli/ownership/ -v                         # WP04a

# Type checking
mypy src/specify_cli/ --strict
```

---
work_package_id: WP00
title: Call-Site Reroute
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
history:
- date: '2026-04-13'
  author: claude
  action: created
  note: Initial WP generation from /spec-kitty.tasks
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- src/specify_cli/next/prompt_builder.py
- src/specify_cli/cli/commands/agent/workflow.py
- tests/specify_cli/next/test_prompt_builder_reroute.py
- tests/specify_cli/cli/commands/agent/test_workflow_reroute.py
tags: []
---

# WP00: Call-Site Reroute

## Objective

Reroute all `build_charter_context()` callers from the legacy `specify_cli.charter.context` module to the canonical `charter.context` module. After this WP, `src/specify_cli/charter/context.py` has zero internal callers, establishing a single oracle for the invariant test in WP04.

## Context

Two of three callers still import from the old path:
- `src/specify_cli/next/prompt_builder.py:13` -- imports `build_charter_context` from `specify_cli.charter.context`
- `src/specify_cli/cli/commands/agent/workflow.py:20` -- imports `build_charter_context` from `specify_cli.charter.context`

One caller already uses the canonical path:
- `src/specify_cli/cli/commands/charter.py:13` -- imports from `charter.context`

The canonical `src/charter/context.py` has a `depth` parameter and action-scoped doctrine loading. The legacy `src/specify_cli/charter/context.py` does not. The reroute may change behavior if the two implementations have diverged. This must be detected and resolved, not papered over.

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- Execution worktrees allocated per computed lane from `lanes.json`.

## Detailed Guidance

### T001: Reroute `prompt_builder.py` import

**Purpose**: Change the import in `src/specify_cli/next/prompt_builder.py` from the legacy to the canonical module.

**Steps**:
1. Open `src/specify_cli/next/prompt_builder.py`
2. Find line 13: `from specify_cli.charter.context import build_charter_context`
3. Replace with: `from charter.context import build_charter_context`
4. If any other symbols are imported from `specify_cli.charter.context`, reroute those too
5. Verify the module resolves correctly by running the existing tests:
   ```bash
   pytest tests/specify_cli/next/ -x -q
   ```

**Files**: `src/specify_cli/next/prompt_builder.py`

**Validation**:
- [ ] Import path changed to `charter.context`
- [ ] No `ImportError` when module is loaded
- [ ] Existing prompt builder tests pass

### T002: Reroute `agent/workflow.py` import

**Purpose**: Change the import in `src/specify_cli/cli/commands/agent/workflow.py` from the legacy to the canonical module.

**Steps**:
1. Open `src/specify_cli/cli/commands/agent/workflow.py`
2. Find line 20: `from specify_cli.charter.context import build_charter_context`
3. Replace with: `from charter.context import build_charter_context`
4. Check for any other imports from `specify_cli.charter.context` and reroute them
5. Run relevant tests:
   ```bash
   pytest tests/specify_cli/cli/commands/agent/ -x -q
   ```

**Files**: `src/specify_cli/cli/commands/agent/workflow.py`

**Validation**:
- [ ] Import path changed to `charter.context`
- [ ] No `ImportError` when module is loaded
- [ ] Existing workflow tests pass

### T003: Before/after output comparison

**Purpose**: Prove the reroute does not change runtime behavior. If the two implementations have diverged, this test will catch it.

**Steps**:
1. Create a test file `tests/specify_cli/next/test_prompt_builder_reroute.py`
2. For each bootstrap action (`specify`, `plan`, `implement`, `review`):
   a. Call the old `specify_cli.charter.context.build_charter_context(repo_root, action=action)` 
   b. Call the new `charter.context.build_charter_context(repo_root, action=action)`
   c. Assert the `text` field of both results is identical
   d. Assert the `mode` field is identical
   e. Assert the `references_count` is identical
3. If any assertion fails, this means the implementations have diverged. **Do not proceed to WP04.** Instead:
   - Document the exact divergence (which action, which fields differ)
   - File it as a blocking issue
   - The divergence must be resolved before the invariant test can use a single oracle

**Files**: `tests/specify_cli/next/test_prompt_builder_reroute.py`

**Validation**:
- [ ] Output comparison test exists and passes for all 4 bootstrap actions
- [ ] If divergence found, it is documented and blocks WP04

### T004: Assert zero remaining references

**Purpose**: Confirm no callers in `src/` still reference the old module.

**Steps**:
1. Add a test (can be in the same file or a new one) that runs:
   ```python
   import subprocess
   result = subprocess.run(
       ["grep", "-r", "specify_cli.charter.context", "src/"],
       capture_output=True, text=True
   )
   assert result.stdout.strip() == "", f"Stale references found:\n{result.stdout}"
   ```
2. Alternatively, use a simpler assertion by scanning Python files with `ast` or `pathlib`
3. The legacy module itself (`src/specify_cli/charter/context.py`) still exists -- that's fine. We're asserting no other file in `src/` imports from it.

**Files**: Test file from T003 (extend it)

**Validation**:
- [ ] grep returns zero matches for `specify_cli.charter.context` in `src/` (excluding the module itself)
- [ ] Test is part of the test suite

## Definition of Done

1. Both import paths changed to `charter.context`
2. Before/after comparison proves identical output for all 4 bootstrap actions
3. Zero remaining callers of `specify_cli.charter.context` in `src/`
4. All existing tests pass (no regressions)
5. mypy --strict passes

## Risks

- **Divergence discovered**: If the two implementations produce different output, this WP becomes a debugging task. The fix is to align them (typically by fixing the legacy one to match canonical, or vice versa), not to skip the comparison.
- **Hidden callers**: There may be dynamic imports or string-based references. The grep test catches string-based references; dynamic imports would need manual audit.

## Reviewer Guidance

- Verify the import paths are correct (not typos like `chater.context`)
- Verify the before/after test covers all 4 actions, not just one
- If divergence is found, verify it's documented as a blocker, not silently accepted

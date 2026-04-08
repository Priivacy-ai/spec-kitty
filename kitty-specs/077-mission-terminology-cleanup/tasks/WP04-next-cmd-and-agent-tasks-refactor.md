---
work_package_id: WP04
title: next_cmd.py and agent/tasks.py Selector Refactor
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-005
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
mission_slug: 077-mission-terminology-cleanup
owned_files:
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/cli/commands/test_next_cmd_selectors.py
- tests/specify_cli/cli/commands/test_agent_tasks_selectors.py
priority: P0
tags: []
---

# WP04 — `next_cmd.py` and `agent/tasks.py` Selector Refactor

## Objective

Refactor every tracked-mission selector site in `src/specify_cli/cli/commands/next_cmd.py` and `src/specify_cli/cli/commands/agent/tasks.py` to use `--mission` as canonical, drop `--mission-run` from tracked-mission alias lists entirely, add hidden `--feature` aliases routed through `resolve_selector`, and update help strings from "Mission run slug" to "Mission slug".

This is the **bulk** of the operator-facing drift. WP01's audit identifies the precise per-site target shapes; this WP applies them.

## Context

The verified-known sites at HEAD `35d43a25`:

**`src/specify_cli/cli/commands/next_cmd.py`**:
- Line 33: `feature: Annotated[str | None, typer.Option("--mission", "--mission-run", "--feature", help="Mission slug")] = None`
- Line 48: example help text uses `spec-kitty next --agent codex --mission-run 034-my-feature`
- Line 61: calls `require_explicit_feature(feature, command_hint="--mission <slug>")`

**`src/specify_cli/cli/commands/agent/tasks.py`** (9 sites — every one declares `typer.Option("--mission", "--mission-run", help="Mission run slug")`):
- Line 842
- Line 1389
- Line 1572
- Line 1655
- Line 1726
- Line 1945 (uses Argument-style: `typer.Option("--mission", "--mission-run", help="Mission run slug")` inside an `Annotated`)
- Line 2205
- Line 2295 (also has `-f` short flag)
- Line 2659

Each site needs the same shape transformation. This is tedious mechanical work but each site is similar enough that one focused pass handles them all.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP04` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T015 — Refactor `next_cmd.py:33` [P]

**Purpose**: Apply the WP03 pattern to `next_cmd.py`'s tracked-mission selector.

**Steps**:
1. Open `src/specify_cli/cli/commands/next_cmd.py` and locate the `next_cmd` function (around line 24+).
2. Replace the parameter declaration:

   **Before**:
   ```python
   feature: Annotated[str | None, typer.Option("--mission", "--mission-run", "--feature", help="Mission slug")] = None,
   ```

   **After**:
   ```python
   mission: Annotated[
       str | None,
       typer.Option("--mission", help="Mission slug"),
   ] = None,
   feature: Annotated[
       str | None,
       typer.Option("--feature", hidden=True, help="(deprecated) Use --mission"),
   ] = None,
   ```

   Note: `--mission-run` is **dropped entirely** from tracked-mission selector aliases. It is reserved for runtime/session use only (FR-002, FR-003).

3. In the function body, find where `feature` is used (around line 61: `mission_slug = require_explicit_feature(feature, command_hint="--mission <slug>")`) and replace:

   **Before**:
   ```python
   mission_slug = require_explicit_feature(feature, command_hint="--mission <slug>")
   ```

   **After**:
   ```python
   from specify_cli.cli.selector_resolution import (
       resolve_selector,
       ENV_VAR_SUPPRESS_FEATURE_DEPRECATION,
   )

   resolved = resolve_selector(
       canonical_value=mission,
       canonical_flag="--mission",
       alias_value=feature,
       alias_flag="--feature",
       suppress_env_var=ENV_VAR_SUPPRESS_FEATURE_DEPRECATION,
       command_hint="--mission <slug>",
   )
   mission_slug = resolved.canonical_value
   ```

4. Verify the import is at the top of the file, not inside the function.

### T016 — Update `next_cmd.py:48` example help text [P]

**Purpose**: The function docstring (around line 48) shows an example invocation with `--mission-run`. Update it to canonical `--mission`.

**Steps**:
1. Find the docstring example:
   ```python
   """
   ...
       spec-kitty next --agent codex --mission-run 034-my-feature
   ...
   """
   ```
2. Replace with:
   ```python
   """
   ...
       spec-kitty next --agent codex --mission 034-my-feature
   ...
   """
   ```
3. If there are other example invocations in the docstring that mention `--mission-run` or `--feature` for tracked-mission selection, update them too. Leave any genuine runtime/session examples alone.

### T017 — Refactor `agent/tasks.py` 9 selector sites

**Purpose**: Apply the same shape transformation to all 9 sites in `agent/tasks.py`.

**Steps**:
1. Open `src/specify_cli/cli/commands/agent/tasks.py`.
2. For each of the 9 sites at lines 842, 1389, 1572, 1655, 1726, 1945, 2205, 2295, 2659:
   - Locate the parameter declaration: `feature: Annotated[str | None, typer.Option("--mission", "--mission-run", help="Mission run slug")] = None,`
   - Replace with two separate parameters:
     ```python
     mission: Annotated[
         str | None,
         typer.Option("--mission", help="Mission slug"),
     ] = None,
     feature: Annotated[
         str | None,
         typer.Option("--feature", hidden=True, help="(deprecated) Use --mission"),
     ] = None,
     ```
   - In the function body, find where `feature` is used and replace with the `resolve_selector` pattern from T015.

3. **Special case at line 2295**: this site has `-f` as a short flag:
   ```python
   feature: Annotated[str | None, typer.Option("--mission", "--mission-run", "-f", help="Mission run slug")] = None,
   ```
   The `-f` short flag goes on the canonical `--mission` parameter, not on `--feature`:
   ```python
   mission: Annotated[
       str | None,
       typer.Option("--mission", "-f", help="Mission slug"),
   ] = None,
   ```

4. **Special case at line 1945**: this site has the `Option` wrapped slightly differently. Read it carefully and apply the same transformation.

5. Add the import once at the top of `agent/tasks.py` (or verify it's already there from another WP):
   ```python
   from specify_cli.cli.selector_resolution import (
       resolve_selector,
       ENV_VAR_SUPPRESS_FEATURE_DEPRECATION,
   )
   ```

6. **Critical**: every site must be updated. Missing one means the corresponding command still has the bug.

### T018 — Replace "Mission run slug" help text

**Purpose**: After the parameter refactor, no help string in these files should say "Mission run slug" for tracked-mission selectors.

**Steps**:
1. After T015-T017 are done, grep the modified files:
   ```bash
   grep -n "Mission run slug" src/specify_cli/cli/commands/next_cmd.py src/specify_cli/cli/commands/agent/tasks.py
   ```
2. Expected result: zero matches. The refactor in T015-T017 already replaces them with `"Mission slug"` on the canonical parameter.
3. If any remain, fix them.

### T019 — Add integration tests for representative commands

**Purpose**: Cover the canonical/alias/conflict cases for at least one command from each file via `typer.testing.CliRunner`.

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_next_cmd_selectors.py` with 5 tests:
   - canonical succeeds
   - alias `--feature` succeeds with warning
   - dual-flag conflict fails (regression)
   - same-value compat succeeds with warning
   - `--help` does not show `--feature`

   Pattern:
   ```python
   import pytest
   from typer.testing import CliRunner
   from specify_cli.cli.commands.next_cmd import next_cmd  # or whatever the app symbol is
   from specify_cli.cli import selector_resolution

   @pytest.fixture(autouse=True)
   def _reset_warned():
       selector_resolution._warned.clear()
       yield
       selector_resolution._warned.clear()

   runner = CliRunner(mix_stderr=False)

   def test_next_cmd_canonical_succeeds():
       # ... invoke `next` with --mission, assert exit 0, no warning
       ...

   def test_next_cmd_alias_with_warning():
       # ... invoke with --feature, assert exit 0, warning on stderr
       ...

   def test_next_cmd_dual_flag_conflict_fails():
       # ... invoke with --mission A --feature B, assert exit non-zero, conflict message
       ...
   ```

2. Create `tests/specify_cli/cli/commands/test_agent_tasks_selectors.py` with **3 representative tests** (canonical / alias / conflict) for at least one command from `agent/tasks.py`. Pick the most-used command (likely the one at line 842 or 2295). Three tests per representative command is enough — the unit tests in WP02 already cover the helper logic exhaustively, so per-command integration tests just confirm wiring.

3. Run the new tests:
   ```bash
   PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/test_next_cmd_selectors.py tests/specify_cli/cli/commands/test_agent_tasks_selectors.py
   ```

## Files Touched

| File | Action | Notes |
|---|---|---|
| `src/specify_cli/cli/commands/next_cmd.py` | MODIFY | 1 selector site + 1 help-text example |
| `src/specify_cli/cli/commands/agent/tasks.py` | MODIFY | 9 selector sites |
| `tests/specify_cli/cli/commands/test_next_cmd_selectors.py` | CREATE | 5 integration tests |
| `tests/specify_cli/cli/commands/test_agent_tasks_selectors.py` | CREATE | 3 integration tests |

## Definition of Done

- [ ] `next_cmd.py:33` declares `--mission` and `--feature` as two separate parameters; `--mission-run` is gone
- [ ] `next_cmd.py:48` example uses `--mission`, not `--mission-run`
- [ ] All 9 sites in `agent/tasks.py` declare two separate parameters; `--mission-run` is gone from tracked-mission alias lists
- [ ] `-f` short flag at `agent/tasks.py:2295` is on `--mission`, not `--feature`
- [ ] `grep "Mission run slug"` returns zero matches in both files
- [ ] All function bodies that previously called `require_explicit_feature(feature, ...)` directly now call `resolve_selector(...)` first and pass the resolved value to `require_explicit_feature` (or use `resolved.canonical_value` directly if `resolve_selector` already raises on missing values)
- [ ] All 8 new integration tests pass
- [ ] mypy --strict is clean on both modified files
- [ ] No other files in `src/specify_cli/cli/commands/` are touched (those are owned by other WPs)

## Risks and Reviewer Guidance

**Risks**:
- Missing one of the 9 sites in `agent/tasks.py` is the most likely failure mode. Use the WP01 audit as the authoritative checklist; tick each line number off as you refactor it.
- The `Annotated[...]` wrapping in some sites is slightly different (with vs. without `Annotated`, with or without `-f` short flag). Read each site carefully before applying the pattern blindly.
- Some commands in `agent/tasks.py` may have additional logic that depends on the parameter being named `feature`. After renaming the canonical parameter, search the function body for `feature` and update.

**Reviewer checklist**:
- [ ] All 9 site line numbers from spec §8.1.1 are verified refactored
- [ ] No `--mission-run` appears in tracked-mission alias lists in either file
- [ ] No "Mission run slug" help text remains
- [ ] `-f` short flag at line 2295 is on `--mission`
- [ ] WP01 audit document is consulted to confirm the site list is complete
- [ ] Imports of `resolve_selector` are at the top of each file, not inside functions

## Implementation Command

```bash
spec-kitty implement WP04
```

This WP depends on WP02. Wait for WP02 to be merged. WP04 can run in parallel with WP03 and WP05 (different files, no shared ownership).

## References

- Spec §8.1.1 — Verified tracked-mission drift sites
- Spec FR-001, FR-002, FR-003, FR-005, FR-008
- WP01 audit document (`research/selector-audit.md`)
- `contracts/selector_resolver.md` §"Tracked-Mission Command"
- `quickstart.md` Step 4 — bulk refactor walkthrough

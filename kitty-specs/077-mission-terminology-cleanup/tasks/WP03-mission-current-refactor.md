---
work_package_id: WP03
title: mission current Refactor and Dual-Flag Bug Fix
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-005
- FR-006
- FR-008
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Lane workspace per execution lane (resolved by spec-kitty implement WP03)
subtasks:
- T011
- T012
- T013
- T014
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: src/specify_cli/cli/commands/mission.py
execution_mode: code_change
mission_slug: 077-mission-terminology-cleanup
owned_files:
- src/specify_cli/cli/commands/mission.py
- tests/specify_cli/cli/commands/test_mission_current.py
priority: P0
tags: []
---

# WP03 — `mission current` Refactor and Dual-Flag Bug Fix

## Objective

Fix the **verified dual-flag bug** in `mission current` (spec §8.2). Refactor `src/specify_cli/cli/commands/mission.py:172-194` to declare `--mission` and `--feature` as **two separate typer parameters** and route them through `resolve_selector` from WP02. This is the canonical end-to-end demonstration of the new pattern.

This WP exists as its own focused unit because:
1. It fixes the most-cited regression bug in the mission's spec (`mission current --mission A --feature B` silently resolves to B).
2. It's the smallest possible end-to-end demonstration that the helper works in production code.
3. The `mission current` integration tests serve as the regression test for FR-006.

## Context

The current implementation at `src/specify_cli/cli/commands/mission.py:172-194` is:

```python
@app.command("current")
def current_cmd(
    feature: str | None = typer.Option(
        None,
        "--mission",
        "--feature",
        "-f",
        help="Mission slug",
    ),
) -> None:
    """Show the active mission type for a mission (auto-detects mission from cwd)."""
    project_root = get_project_root_or_exit()
    check_version_compatibility(project_root, "mission")

    # Detect feature if not explicitly provided
    mission_slug = feature if feature else _detect_current_feature(project_root)

    if not mission_slug:
        # ... error path with available missions list ...
```

The bug: typer collapses the three-alias declaration into a single `feature` parameter with last-value-wins resolution. Passing `mission current --mission A --feature B` silently resolves `feature` to `"B"` (the second value typer saw). No conflict is raised. The user gets a different mission than they asked for.

The fix: split into two separate parameters and reconcile via `resolve_selector`.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP03` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T011 — Refactor `mission.py:172-194` to use two separate parameters

**Purpose**: Replace the multi-alias `Option` with two separate parameters.

**Steps**:
1. Open `src/specify_cli/cli/commands/mission.py`.
2. Locate the `current_cmd` function (around line 172).
3. Replace the parameter declaration:

   **Before**:
   ```python
   @app.command("current")
   def current_cmd(
       feature: str | None = typer.Option(
           None,
           "--mission",
           "--feature",
           "-f",
           help="Mission slug",
       ),
   ) -> None:
   ```

   **After**:
   ```python
   from typing import Annotated
   from specify_cli.cli.selector_resolution import (
       resolve_selector,
       ENV_VAR_SUPPRESS_FEATURE_DEPRECATION,
   )

   @app.command("current")
   def current_cmd(
       mission: Annotated[
           str | None,
           typer.Option(
               "--mission",
               "-f",
               help="Mission slug",
           ),
       ] = None,
       feature: Annotated[
           str | None,
           typer.Option(
               "--feature",
               hidden=True,
               help="(deprecated) Use --mission",
           ),
       ] = None,
   ) -> None:
   ```

4. **Critical decisions**:
   - The canonical parameter is now named `mission` (not `feature`). Update the function body to use `mission_slug` resolved from this parameter.
   - The `-f` short flag stays on `--mission` (the canonical flag), not on `--feature`. Existing scripts that use `-f` for `--mission` will continue to work.
   - The `hidden=True` on the alias parameter is the **charter compliance switch**. Without it, the grep guard in WP09 (Guard 3) will fail the build.

### T012 — Wire `mission current` through `resolve_selector`

**Purpose**: Replace the function body's parameter handling with a call to the helper.

**Steps**:
1. After the parameter refactor, replace the `mission_slug = feature if feature else _detect_current_feature(project_root)` line with:

   ```python
   def current_cmd(
       mission: ...,
       feature: ...,
   ) -> None:
       """Show the active mission type for a mission."""
       project_root = get_project_root_or_exit()
       check_version_compatibility(project_root, "mission")

       # Resolve --mission / --feature into the canonical mission slug.
       # Raises typer.BadParameter on dual-flag conflict (FR-006).
       # Emits a deprecation warning if --feature was used (FR-005).
       try:
           resolved = resolve_selector(
               canonical_value=mission,
               canonical_flag="--mission",
               alias_value=feature,
               alias_flag="--feature",
               suppress_env_var=ENV_VAR_SUPPRESS_FEATURE_DEPRECATION,
               command_hint="--mission <slug>",
           )
           mission_slug: str | None = resolved.canonical_value
       except typer.BadParameter:
           # Helper handles the missing-value case via require_explicit_feature.
           # If neither value was provided, fall through to the auto-detect path
           # below for backward-compat with the old behavior of detecting from cwd.
           mission_slug = _detect_current_feature(project_root)

       if not mission_slug:
           console.print(
               "[yellow]No active mission detected.[/yellow]\n"
               "\nUse [cyan]--mission <slug>[/cyan] to specify one, "
               "or run from within a mission worktree."
           )
           # ... existing list-available-missions fallback ...
   ```

2. **Subtle point**: the original `current_cmd` had a fallback to `_detect_current_feature(project_root)` (which always returns None per the function definition). The helper's behavior on "both empty" is to call `require_explicit_feature` which raises. The wrapper catches that and falls through to the existing list-available-missions UX. Preserve that UX exactly.

3. Update the help text "[yellow]No active feature detected" → "[yellow]No active mission detected" to match canonical terminology (FR-008 spirit).

### T013 — Add 6 integration tests for `mission current`

**Purpose**: Cover all canonical/alias/conflict cases for the `mission current` command via real `typer.testing.CliRunner` invocations. **One of these tests is the regression test for the verified bug.**

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_mission_current.py` (new file):

   ```python
   """Integration tests for `spec-kitty mission current` selector handling.

   See kitty-specs/077-mission-terminology-cleanup/spec.md §10.1 acceptance gate 3.
   """
   import pytest
   from typer.testing import CliRunner

   from specify_cli.cli.commands.mission import app
   from specify_cli.cli import selector_resolution


   @pytest.fixture(autouse=True)
   def _reset_warned():
       selector_resolution._warned.clear()
       yield
       selector_resolution._warned.clear()


   runner = CliRunner(mix_stderr=False)


   def test_mission_current_canonical_succeeds(tmp_repo_with_mission):
       result = runner.invoke(app, ["current", "--mission", "077-mission-terminology-cleanup"])
       assert result.exit_code == 0
       assert "Warning" not in result.stderr


   def test_mission_current_alias_succeeds_with_warning(tmp_repo_with_mission):
       result = runner.invoke(app, ["current", "--feature", "077-mission-terminology-cleanup"])
       assert result.exit_code == 0
       assert "Warning:" in result.stderr
       assert "--feature is deprecated" in result.stderr
       assert "--mission" in result.stderr


   def test_mission_current_dual_flag_conflict_fails(tmp_repo_with_mission):
       """Regression test for the verified dual-flag bug (spec §8.2)."""
       result = runner.invoke(app, [
           "current",
           "--mission", "077-mission-A",
           "--feature", "077-mission-B",
       ])
       assert result.exit_code != 0
       assert "077-mission-A" in (result.stderr + result.output)
       assert "077-mission-B" in (result.stderr + result.output)
       assert "Conflicting" in (result.stderr + result.output)


   def test_mission_current_same_value_with_warning(tmp_repo_with_mission):
       result = runner.invoke(app, [
           "current",
           "--mission", "077-mission-terminology-cleanup",
           "--feature", "077-mission-terminology-cleanup",
       ])
       assert result.exit_code == 0
       assert "Warning:" in result.stderr


   def test_mission_current_suppression_env_var(tmp_repo_with_mission, monkeypatch):
       monkeypatch.setenv("SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION", "1")
       result = runner.invoke(app, ["current", "--feature", "077-mission-terminology-cleanup"])
       assert result.exit_code == 0
       assert "Warning" not in result.stderr


   def test_mission_current_help_does_not_mention_feature():
       """The hidden alias must not appear in --help output."""
       result = runner.invoke(app, ["current", "--help"])
       assert result.exit_code == 0
       assert "--feature" not in result.output
       assert "--mission" in result.output
   ```

2. Use the existing `tmp_repo_with_mission` fixture if it exists in `tests/conftest.py`. If not, create a small fixture that sets up a temp project with one mission directory.

3. The third test (`test_mission_current_dual_flag_conflict_fails`) **is** the regression test for the bug. It must fail before WP03 lands and pass after.

### T014 — Manually reproduce verified dual-flag bug → confirm fixed

**Purpose**: End-to-end smoke test that the verified bug (spec §8.2) is fixed in the actual built CLI.

**Steps**:
1. After T011-T013 are done and tests pass, run the manual repro from `quickstart.md` Step 13:

   ```bash
   uv run spec-kitty mission current --mission 077-mission-terminology-cleanup --feature 047-namespace-aware-artifact-body-sync
   ```

2. **Expected output** (post-fix):
   - Exit code: non-zero
   - Stderr contains: `Conflicting selectors: --mission='077-mission-terminology-cleanup' and --feature='047-namespace-aware-artifact-body-sync' were both provided with different values. --feature is a hidden deprecated alias for --mission; pass only --mission.`

3. Run the canonical and alias variants too:
   ```bash
   uv run spec-kitty mission current --mission 077-mission-terminology-cleanup
   # Expected: succeeds, no warning

   uv run spec-kitty mission current --feature 077-mission-terminology-cleanup
   # Expected: succeeds, one yellow Warning line on stderr
   ```

4. Verify that `--feature` is hidden from help:
   ```bash
   uv run spec-kitty mission current --help | grep -- '--feature'
   # Expected: empty
   ```

5. Capture the manual repro output in the WP completion notes for the WP10 acceptance evidence.

## Files Touched

| File | Action | Notes |
|---|---|---|
| `src/specify_cli/cli/commands/mission.py` | MODIFY | Only the `current_cmd` function (around lines 172-205). Other commands in this file are not touched. |
| `tests/specify_cli/cli/commands/test_mission_current.py` | CREATE | 6 integration tests |

**Out of bounds**:
- The `switch` command at `mission.py:273` already has `deprecated=True`. Do not touch it.
- The `_detect_current_feature` helper at line 160 always returns None. Leave it; it's used by the fallback path.
- Other typer commands in this file (e.g. `mission list`) are not in scope for WP03; if they have selector drift, they're handled by WP04 or WP05.

## Definition of Done

- [ ] `mission.py:172-194` declares `--mission` and `--feature` as two separate typer parameters
- [ ] `--feature` parameter has `hidden=True`
- [ ] `current_cmd` body calls `resolve_selector` from WP02
- [ ] All 6 integration tests in `test_mission_current.py` pass
- [ ] Manual repro of `--mission A --feature B` exits non-zero with conflict error
- [ ] Manual repro of `--feature X` shows exactly one yellow stderr Warning line
- [ ] Manual repro of `--feature X` with `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION=1` shows no warning
- [ ] `mission current --help` does not mention `--feature`
- [ ] mypy --strict is clean on the modified file
- [ ] No other commands in `mission.py` are touched

## Risks and Reviewer Guidance

**Risks**:
- The original parameter was named `feature`. Renaming it to `mission` requires updating every reference inside `current_cmd`. Use the IDE's find-in-function-scope rather than global rename to avoid touching other commands.
- The fallback path (`_detect_current_feature` returns None → list available missions) must be preserved. Don't accidentally change the UX when no value is provided.
- The `-f` short flag was originally on the multi-alias `Option`. After the split, it goes on the canonical `--mission` parameter, not on `--feature`. Existing user scripts that pass `-f X` will continue to work because typer treats `-f` as a synonym for `--mission`.

**Reviewer checklist**:
- [ ] Only `current_cmd` is modified in this file; other commands untouched
- [ ] `--feature` is `hidden=True`
- [ ] The function body imports `resolve_selector` and `ENV_VAR_SUPPRESS_FEATURE_DEPRECATION` from `selector_resolution`
- [ ] The conflict regression test from T013 is present and passes
- [ ] The manual repro from T014 is captured in the WP completion notes
- [ ] `-f` short flag is on `--mission`, not `--feature`

## Implementation Command

```bash
spec-kitty implement WP03
```

This WP depends on WP02. Wait for WP02 to be merged before starting.

## References

- Spec §8.2 — Verified behavior bug (the regression target)
- Spec FR-001, FR-005, FR-006, FR-008, FR-011 — what this WP must satisfy
- `contracts/selector_resolver.md` §"Tracked-Mission Command" — the call-site pattern
- `quickstart.md` Step 3 — line-by-line implementation guide
- `quickstart.md` Step 13 — manual repro commands

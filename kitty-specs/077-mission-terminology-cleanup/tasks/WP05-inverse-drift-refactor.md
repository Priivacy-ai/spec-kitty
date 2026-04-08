---
work_package_id: WP05
title: Inverse Drift Refactor (--mission → --mission-type)
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-021
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
mission_slug: 077-mission-terminology-cleanup
owned_files:
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/charter.py
- src/specify_cli/cli/commands/lifecycle.py
- tests/specify_cli/cli/commands/test_inverse_drift_selectors.py
priority: P0
tags: []
---

# WP05 — Inverse Drift Refactor (`--mission` → `--mission-type`)

## Objective

Convert the three verified inverse-drift sites where `--mission` semantically means "blueprint/template selector" so the canonical literal flag is `--mission-type`, with `--mission` retained as a hidden deprecated alias. This is FR-021 from the spec.

These sites are the **inverse** of WP03/WP04: there, `--feature` was the deprecated alias for the canonical `--mission`. Here, `--mission` is the deprecated alias for the canonical `--mission-type`.

The same `resolve_selector` helper handles both directions; the call sites just pass different `canonical_flag`/`alias_flag`/`suppress_env_var` values.

## Context

The verified inverse-drift sites at HEAD `35d43a25`:

**1. `src/specify_cli/cli/commands/agent/mission.py:488`** (`agent mission create`):
```python
mission: Annotated[str | None, typer.Option("--mission", help="Mission type (e.g., 'documentation', 'software-dev')")] = None,
```
The parameter name is `mission` but the value is a mission *type*. Default value: `None`.

**2. `src/specify_cli/cli/commands/charter.py:67`** (`charter interview`):
```python
mission: str = typer.Option("software-dev", "--mission", help="Mission key for charter defaults"),
```
**Critical**: this site has a default value of `"software-dev"`. The default must move to the canonical `--mission-type` parameter, not the alias.

**3. `src/specify_cli/cli/commands/lifecycle.py:27`** (`lifecycle.specify`):
```python
mission: Optional[str] = typer.Option(None, "--mission", help="Mission type (e.g., software-dev, research)"),
```
Default value: `None`. Note: this uses `Optional[str]` instead of `str | None` — preserve the existing style.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP05` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T020 — Refactor `agent/mission.py:488` [P]

**Purpose**: Convert `agent mission create` to use `--mission-type` as canonical.

**Steps**:
1. Open `src/specify_cli/cli/commands/agent/mission.py` and locate `create_mission` (around line 485).
2. Replace the `mission:` parameter:

   **Before**:
   ```python
   @app.command(name="create")
   def create_mission(
       mission_slug: Annotated[str, typer.Argument(help="Mission slug (e.g., 'user-auth')")],
       mission: Annotated[str | None, typer.Option("--mission", help="Mission type (e.g., 'documentation', 'software-dev')")] = None,
       json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
       target_branch: Annotated[str | None, typer.Option("--target-branch", help="Target branch (defaults to current branch)")] = None,
   ) -> None:
   ```

   **After**:
   ```python
   from specify_cli.cli.selector_resolution import (
       resolve_selector,
       ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION,
   )

   @app.command(name="create")
   def create_mission(
       mission_slug: Annotated[str, typer.Argument(help="Mission slug (e.g., 'user-auth')")],
       mission_type: Annotated[
           str | None,
           typer.Option(
               "--mission-type",
               help="Mission type (e.g., 'documentation', 'software-dev')",
           ),
       ] = None,
       mission: Annotated[
           str | None,
           typer.Option(
               "--mission",
               hidden=True,
               help="(deprecated) Use --mission-type",
           ),
       ] = None,
       json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
       target_branch: Annotated[str | None, typer.Option("--target-branch", help="Target branch (defaults to current branch)")] = None,
   ) -> None:
   ```

3. In the function body, find where `mission` is used (passed to `create_mission_core(mission=mission)`) and reconcile through the helper:

   **Before** (somewhere near the bottom of the function):
   ```python
   from specify_cli.core.mission_creation import create_mission_core
   result = create_mission_core(
       mission_slug=mission_slug,
       mission=mission,  # ← this is actually the mission type
       ...
   )
   ```

   **After**:
   ```python
   from specify_cli.core.mission_creation import create_mission_core
   resolved = resolve_selector(
       canonical_value=mission_type,
       canonical_flag="--mission-type",
       alias_value=mission,
       alias_flag="--mission",
       suppress_env_var=ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION,
       command_hint="--mission-type <name>",
   )
   resolved_mission_type = resolved.canonical_value
   result = create_mission_core(
       mission_slug=mission_slug,
       mission=resolved_mission_type,  # downstream still expects param named 'mission'
       ...
   )
   ```

4. **Important**: do not rename the parameter `mission` in `create_mission_core` — that's a downstream API change outside this WP's ownership. Just pass the resolved value to it.

### T021 — Refactor `charter.py:67` [P]

**Purpose**: Convert `charter interview` to use `--mission-type` as canonical, **preserving the default value**.

**Steps**:
1. Open `src/specify_cli/cli/commands/charter.py` and locate the `interview` function (around line 65).
2. Replace the parameter declaration:

   **Before**:
   ```python
   @app.command()
   def interview(
       mission: str = typer.Option("software-dev", "--mission", help="Mission key for charter defaults"),
       profile: str = typer.Option("minimal", "--profile", help="Interview profile: minimal or comprehensive"),
       ...
   ```

   **After**:
   ```python
   from specify_cli.cli.selector_resolution import (
       resolve_selector,
       ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION,
   )

   @app.command()
   def interview(
       mission_type: str = typer.Option("software-dev", "--mission-type", help="Mission type for charter defaults"),
       mission: str | None = typer.Option(None, "--mission", hidden=True, help="(deprecated) Use --mission-type"),
       profile: str = typer.Option("minimal", "--profile", help="Interview profile: minimal or comprehensive"),
       ...
   ```

3. **Critical decision**: the default `"software-dev"` moves from `mission` to `mission_type` (the canonical parameter). The deprecated alias `mission` defaults to `None`. This means:
   - If the user passes nothing → resolves to `"software-dev"` (preserved from original behavior)
   - If the user passes `--mission-type research` → resolves to `"research"`
   - If the user passes `--mission research` → resolves to `"research"` with deprecation warning

4. In the function body, near the top, reconcile via the helper:
   ```python
   resolved = resolve_selector(
       canonical_value=mission_type,
       canonical_flag="--mission-type",
       alias_value=mission,
       alias_flag="--mission",
       suppress_env_var=ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION,
       command_hint="--mission-type <name>",
   )
   resolved_mission_type = resolved.canonical_value
   ```

5. Replace every subsequent reference to `mission` (the old variable name) inside the function body with `resolved_mission_type`.

6. **Subtle case**: because `mission_type` has a non-None default `"software-dev"`, the helper will see `canonical_value="software-dev"` and `alias_value=None` for the no-argument case. That correctly resolves to `"software-dev"` with no warning. For the deprecated case where the user passes `--mission research`, the helper sees `canonical_value="software-dev"` (the default!) and `alias_value="research"` — this is the **conflict** case, and the helper would raise BadParameter.

   **This is wrong UX** for the default-value scenario. The fix: detect whether `mission_type` was explicitly provided vs defaulted. typer doesn't give us that directly, but we can sentinel:

   ```python
   _DEFAULT_MISSION_TYPE = "software-dev"

   def interview(
       mission_type: str = typer.Option(_DEFAULT_MISSION_TYPE, "--mission-type", help="..."),
       mission: str | None = typer.Option(None, "--mission", hidden=True, help="..."),
       ...
   ) -> None:
       # Special case: if mission_type is the default and mission is set,
       # treat as alias-only (don't conflict the default against the alias).
       if mission_type == _DEFAULT_MISSION_TYPE and mission is not None:
           resolved_mission_type = resolve_selector(
               canonical_value=None,  # treat default as "not explicitly set"
               canonical_flag="--mission-type",
               alias_value=mission,
               alias_flag="--mission",
               suppress_env_var=ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION,
               command_hint="--mission-type <name>",
           ).canonical_value
       else:
           resolved_mission_type = resolve_selector(
               canonical_value=mission_type,
               canonical_flag="--mission-type",
               alias_value=mission,
               alias_flag="--mission",
               suppress_env_var=ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION,
               command_hint="--mission-type <name>",
           ).canonical_value
   ```

   This preserves the original behavior: if the user passes only `--mission research`, it resolves to `"research"` with a warning, not a conflict error against the implicit default `"software-dev"`.

   If you find a cleaner solution (e.g., changing the default to None and applying it after resolution), use it. The acceptance criterion is "pre-existing default behavior is preserved, and deprecation warning fires when `--mission` is passed".

### T022 — Refactor `lifecycle.py:27` [P]

**Purpose**: Convert `lifecycle.specify` to use `--mission-type` as canonical.

**Steps**:
1. Open `src/specify_cli/cli/commands/lifecycle.py` and locate the `specify` function (around line 25).
2. Replace the parameter:

   **Before**:
   ```python
   def specify(
       feature: str = typer.Argument(..., help="Feature name or slug (e.g., user-authentication)"),
       mission: Optional[str] = typer.Option(None, "--mission", help="Mission type (e.g., software-dev, research)"),
       json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
   ) -> None:
       """Create a feature scaffold in kitty-specs/."""
       slug = _slugify_feature_input(feature)
       agent_feature.create_mission(mission_slug=slug, mission=mission, json_output=json_output)
   ```

   **After**:
   ```python
   from specify_cli.cli.selector_resolution import (
       resolve_selector,
       ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION,
   )

   def specify(
       feature: str = typer.Argument(..., help="Feature name or slug (e.g., user-authentication)"),
       mission_type: Optional[str] = typer.Option(None, "--mission-type", help="Mission type (e.g., software-dev, research)"),
       mission: Optional[str] = typer.Option(None, "--mission", hidden=True, help="(deprecated) Use --mission-type"),
       json_output: bool = typer.Option(False, "--json", help="Emit JSON result"),
   ) -> None:
       """Create a feature scaffold in kitty-specs/."""
       slug = _slugify_feature_input(feature)
       resolved = resolve_selector(
           canonical_value=mission_type,
           canonical_flag="--mission-type",
           alias_value=mission,
           alias_flag="--mission",
           suppress_env_var=ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION,
           command_hint="--mission-type <name>",
       )
       agent_feature.create_mission(mission_slug=slug, mission=resolved.canonical_value, json_output=json_output)
   ```

3. **Note**: this site also has another function `plan` at line 35-40 with `feature: Optional[str] = typer.Option(None, "--mission", "--feature", help="Mission slug")`. **That's a tracked-mission selector site, not inverse drift.** Check whether WP04 already covers `lifecycle.py` via the WP01 audit. If not, this WP05 should also fix the `plan` function as a tracked-mission site (and the audit should have flagged it). If WP04 already owns it, leave it for WP04.

   **Suggested resolution**: add `lifecycle.py` to WP04's owned_files if the audit found tracked-mission sites in this file, and have WP05 own only the inverse-drift site at line 27. But since we already declared `lifecycle.py` in WP05's owned_files, the cleanest path is for WP05 to handle BOTH the inverse-drift site at line 27 AND the tracked-mission site at line 35 in the same pass. Update T022 to cover both if needed.

   **Important**: the WP01 audit must clarify this. If it doesn't, escalate to the planner (see the Risks section).

### T023 — Add 9 integration tests (3 sites × canonical/alias/conflict)

**Purpose**: Cover the canonical/alias/conflict cases for each of the three inverse-drift sites.

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_inverse_drift_selectors.py` with three test groups:

   ```python
   import pytest
   from typer.testing import CliRunner
   from specify_cli.cli import selector_resolution

   @pytest.fixture(autouse=True)
   def _reset_warned():
       selector_resolution._warned.clear()
       yield
       selector_resolution._warned.clear()

   runner = CliRunner(mix_stderr=False)


   class TestAgentMissionCreate:
       """Inverse drift: agent mission create --mission-type / --mission."""

       def test_canonical_succeeds(self, tmp_repo):
           # invoke agent mission create with --mission-type, assert success
           ...

       def test_alias_with_warning(self, tmp_repo):
           # invoke with --mission, assert success + warning
           ...

       def test_conflict_fails(self, tmp_repo):
           # invoke with --mission-type A --mission B, assert non-zero + conflict message
           ...


   class TestCharterInterview:
       def test_default_software_dev_no_warning(self, tmp_repo):
           # invoke with no mission flag, assert default 'software-dev' resolved, no warning
           ...

       def test_canonical_succeeds(self, tmp_repo):
           ...

       def test_alias_with_warning(self, tmp_repo):
           ...

       def test_conflict_fails(self, tmp_repo):
           ...


   class TestLifecycleSpecify:
       def test_canonical_succeeds(self, tmp_repo):
           ...

       def test_alias_with_warning(self, tmp_repo):
           ...

       def test_conflict_fails(self, tmp_repo):
           ...
   ```

2. The TestCharterInterview group has an extra test for the default-value behavior because that's the trickiest case (see T021 step 6).

3. Run:
   ```bash
   PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/test_inverse_drift_selectors.py
   ```

### T024 — Verify `--mission` help text references the deprecation

**Purpose**: Confirm that on each refactored site, the hidden `--mission` parameter's help string says "(deprecated) Use --mission-type" and that the canonical `--mission-type` parameter's help string is the migrated version.

**Steps**:
1. After T020-T023, run:
   ```bash
   uv run spec-kitty agent mission create --help | grep -E "(mission|type)"
   uv run spec-kitty charter interview --help | grep -E "(mission|type)"
   uv run spec-kitty lifecycle specify --help | grep -E "(mission|type)"
   ```
2. Expected: `--mission-type` appears with the canonical help text; `--mission` does NOT appear in any help output (it's `hidden=True`).
3. If any `--mission` appears in help output, find the parameter declaration and add `hidden=True`.

## Files Touched

| File | Action | Notes |
|---|---|---|
| `src/specify_cli/cli/commands/agent/mission.py` | MODIFY | Only `create_mission` function (~line 485) |
| `src/specify_cli/cli/commands/charter.py` | MODIFY | Only `interview` function (~line 65), preserving the `software-dev` default |
| `src/specify_cli/cli/commands/lifecycle.py` | MODIFY | `specify` function (~line 25); also `plan` function (~line 35) if WP01 audit confirms it's a tracked-mission site |
| `tests/specify_cli/cli/commands/test_inverse_drift_selectors.py` | CREATE | 9-10 integration tests |

## Definition of Done

- [ ] All 3 inverse-drift sites use `--mission-type` as canonical and `--mission` as `hidden=True` alias
- [ ] `charter interview`'s `software-dev` default is preserved (default-value scenario emits no warning)
- [ ] All 3 sites import and call `resolve_selector`
- [ ] All 9-10 integration tests pass
- [ ] `--mission` does not appear in any of the three commands' `--help` output
- [ ] mypy --strict is clean on all modified files
- [ ] If WP01 audit identified additional tracked-mission sites in `lifecycle.py`, those are also handled here

## Risks and Reviewer Guidance

**Risks**:
- The `charter interview` default-value handling is the trickiest part of this WP. Get it wrong and either (a) the default no longer works without a flag, or (b) the deprecation warning fires when no `--mission` is passed (because the helper sees `canonical_value="software-dev"` from the default and `alias_value=None`). The sentinel approach in T021 step 6 handles this; verify with the test in TestCharterInterview.test_default_software_dev_no_warning.
- `lifecycle.py` may have a tracked-mission site at line 35 (`plan` function) in addition to the inverse-drift site at line 27. This WP owns the file; check the WP01 audit and handle both cases here if needed. **Do not let WP04 also own this file** (would create an ownership conflict).
- Each call site uses different helper imports — make sure the import block at the top of each file is consistent.

**Reviewer checklist**:
- [ ] All 3 sites use `hidden=True` on the `--mission` alias parameter
- [ ] `charter interview` default behavior is preserved (test with no flags)
- [ ] All 3 sites use `ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION` (not the FEATURE one)
- [ ] No `--mission` in `--help` output for any of the three commands
- [ ] WP01 audit was consulted to confirm `lifecycle.py` line 35 disposition
- [ ] No conflict with WP04 ownership of `lifecycle.py` (this WP owns it)

## Implementation Command

```bash
spec-kitty implement WP05
```

This WP depends on WP02. Wait for WP02 to be merged. WP05 can run in parallel with WP03 and WP04 (different files, no shared ownership).

## References

- Spec §8.1.2 — Verified inverse-drift sites
- Spec FR-004, FR-021
- WP01 audit document
- `contracts/selector_resolver.md` §"Inverse-Drift Command"
- `quickstart.md` Step 5

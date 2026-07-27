# Quickstart: Implementing feature-alias-removal-01KW0N87

**Branch**: `feat/feature-alias-removal`
**Clone**: `/tmp/sk-1797/m1060-feature-alias-removal`

---

## Before You Start

1. Confirm you are on the correct branch:
   ```bash
   git -C /tmp/sk-1797/m1060-feature-alias-removal branch --show-current
   # Expected: feat/feature-alias-removal
   ```

2. Confirm `_legacy_aliases.py` is absent:
   ```bash
   find /tmp/sk-1797/m1060-feature-alias-removal/src -name "_legacy_aliases.py"
   # Expected: no output
   ```

3. Verify the test suite is green before touching anything:
   ```bash
   cd /tmp/sk-1797/m1060-feature-alias-removal
   PWHEADLESS=1 pytest tests/contract/test_terminology_guards.py tests/contract/test_feature_alias_scope.py -q
   ```

---

## Edit Sequence (per-WP expected decomposition)

### WP01 — Remove `--feature` from implement.py and merge.py

**Files**: `src/specify_cli/cli/commands/implement.py`, `merge.py`

1. `implement.py`:
   - Remove `feature: Annotated[str|None, typer.Option("--feature", hidden=True, ...)] = None` param from `implement()` (line ~934)
   - Remove `feature: str | None` param from `_run_recover_mode()` (line ~836)
   - Update `detect_feature_context()`: remove `feature_flag` param, change `raw_handle = mission_flag or feature_flag` to `raw_handle = mission_flag`, add whitespace-normalization inline guard raising `typer.BadParameter`
   - Update call sites: `detect_feature_context(mission, feature, ...)` → `detect_feature_context(mission, ...)` at lines 851 and 999
   - Rename `_feature_number` → `_mission_number` at both call sites (lines 851 and 999)
   - Update `_run_recover_mode` call at line ~979: drop `feature` arg

2. `merge.py`:
   - Remove `feature: str = typer.Option(None, "--feature", hidden=True, ...)` from `merge()` (line ~412)
   - Remove `feature: str | None` from `_resolve_slug_or_exit()` (line ~231); update `(mission or feature or "").strip()` → `(mission or "").strip()`
   - Remove `feature: str | None` from `_dispatch_abort()` (~277) and `_dispatch_resume()` (~328); same `or feature` removal in slug computation
   - Update all three callers in `merge()` to drop `feature` arg (~441, ~445, ~453)
   - Rename `resolved_feature` → `resolved_mission` everywhere (≈10 occurrences): `merge()`, `_run_real_merge()`, `_dispatch_resume()`
   - Update no-selector error at line ~501-503: `raise typer.Exit(1)` → `raise typer.Exit(2)`

### WP02 — Remove `--feature` from next_cmd.py, research.py, context.py, accept.py

**Files**: `src/specify_cli/cli/commands/next_cmd.py`, `research.py`, `context.py`, `accept.py`

1. `next_cmd.py`:
   - Remove `feature: Annotated[...] = None` param (lines ~71-74)
   - Update `_resolve_mission_slug(mission, feature, repo_root)` → drop `feature` param, replace `resolve_selector(...)` block with inline guard
   - Update call at line ~116: drop `feature` arg

2. `research.py`:
   - Remove `feature: str | None = typer.Option(...)` param (lines ~33-38)
   - Replace `resolve_selector(...)` block (lines ~67-79) with inline guard
   - Remove `except typer.BadParameter` block (inline guard raises BadParameter directly)
   - Rename StepTracker keys `"feature"` → `"mission"` throughout (cosmetic but consistent)

3. `context.py` (`mission_resolve_command`):
   - Remove `feature: Annotated[...] = None` param (line ~244)
   - Replace `resolve_selector(...)` call (lines ~269-276) with inline guard

4. `accept.py`:
   - Remove `feature: str | None = typer.Option(...)` param (lines ~231-236)
   - Change `raw_handle = mission or feature` → `raw_handle = mission.strip() if isinstance(mission, str) else None`
   - Update `if raw_handle is None:` → `if not raw_handle:` (catches whitespace-only)
   - Change `raise typer.Exit(1)` → `raise typer.Exit(2)` in no-selector guard
   - Rename `feature_slug` → `mission_slug` in `_spec_artifact_dirty_paths()` and `_commit_residual_acceptance_artifacts()` parameter and local variable names

### WP03 — Remove `--feature` from lifecycle.py and mission_type.py; positional rename

**Files**: `src/specify_cli/cli/commands/lifecycle.py`, `mission_type.py`

1. `lifecycle.py`:
   - `specify()`: rename positional `feature` → `mission` (line ~126); update help text; update `_slugify_feature_input(feature)` → `_slugify_feature_input(mission)` at line ~133
   - `plan()`: remove `feature: str | None = typer.Option(None, "--feature", ...)` (line ~169); change `if mission is not None or feature is not None:` → `if mission is not None:`; replace `resolve_selector(...)` block with inline whitespace-normalization
   - `tasks()`: same pattern as `plan()` but also update the `else:` branch condition

2. `mission_type.py` (`current_cmd`):
   - Remove `feature: Annotated[...] = None` param (lines ~207-210)
   - Change `if mission is None and feature is None and not detected_mission:` → `if mission is None and not detected_mission:` (~217)
   - Change `if mission is None and feature is None:` → `if mission is None:` (~239)
   - Replace `resolve_selector(...)` + `except typer.BadParameter` block with inline guard

### WP04 — Terminology guard extension and test updates

**Files**: `tests/contract/test_terminology_guards.py`, `tests/contract/test_feature_alias_scope.py`, `tests/specify_cli/cli/test_no_visible_feature_alias.py`

1. `test_terminology_guards.py`: add 8 new paths to `INSCOPE_FEATURE_FREE_FILES`:
   - `src/specify_cli/cli/commands/implement.py`
   - `src/specify_cli/cli/commands/merge.py`
   - `src/specify_cli/cli/commands/next_cmd.py`
   - `src/specify_cli/cli/commands/research.py`
   - `src/specify_cli/cli/commands/context.py`
   - `src/specify_cli/cli/commands/accept.py`
   - `src/specify_cli/cli/commands/lifecycle.py`
   - `src/specify_cli/cli/commands/mission_type.py`

2. `test_feature_alias_scope.py`: flip merge assertions:
   - `test_merge_still_accepts_feature_alias` → now asserts `result.exit_code == 2` and `"No such option" in result.output`
   - `test_merge_feature_and_mission_both_accepted` → now asserts `--feature` rejected (exit 2), `--mission` accepted
   - `test_merge_feature_alias_is_hidden_in_cli_introspection` → now asserts merge has NO `--feature` param
   - Update `_INSCOPE_FILES` and `_INSCOPE_COMMAND_NAMES` to include the 8 new files/commands

3. `test_no_visible_feature_alias.py`:
   - Add `test_zero_feature_flags_exist_cli_wide()` asserting 0 `--feature` params anywhere in the CLI tree
   - `test_every_feature_flag_is_hidden` passes vacuously (no flags → 0 offenders)

### WP05 — No-selector regression tests (FR-008)

**File**: `tests/contract/test_no_selector_guard.py` (new)

Add 8 tests, one per command, following the shape in `contracts/no-selector-error-contract.md`.
Each test invokes the command with no `--mission` arg and asserts exit code 2, no TypeError,
and a user-readable error string.

### WP06 — Docs and CHANGELOG (FR-010)

**Files**: `docs/status-model.md`, `docs/reference/environment-variables.md`,
`docs/reference/orchestrator-api.md`, `docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md`, `CHANGELOG.md`

- `docs/status-model.md:10`: update "deferred user-facing top-level" to reflect all top-level commands
  are now alias-free
- `docs/reference/environment-variables.md:232,287`: update `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION`
  description to note it is now inert (no `--feature` warnings are emitted)
- `docs/reference/orchestrator-api.md:81`: remove or update the `--feature` entry in the command options list
- `docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md:24`: update the implement opts list
  to remove `--feature`
- `CHANGELOG.md`: add unreleased entry describing the complete removal of `--feature` from all 8 commands

---

## Ruff/Mypy Gate

After each WP, run:
```bash
cd /tmp/sk-1797/m1060-feature-alias-removal
ruff check src/specify_cli/cli/commands/{implement,merge,next_cmd,research,context,accept,lifecycle,mission_type}.py
mypy src/specify_cli/cli/commands/{implement,merge,next_cmd,research,context,accept,lifecycle,mission_type}.py
```

No new errors or warnings are acceptable.

## Full Suite Gate

After WP05:
```bash
PWHEADLESS=1 pytest tests/contract/ tests/specify_cli/cli/ -q -n auto --dist loadfile
```

After WP06:
```bash
pytest tests/architectural/test_no_legacy_terminology.py -q
```

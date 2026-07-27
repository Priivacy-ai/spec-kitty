---
work_package_id: WP02
title: Selector Resolution Helper
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-021
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-077-mission-terminology-cleanup
base_commit: f01ba8f466b66a22b45ba20401c7c388f2815a3a
created_at: '2026-04-08T13:51:04.373132+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
shell_pid: "82147"
agent: "codex:gpt-5-codex:implementer:orchestrator"
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: src/specify_cli/cli/selector_resolution.py
execution_mode: code_change
mission_slug: 077-mission-terminology-cleanup
owned_files:
- src/specify_cli/cli/selector_resolution.py
- tests/specify_cli/cli/commands/test_selector_resolution.py
priority: P0
tags: []
---

# WP02 — Selector Resolution Helper

## Objective

Implement `src/specify_cli/cli/selector_resolution.py` and its unit test file `tests/specify_cli/cli/commands/test_selector_resolution.py`. This is the central enforcement point for FR-006 (deterministic dual-flag conflict), FR-007 (same-value compat with warning), FR-021 (inverse direction), NFR-002 (single warning per invocation), and NFR-003 (suppression env var).

This WP produces the helper itself + 12 unit tests. WP03/WP04/WP05/WP09 consume it.

## Context

The verified bug at `src/specify_cli/cli/commands/mission.py:172-194` exists because typer collapses multi-alias `Option` declarations into a single parameter with last-value-wins resolution. The fix is architectural: declare canonical and alias as **separate** typer parameters and reconcile them in a small post-parse helper. This WP implements that helper.

The helper does **not** modify or replace `require_explicit_feature` at `src/specify_cli/core/paths.py:273`. Instead, it sits *upstream* — selector resolution → existing presence check.

The full design is in:
- `data-model.md` — `SelectorResolution` dataclass + algorithm
- `contracts/selector_resolver.md` — public API contract + 12 required test cases
- `contracts/deprecation_warning.md` — warning text format + suppression contract

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP02` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T005 — Create `selector_resolution.py` module shell

**Purpose**: Set up the new module file with imports, the `SelectorResolution` dataclass, and the module-level state.

**Steps**:
1. Create `src/specify_cli/cli/selector_resolution.py` with the following structure:
   ```python
   """Post-parse selector resolution for canonical/alias CLI flags.

   See kitty-specs/077-mission-terminology-cleanup/spec.md §11.1 for the
   asymmetric migration policy this helper implements.
   """
   from __future__ import annotations

   import os
   from dataclasses import dataclass

   import typer
   from rich.console import Console

   from specify_cli.core.paths import require_explicit_feature

   _err_console = Console(stderr=True)
   _warned: set[tuple[str, str]] = set()


   @dataclass(frozen=True, slots=True)
   class SelectorResolution:
       """Captures the canonical resolved value and how it was resolved."""

       canonical_value: str
       canonical_flag: str
       alias_used: bool
       alias_flag: str | None
       warning_emitted: bool

       def __post_init__(self) -> None:
           if self.alias_used and self.alias_flag is None:
               raise ValueError("alias_used=True requires alias_flag to be set")
           if not self.alias_used and self.alias_flag is not None:
               raise ValueError("alias_used=False requires alias_flag to be None")
   ```

2. Verify the file imports cleanly:
   ```bash
   uv run python -c "from specify_cli.cli.selector_resolution import SelectorResolution"
   ```

**Files**:
- `src/specify_cli/cli/selector_resolution.py` (new, ~30 lines after T005)

### T006 — Implement `_emit_deprecation_warning`

**Purpose**: Add the private sub-helper that emits the yellow stderr deprecation warning at most once per `(canonical_flag, alias_flag)` pair per process, with env var suppression.

**Steps**:
1. Add the doc-path mapping helper:
   ```python
   _MIGRATION_DOCS = {
       "--feature": "docs/migration/feature-flag-deprecation.md",
       "--mission": "docs/migration/mission-type-flag-deprecation.md",
   }


   def _doc_path_for(alias_flag: str) -> str:
       """Map an alias flag to its migration doc path."""
       return _MIGRATION_DOCS[alias_flag]
   ```

2. Add the warning emit function:
   ```python
   def _emit_deprecation_warning(
       canonical_flag: str,
       alias_flag: str,
       suppress_env_var: str,
   ) -> bool:
       """Emit a single yellow stderr deprecation warning unless suppressed.

       Returns True if a warning was actually emitted, False if suppressed
       or if a warning has already been emitted for this (canonical, alias)
       pair in the current process.
       """
       pair = (canonical_flag, alias_flag)
       if pair in _warned:
           return False
       if os.environ.get(suppress_env_var) == "1":
           return False
       _warned.add(pair)
       doc_path = _doc_path_for(alias_flag)
       _err_console.print(
           f"[yellow]Warning:[/yellow] {alias_flag} is deprecated; "
           f"use {canonical_flag}. See: {doc_path}"
       )
       return True
   ```

3. Match the exact precedent at `src/specify_cli/cli/commands/agent/mission.py:604`:
   ```python
   console.print("[yellow]Warning:[/yellow] --require-tasks is deprecated; use --include-tasks.")
   ```
   Same `[yellow]Warning:[/yellow]` prefix, same prose pattern.

**Files**:
- `src/specify_cli/cli/selector_resolution.py` (extended)

### T007 — Implement `resolve_selector` public function

**Purpose**: Add the main public function that takes two parsed values and reconciles them. This is the function every command body calls.

**Steps**:
1. Add the function signature exactly as in `contracts/selector_resolver.md`:
   ```python
   def resolve_selector(
       *,
       canonical_value: str | None,
       canonical_flag: str,
       alias_value: str | None,
       alias_flag: str,
       suppress_env_var: str,
       command_hint: str | None = None,
   ) -> SelectorResolution:
   ```

2. Implement the resolution algorithm from `data-model.md`:
   ```python
       canonical_norm = (canonical_value or "").strip() or None
       alias_norm = (alias_value or "").strip() or None

       # Both empty: delegate to require_explicit_feature for the missing-value error
       if canonical_norm is None and alias_norm is None:
           # require_explicit_feature raises typer.BadParameter (or ValueError —
           # confirm and wrap if needed)
           hint = command_hint or f"{canonical_flag} <value>"
           require_explicit_feature(None, command_hint=hint)
           # require_explicit_feature should have raised; this is unreachable
           raise RuntimeError("require_explicit_feature did not raise on empty input")

       # Both set, conflicting
       if canonical_norm is not None and alias_norm is not None and canonical_norm != alias_norm:
           raise typer.BadParameter(
               f"Conflicting selectors: {canonical_flag}={canonical_norm!r} and "
               f"{alias_flag}={alias_norm!r} were both provided with different "
               f"values. {alias_flag} is a hidden deprecated alias for "
               f"{canonical_flag}; pass only {canonical_flag}."
           )

       # Both set, equal
       if canonical_norm is not None and alias_norm is not None:
           warning_emitted = _emit_deprecation_warning(canonical_flag, alias_flag, suppress_env_var)
           return SelectorResolution(
               canonical_value=canonical_norm,
               canonical_flag=canonical_flag,
               alias_used=True,
               alias_flag=alias_flag,
               warning_emitted=warning_emitted,
           )

       # Only canonical set
       if canonical_norm is not None:
           return SelectorResolution(
               canonical_value=canonical_norm,
               canonical_flag=canonical_flag,
               alias_used=False,
               alias_flag=None,
               warning_emitted=False,
           )

       # Only alias set
       assert alias_norm is not None  # narrowed by elimination
       warning_emitted = _emit_deprecation_warning(canonical_flag, alias_flag, suppress_env_var)
       return SelectorResolution(
           canonical_value=alias_norm,
           canonical_flag=canonical_flag,
           alias_used=True,
           alias_flag=alias_flag,
           warning_emitted=warning_emitted,
       )
   ```

3. **Critical**: do not change the order of checks. Conflict detection must run *before* warning emission, otherwise a conflict case would emit a warning that's discarded by the BadParameter raise.

4. Verify `require_explicit_feature` actually raises `typer.BadParameter` (or wraps it in one). If it raises `ValueError` instead, wrap the call:
   ```python
   try:
       require_explicit_feature(None, command_hint=hint)
   except ValueError as e:
       raise typer.BadParameter(str(e)) from e
   ```

**Files**:
- `src/specify_cli/cli/selector_resolution.py` (extended)

### T008 — Wire suppression env vars for both directions

**Purpose**: Add the two named env vars from spec §11.1 / NFR-003 as module-level constants, so call sites pass them by name.

**Steps**:
1. Add at the top of the module (right after `_warned`):
   ```python
   ENV_VAR_SUPPRESS_FEATURE_DEPRECATION = "SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION"
   ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION = "SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION"
   ```

2. Document them at the module level (in the docstring) so call sites know which to use:
   - `ENV_VAR_SUPPRESS_FEATURE_DEPRECATION` for `--mission` ↔ `--feature`
   - `ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION` for `--mission-type` ↔ `--mission`

3. Call sites should reference these constants by name, not magic strings:
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
   )
   ```

**Files**:
- `src/specify_cli/cli/selector_resolution.py` (extended; final size ~100 lines)

### T009 — Create `test_selector_resolution.py` with 12 unit test cases

**Purpose**: Cover all 12 unit test cases from `contracts/selector_resolver.md` §"Required Test Coverage".

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_selector_resolution.py` with the autouse fixture from `data-model.md`:
   ```python
   import os
   import pytest
   import typer

   from specify_cli.cli import selector_resolution
   from specify_cli.cli.selector_resolution import (
       resolve_selector,
       ENV_VAR_SUPPRESS_FEATURE_DEPRECATION,
       ENV_VAR_SUPPRESS_MISSION_TYPE_DEPRECATION,
   )


   @pytest.fixture(autouse=True)
   def _reset_selector_resolution_state():
       """Reset the module-level _warned set between tests."""
       selector_resolution._warned.clear()
       yield
       selector_resolution._warned.clear()
   ```

2. Implement all 12 unit tests from the contract. Examples:

   **Test 1 — canonical only**:
   ```python
   def test_canonical_only_returns_value():
       result = resolve_selector(
           canonical_value="077-test",
           canonical_flag="--mission",
           alias_value=None,
           alias_flag="--feature",
           suppress_env_var=ENV_VAR_SUPPRESS_FEATURE_DEPRECATION,
       )
       assert result.canonical_value == "077-test"
       assert result.alias_used is False
       assert result.alias_flag is None
       assert result.warning_emitted is False
   ```

   **Test 4 — conflict** (the regression test for the verified bug):
   ```python
   def test_both_different_raises_bad_parameter(capsys):
       with pytest.raises(typer.BadParameter) as exc_info:
           resolve_selector(
               canonical_value="077-mission-A",
               canonical_flag="--mission",
               alias_value="077-mission-B",
               alias_flag="--feature",
               suppress_env_var=ENV_VAR_SUPPRESS_FEATURE_DEPRECATION,
           )
       msg = str(exc_info.value)
       assert "077-mission-A" in msg
       assert "077-mission-B" in msg
       assert "--mission" in msg
       assert "--feature" in msg
       assert "deprecated" in msg
       # No warning should have been emitted (conflict short-circuits)
       captured = capsys.readouterr()
       assert "Warning" not in captured.err
   ```

   **Test 8 — single warning per pair**:
   ```python
   def test_warning_emitted_only_once_per_pair(capsys):
       for _ in range(2):
           resolve_selector(
               canonical_value=None,
               canonical_flag="--mission",
               alias_value="077-test",
               alias_flag="--feature",
               suppress_env_var=ENV_VAR_SUPPRESS_FEATURE_DEPRECATION,
           )
       captured = capsys.readouterr()
       # Exactly one Warning line in stderr
       assert captured.err.count("Warning:") == 1
   ```

   **Test 10 — env var suppression**:
   ```python
   def test_suppression_env_var_skips_warning(capsys, monkeypatch):
       monkeypatch.setenv(ENV_VAR_SUPPRESS_FEATURE_DEPRECATION, "1")
       result = resolve_selector(
           canonical_value=None,
           canonical_flag="--mission",
           alias_value="077-test",
           alias_flag="--feature",
           suppress_env_var=ENV_VAR_SUPPRESS_FEATURE_DEPRECATION,
       )
       assert result.canonical_value == "077-test"
       assert result.warning_emitted is False
       captured = capsys.readouterr()
       assert "Warning" not in captured.err
   ```

3. Implement all 12 cases from the contract. Use `capsys` (not `caplog`) for stderr capture because the helper uses Rich Console, not the logging module.

**Files**:
- `tests/specify_cli/cli/commands/test_selector_resolution.py` (new, ~250 lines for 12 tests)

### T010 — Verify mypy --strict and ≥90% coverage

**Purpose**: Confirm the helper meets charter quality gates (mypy --strict, ≥90% coverage).

**Steps**:
1. Run mypy --strict on the new module:
   ```bash
   uv run mypy --strict src/specify_cli/cli/selector_resolution.py
   ```
   Fix any type errors before proceeding.

2. Run coverage on the helper:
   ```bash
   uv run pytest tests/specify_cli/cli/commands/test_selector_resolution.py \
     --cov=specify_cli.cli.selector_resolution --cov-report=term-missing
   ```
   Coverage should be 100% (the module is small and every branch is tested). If <90%, add tests for the missing branches.

3. Run all tests one more time to confirm green:
   ```bash
   PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/test_selector_resolution.py
   ```

**Validation**:
- [ ] mypy --strict: 0 errors on `selector_resolution.py`
- [ ] Coverage ≥ 90% (target: 100%)
- [ ] All 12 unit tests pass

## Files Touched

| File | Action | Estimated lines |
|---|---|---|
| `src/specify_cli/cli/selector_resolution.py` | CREATE | ~100 |
| `tests/specify_cli/cli/commands/test_selector_resolution.py` | CREATE | ~250 |

No other files are touched. No imports added to existing CLI command files (those happen in WP03/WP04/WP05).

## Definition of Done

- [ ] `src/specify_cli/cli/selector_resolution.py` exists and is importable
- [ ] `SelectorResolution` dataclass is frozen, has slots, validates `alias_used`/`alias_flag` consistency
- [ ] `resolve_selector` correctly handles all 5 cases (both empty / both equal / both conflict / canonical only / alias only)
- [ ] `_emit_deprecation_warning` enforces the single-warning-per-invocation guarantee via the module-level `_warned` set
- [ ] Both suppression env vars are exported as module constants
- [ ] All 12 unit tests pass
- [ ] mypy --strict is clean
- [ ] Coverage on the new module is ≥ 90% (target: 100%)
- [ ] The module is **not** imported by any CLI command yet (that happens in WP03/WP04/WP05)

## Risks and Reviewer Guidance

**Risks**:
- If `require_explicit_feature` raises `ValueError` instead of `typer.BadParameter`, the empty-input case will leak the wrong exception type. Verify by reading the function and wrap if needed.
- Without the `_reset_selector_resolution_state` autouse fixture, test order affects warning emission and CI is flaky. Install the fixture from the start.
- A future PR might add a third alias direction. Keep the helper symmetric: it takes `canonical_*` and `alias_*` keyword arguments and doesn't hardcode `--feature` or `--mission` anywhere outside the env var constants and `_doc_path_for`.

**Reviewer checklist**:
- [ ] `_warned` is a module-level set, not an instance attribute
- [ ] The check order in `resolve_selector` is: empty → conflict → both-equal → canonical-only → alias-only
- [ ] No magic strings in call-site usage; env vars are imported as constants
- [ ] Tests use `capsys`, not `caplog` (Rich → stderr, not logging)
- [ ] The autouse fixture clears `_warned` both before and after each test (defensive)

## Implementation Command

```bash
spec-kitty implement WP02
```

This WP depends on WP01. Wait for WP01 to be merged before starting.

## References

- `data-model.md` — `SelectorResolution` shape and resolution algorithm
- `contracts/selector_resolver.md` — public API + 12 test cases
- `contracts/deprecation_warning.md` — warning text format
- Spec FR-006, FR-007, FR-021, NFR-002, NFR-003
- Existing precedent: `src/specify_cli/cli/commands/agent/mission.py:604` (same warning style)
- Existing helper: `src/specify_cli/core/paths.py:273` (`require_explicit_feature` — not modified)

## Activity Log

- 2026-04-08T13:51:50Z – codex:gpt-5-codex:implementer:orchestrator – shell_pid=82147 – Started implementation via action command
- 2026-04-08T15:01:30Z – codex:gpt-5-codex:implementer:orchestrator – shell_pid=82147 – Moved to done

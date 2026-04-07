---
work_package_id: WP06
title: Fix slug validator
dependencies: []
requirement_refs:
- FR-017
- FR-018
- FR-019
planning_base_branch: main
merge_target_branch: main
branch_strategy: Plan and merge on main; execution worktree allocated by finalize-tasks lane computation.
subtasks: [T035, T036, T037, T038]
history:
- date: '2026-04-07'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/core/
execution_mode: code_change
owned_files:
- src/specify_cli/core/mission_creation.py
- tests/core/test_slug_validator_unit.py
---

# WP06: Fix Slug Validator

## Objective

Update `KEBAB_CASE_PATTERN` in `mission_creation.py` to accept digit-prefixed slugs (e.g. `068-feature-name`). Update the error message and add tests.

**Success criterion**: `spec-kitty specify 070-new-feature` (or the equivalent `create("070-new-feature")` call) does not raise `MissionCreationError` for the slug. `User-Auth` and `user_auth` still raise errors.

## Context

`KEBAB_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")` at line 47 of `src/specify_cli/core/mission_creation.py` requires the first character to be a lowercase letter. Spec-kitty's own feature slugs start with three digits (`001-`, `002-`, ..., `068-`, `069-`). The `specify` command is unusable with spec-kitty's own naming convention.

This is a 1-line regex change plus error message update. Total scope: ~10 lines changed, 1 new test file.

## Branch Strategy

- **Implementation branch**: allocated by `finalize-tasks` (Lane A worktree — independent)
- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Command**: `spec-kitty implement WP06`

---

## Subtask T035: Update `KEBAB_CASE_PATTERN`

**Purpose**: Accept digit-prefixed slugs while preserving all existing rejections.

**File**: `src/specify_cli/core/mission_creation.py`

**Change** at line 47:

```python
# Before:
KEBAB_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

# After:
KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9]*(-[a-z0-9]+)*$")
# Note: Intentionally permissive — bare-digit slugs like "069" are accepted.
# create() always prefixes the mission number, so "069" becomes "070-069" in practice.
```

**Pattern analysis**:
- Old: `^[a-z]` — first char must be lowercase letter
- New: `^[a-z0-9]` — first char may be lowercase letter OR digit
- Everything else is identical: subsequent chars are `[a-z0-9]`, optional hyphen-separated segments

**Accepted by new pattern** (verify each):
- `068-feature-name` ✓
- `001-foo` ✓
- `user-auth` ✓ (letter-prefix — still works)
- `fix-bug-123` ✓
- `069` ✓ (bare digit — intentionally accepted; note in comment)

**Still rejected by new pattern**:
- `User-Auth` ✗ (uppercase)
- `user_auth` ✗ (underscore)
- `` ✗ (empty)
- `-starts-with-hyphen` ✗ (hyphen first)
- `ends-with-` ✗ (trailing hyphen)

---

## Subtask T036: Update error message and docstring

**Purpose**: Remove the now-incorrect "starts with number" invalid example; add a digit-prefix valid example; add explanatory comment.

**File**: `src/specify_cli/core/mission_creation.py`

**Change** at lines ~202–212 (inside `create_mission()`):

```python
# Before:
raise MissionCreationError(
    f"Invalid feature slug '{mission_slug}'. "
    "Must be kebab-case (lowercase letters, numbers, hyphens only)."
    "\n\nValid examples:"
    "\n  - user-auth"
    "\n  - fix-bug-123"
    "\n  - new-dashboard"
    "\n\nInvalid examples:"
    "\n  - User-Auth (uppercase)"
    "\n  - user_auth (underscores)"
    "\n  - 123-fix (starts with number)"   # ← remove this line
)

# After:
raise MissionCreationError(
    f"Invalid feature slug '{mission_slug}'. "
    "Must be kebab-case (lowercase letters, numbers, hyphens only)."
    "\n\nValid examples:"
    "\n  - user-auth"
    "\n  - fix-bug-123"
    "\n  - 068-feature-name"               # ← new: digit-prefix example
    "\n  - new-dashboard"
    "\n\nInvalid examples:"
    "\n  - User-Auth (uppercase)"
    "\n  - user_auth (underscores)"
    # removed: "\n  - 123-fix (starts with number)"
)
```

**Also update the docstring** at line ~179 (parameter description for `mission_slug`):

```python
# Find: "Bare slug such as ``"user-auth"`` (kebab-case, no number prefix)."
# Change to: "Bare slug such as ``"user-auth"`` or ``"068-feature"`` (kebab-case)."
```

---

## Subtask T037: Unit tests — slug validation

**Purpose**: Test the new regex accepts digit-prefixed slugs and still rejects invalid ones.

**File**: `tests/core/test_slug_validator_unit.py` (new)

```python
"""Unit tests for slug validator in mission_creation.py (FR-017, FR-018, FR-019)."""
from __future__ import annotations

import pytest
from specify_cli.core.mission_creation import KEBAB_CASE_PATTERN, MissionCreationError


class TestKebabCasePattern:
    """Test the KEBAB_CASE_PATTERN regex directly."""

    @pytest.mark.parametrize("slug", [
        "user-auth",           # letter-prefix (existing, must keep working)
        "fix-bug-123",         # letter-prefix with numbers
        "new-dashboard",       # multi-word
        "068-feature-name",    # digit-prefix (the fix)
        "001-foo",             # digit-prefix short
        "069-planning-pipeline-integrity",  # real spec-kitty slug
        "123",                 # bare digit (intentionally permissive)
        "a",                   # single letter
        "1",                   # single digit
    ])
    def test_valid_slugs(self, slug: str) -> None:
        assert KEBAB_CASE_PATTERN.match(slug) is not None, f"Expected {slug!r} to match"

    @pytest.mark.parametrize("slug", [
        "",                    # empty (FR-019)
        "User-Auth",           # uppercase (FR-018)
        "user_auth",           # underscore (FR-018)
        "user auth",           # space (FR-018)
        "-starts-with-hyphen", # leading hyphen
        "ends-with-",          # trailing hyphen
        "double--hyphen",      # double hyphen
        "UPPER",               # all uppercase
    ])
    def test_invalid_slugs(self, slug: str) -> None:
        assert KEBAB_CASE_PATTERN.match(slug) is None, f"Expected {slug!r} to NOT match"


class TestCreateMissionSlugValidation:
    """Integration-level test through create_mission() entry point."""

    def test_digit_prefix_slug_accepted(self, tmp_path: Path) -> None:
        """FR-017: digit-prefixed slug does not raise MissionCreationError."""
        from pathlib import Path
        from unittest.mock import patch

        with patch("specify_cli.core.mission_creation.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.core.mission_creation.is_git_repo", return_value=True), \
             patch("specify_cli.core.mission_creation.get_current_branch", return_value="main"), \
             patch("specify_cli.core.mission_creation.get_next_feature_number", return_value=70), \
             patch("specify_cli.core.mission_creation.is_worktree_context", return_value=False), \
             patch("specify_cli.core.mission_creation._commit_mission_files"):
            from specify_cli.core.mission_creation import create_mission
            # Should not raise
            result = create_mission("070-new-feature")
            assert result is not None

    def test_uppercase_slug_still_rejected(self, tmp_path: Path) -> None:
        """FR-018: uppercase slugs are still rejected."""
        from specify_cli.core.mission_creation import create_mission
        with pytest.raises(MissionCreationError, match="Invalid feature slug"):
            create_mission("User-Auth")
```

---

## Subtask T038: Integration test — `create "070-new-feature"` passes

This is covered by T037's `test_digit_prefix_slug_accepted`. If a more end-to-end test is needed (invoking the CLI via `typer.testing.CliRunner`), add to the same test file:

```python
from typer.testing import CliRunner
from specify_cli.cli.commands.agent.mission import app

runner = CliRunner()

class TestSlugCLI:
    def test_cli_create_digit_prefix_slug(self, tmp_path: Path) -> None:
        """FR-017: CLI create command accepts digit-prefixed slug."""
        with patch("specify_cli.core.mission_creation.locate_project_root",
                   return_value=tmp_path), \
             patch("specify_cli.core.mission_creation.is_git_repo", return_value=True), \
             patch("specify_cli.core.mission_creation.get_current_branch", return_value="main"), \
             patch("specify_cli.core.mission_creation.get_next_feature_number", return_value=70), \
             patch("specify_cli.core.mission_creation.is_worktree_context", return_value=False), \
             patch("specify_cli.core.mission_creation._commit_mission_files"):

            result = runner.invoke(app, ["mission", "create", "070-new-feature", "--json"])

        # Should not contain "Invalid feature slug"
        assert "Invalid feature slug" not in result.output
        assert result.exit_code == 0
```

---

## Definition of Done

- [ ] `KEBAB_CASE_PATTERN` changed from `^[a-z]` to `^[a-z0-9]` as first character class
- [ ] Inline comment added explaining intentional permissiveness for bare-digit slugs
- [ ] Error message updated (no more "starts with number" invalid example; digit-prefix valid example added)
- [ ] Docstring at line ~179 updated
- [ ] `tests/core/test_slug_validator_unit.py` passes
- [ ] All existing tests in the codebase that use `KEBAB_CASE_PATTERN` or `create_mission()` still pass
- [ ] `mypy --strict src/specify_cli/core/mission_creation.py` passes

## Reviewer Guidance

- The regex change is a one-character edit: `[a-z]` → `[a-z0-9]`. Verify the rest of the pattern is unchanged.
- Confirm the em dash in error messages was not unintentionally altered.
- Run the full test suite after this change to catch any snapshot tests that may have recorded the old error message text.

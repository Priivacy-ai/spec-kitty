---
work_package_id: WP01
title: --feature → --mission CLI Flag Rename
lane: done
dependencies: []
requirement_refs:
- FR-017
- FR-018
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase A - Pre-work
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-22T11:50:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer
---

# Work Package Prompt: WP01 – `--feature` → `--mission` CLI Flag Rename

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, address the Review Feedback section first.

---

## Review Feedback

*[Empty — populated by `/spec-kitty.review` if work is returned.]*

---

## Objectives & Success Criteria

- `--mission` works as the canonical flag on all 16 CLI entry points (14 files, 38 `typer.Option` occurrences).
- `--feature` continues to work as a backward-compatible hidden alias and emits a deprecation warning on stderr.
- Passing both flags with different values raises a `typer.BadParameter` error.
- Passing both flags with identical values works silently (no error, no warning).
- A shared utility `resolve_mission_or_feature()` centralizes the resolution logic.
- All existing tests pass. New ATDD tests cover the 4 acceptance scenarios from US-7.
- `ruff check .` and `mypy` clean.

## Context & Constraints

- **Plan**: `kitty-specs/057-doctrine-stack-init-and-profile-integration/plan.md` → WP-A1
- **Spec**: US-7, FR-017, FR-018, C-005
- **Constraint C-005**: `--feature` must remain accepted for at least one deprecation cycle. Conflicting `--feature` and `--mission` values must produce a clear error. Same-value case works silently.
- This is pre-work — do NOT introduce any other changes. Boy Scout only within touched files.
- **Start command**: `spec-kitty implement WP01` (no `--base` needed — first WP)

## Subtasks & Detailed Guidance

### Subtask T001 – Create `resolve_mission_or_feature()` utility

- **Purpose**: Centralize the flag resolution logic so every command uses identical semantics. Prevents future drift.
- **Files**: Create `src/specify_cli/cli/commands/_flag_utils.py` (new file, ~30 lines).
- **Steps**:
  1. Create the file with:
     ```python
     """Shared utility for resolving --mission / --feature flag backward compatibility."""
     from __future__ import annotations
     import typer


     def resolve_mission_or_feature(
         mission: str | None,
         feature: str | None,
     ) -> str | None:
         """Resolve --mission / --feature flag pair.

         Returns:
             The resolved slug, or None if neither was provided.

         Raises:
             typer.BadParameter: If both flags are provided with different values.
         """
         if mission and feature:
             if mission != feature:
                 raise typer.BadParameter(
                     f"Conflicting flags: --mission={mission!r} and --feature={feature!r}. "
                     "Use --mission only (--feature is deprecated).",
                     param_hint="'--mission' / '--feature'",
                 )
             # Same value — accept silently, prefer mission
             return mission
         if feature is not None:
             typer.echo(
                 "⚠️  --feature is deprecated; use --mission instead.",
                 err=True,
             )
             return feature
         return mission  # may be None
     ```
  2. Run `ruff check src/specify_cli/cli/commands/_flag_utils.py` and fix any issues.
  3. Run `mypy src/specify_cli/cli/commands/_flag_utils.py` and fix any type errors.
- **Parallel?**: No — T002 (tests) can be written in parallel but this utility must exist before T003/T004.

### Subtask T002 – Write ATDD acceptance tests (tests first)

- **Purpose**: Acceptance tests must be written BEFORE implementation begins (T003/T004) and must fail on the current codebase. They become the green gate for this WP.
- **Files**: Create `tests/specify_cli/cli/commands/test_mission_flag_rename.py`.
- **Steps**:
  1. Write 4 test functions covering the US-7 acceptance scenarios:
     - `test_mission_flag_works` — invoke `agent workflow implement WP01 --mission 056-x` → exits successfully (or not `--feature` deprecation warning).
     - `test_feature_flag_emits_deprecation_warning` — invoke any command with `--feature 056-x` → stderr contains "deprecated" and command succeeds.
     - `test_conflicting_flags_raises_error` — invoke with `--mission 056-a --feature 056-b` → exit code non-zero, error message mentions conflict.
     - `test_same_value_both_flags_silent` — invoke with `--mission 056-x --feature 056-x` → succeeds with no warning.
  2. Use `typer.testing.CliRunner` or `subprocess` to invoke commands.
  3. Run `pytest tests/specify_cli/cli/commands/test_mission_flag_rename.py -v` — all 4 tests must FAIL (red) at this point. If they pass, the implementation already exists; investigate.
- **Parallel?**: Can be written alongside T001.

### Subtask T003 – Apply rename to 8 top-level commands

- **Purpose**: Add `--mission` primary option and `--feature` hidden alias to all 8 top-level command files.
- **Files** (all in `src/specify_cli/cli/commands/`): `accept.py`, `implement.py`, `merge.py`, `lifecycle.py`, `next_cmd.py`, `research.py`, `validate_encoding.py`, `verify.py`.
- **Steps** for each file:
  1. Read the file. Locate the `typer.Option("--feature", ...)` parameter.
  2. Add a `--mission` parameter immediately before the `--feature` parameter:
     ```python
     mission: Annotated[str | None, typer.Option("--mission", help="Mission slug (e.g., '020-my-feature')")] = None,
     feature: Annotated[str | None, typer.Option("--feature", hidden=True, help="[Deprecated] Use --mission")] = None,
     ```
  3. At the top of the command body, replace the use of `feature` with the result of the utility:
     ```python
     from specify_cli.cli.commands._flag_utils import resolve_mission_or_feature
     slug = resolve_mission_or_feature(mission, feature)
     ```
  4. Update all internal references from `feature` to `slug` (or rename `slug` to `feature_slug` for clarity — be consistent within the file).
  5. Update help text in the command docstring/description to say "mission" instead of "feature".
- **Edge case**: Some files use `Optional[str]` style rather than `Annotated`. Use the same style as the existing code in that file.
- **Parallel?**: Yes — T003 and T004 can run simultaneously (disjoint file sets).

### Subtask T004 – Apply rename to 6 agent subcommands

- **Purpose**: Same pattern as T003 but for the agent subcommand files, which have more `--feature` occurrences per file (tasks.py has 9, status.py has 6).
- **Files** (all in `src/specify_cli/cli/commands/agent/`): `__init__.py`, `context.py`, `feature.py`, `status.py`, `tasks.py`, `workflow.py`.
- **Steps**: Same as T003, applied to each of the 38 `typer.Option("--feature", ...)` occurrences across these files.
- **Note for `feature.py`**: This file has 5 occurrences and is the longest (1996 lines). Read it carefully before editing; the `--feature` option is used in 5 different commands within the file.
- **Note for `tasks.py`**: 9 occurrences across different commands. Also 2159 lines — read and edit methodically.
- **After applying**: Run `rg 'typer.Option.*"--feature"' src/specify_cli/cli/commands/` to confirm zero remaining `typer.Option` entries with `--feature`. Any remaining occurrences are missed.
- **Parallel?**: Yes — can run simultaneously with T003.

### Subtask T005 – Update existing tests to cover both flags

- **Purpose**: Existing tests may hardcode `--feature`. Update them to test `--mission` by default and add a `--feature` alias path for the most critical commands.
- **Files**: `tests/specify_cli/cli/commands/` and `tests/agent/cli/commands/` — any test that passes `--feature`.
- **Steps**:
  1. Run `rg '"--feature"' tests/` to find all test occurrences.
  2. For each: update the primary test invocation to use `--mission`. Add a companion test using `--feature` with assertion that deprecation warning appears in stderr.
  3. Run `pytest tests/ -x` and fix any failures caused by the rename.
  4. Run the new ATDD tests from T002 — all 4 should now pass (green).
- **Parallel?**: No — must complete after T003 and T004.

## Test Strategy

```bash
# Acceptance tests (must be green after T005)
rtk test pytest tests/specify_cli/cli/commands/test_mission_flag_rename.py -v

# Full regression (must stay green)
rtk test pytest tests/ -x

# Coverage gate (90%+ on new modules — constitution requirement)
rtk test pytest tests/ --cov=specify_cli --cov=doctrine --cov=constitution --cov-fail-under=90 -q

# Type check
mypy --strict src/specify_cli/cli/commands/_flag_utils.py src/specify_cli/cli/commands/

# Lint
rtk ruff check src/specify_cli/cli/commands/
```

## Risks & Mitigations

- **Missed occurrence**: Run `rg 'typer.Option.*"--feature"' src/specify_cli/` at the end. Result must be zero.
- **Breaking downstream automation**: Deprecation warning goes to stderr, not stdout. JSON output commands (`--json`) must not include the warning in JSON payload — use `typer.echo(..., err=True)`.

## Review Guidance

- Reviewer should confirm zero `typer.Option("--feature"` remaining in source (unless hidden alias).
- Confirm `resolve_mission_or_feature()` is used in ALL 14 files (not inline logic).
- Run `spec-kitty agent workflow implement --feature some-slug` and verify deprecation warning on stderr.
- Run `spec-kitty agent workflow implement --mission some-slug --feature other-slug` and verify error.

## Activity Log

- 2026-03-22T11:50:00Z – system – lane=planned – Prompt created.

---
work_package_id: WP04
title: Terminology guard extension and existing test updates
dependencies:
- WP03
requirement_refs:
- FR-007
- FR-009
tracker_refs: []
planning_base_branch: feat/feature-alias-removal
merge_target_branch: feat/feature-alias-removal
branch_strategy: Planning artifacts for this mission were generated on feat/feature-alias-removal. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/feature-alias-removal unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
agent: claude
shell_pid: '1802586'
history:
- timestamp: '2026-06-26T00:56:06Z'
  agent: system
  action: Prompt generated via spec-kitty tasks
agent_profile: python-pedro
authoritative_surface: tests/contract/
create_intent: []
execution_mode: code_change
owned_files:
- tests/contract/test_terminology_guards.py
- tests/contract/test_feature_alias_scope.py
- tests/specify_cli/cli/test_no_visible_feature_alias.py
role: implementer
tags: []
---

# Work Package Prompt: WP04 – Terminology guard extension and existing test updates

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Extend `INSCOPE_FEATURE_FREE_FILES` with all 8 in-scope command file paths so any future
reintroduction of `"--feature"` in those files fails CI. Update `test_feature_alias_scope.py`
to reflect that merge now also rejects `--feature`. Add a zero-feature-flags assertion to
`test_no_visible_feature_alias.py`. All updates must be test fixes/extensions, NOT deletions
(NFR-001).

**Files in scope (ONLY these three):**
- `tests/contract/test_terminology_guards.py`
- `tests/contract/test_feature_alias_scope.py`
- `tests/specify_cli/cli/test_no_visible_feature_alias.py`

---

## Context

**Current state of `test_terminology_guards.py`:**
- Contains `INSCOPE_FEATURE_FREE_FILES` with 10 file paths (the previously-cleaned internal
  files from PR #1985).
- After WP01-WP03, all 8 user-facing files are also clean. Extend the tuple to 18 entries.

**Current state of `test_feature_alias_scope.py`:**
- Contains assertions that `merge` still accepts `--feature` (it was out of scope in a prior mission).
- The 3 merge-specific tests must FLIP direction — they now assert merge REJECTS `--feature`.
- Also contains `_INSCOPE_FILES` tuple — update to include all 8 newly-cleaned files.
- DO NOT DELETE any tests. Update them (NFR-001).

**Current state of `test_no_visible_feature_alias.py`:**
- Contains `test_every_feature_flag_is_hidden` — currently passes because remaining `--feature`
  flags were `hidden=True`. After WP01-WP03, no `--feature` flags exist at all, so this test
  passes trivially.
- Add a NEW test `test_zero_feature_flags_exist_cli_wide` that asserts the CLI tree has zero
  `--feature` Typer parameters (not just zero visible ones).

**8 in-scope file paths** (to add to both `INSCOPE_FEATURE_FREE_FILES` and `_INSCOPE_FILES`):
```
src/specify_cli/cli/commands/implement.py
src/specify_cli/cli/commands/merge.py
src/specify_cli/cli/commands/next_cmd.py
src/specify_cli/cli/commands/research.py
src/specify_cli/cli/commands/context.py
src/specify_cli/cli/commands/accept.py
src/specify_cli/cli/commands/lifecycle.py
src/specify_cli/cli/commands/mission_type.py
```

---

## Subtask T018 — Extend `INSCOPE_FEATURE_FREE_FILES` in test_terminology_guards.py

**Purpose**: Add the 8 in-scope file paths to `INSCOPE_FEATURE_FREE_FILES` so the terminology
guard catches any future reintroduction of `"--feature"` in these files (FR-007).

**Steps:**
1. Open `tests/contract/test_terminology_guards.py`.
2. Find the `INSCOPE_FEATURE_FREE_FILES` tuple/set definition (currently 10 entries).
3. Add all 8 in-scope paths listed in the Context section above. Use the same path format
   as the existing entries (likely relative to repo root, e.g., `"src/specify_cli/cli/commands/implement.py"`).
4. Run the guard test to confirm it passes with the 8 newly-clean files:
   ```bash
   pytest tests/contract/test_terminology_guards.py -v -k "feature_free"
   ```

**Validation:**
- Test passes.
- Manually adding `"--feature"` to `implement.py` and re-running the test causes it to fail;
  then revert.

---

## Subtask T019 — Flip merge assertions in test_feature_alias_scope.py

**Purpose**: The three merge-specific tests in `test_feature_alias_scope.py` currently assert
that merge ACCEPTS `--feature`. After WP01, merge REJECTS `--feature`. Flip the assertions
(do NOT delete the tests — NFR-001).

**Steps:**
1. Open `tests/contract/test_feature_alias_scope.py`.
2. Find and update the `_INSCOPE_FILES` tuple (or equivalent): add the 8 new in-scope file
   paths to ensure scope consistency.
3. Find the three merge-specific test functions. They likely look like:
   - `test_merge_still_accepts_feature_alias` — rename (or update docstring) to reflect the
     new behavior; change assertion from "accepts" to "rejects with exit 2 / No such option".
   - `test_merge_feature_and_mission_both_accepted` — update: `--feature` is now rejected;
     `--mission` still works.
   - `test_merge_feature_alias_is_hidden_in_cli_introspection` — update: merge now has NO
     `--feature` param at all (not hidden, not visible — absent).
4. For each updated test, update the assertion to match the new expected behavior:
   - Exit code 2.
   - `"No such option: --feature"` in output (Typer's native unknown-option message).
   - Or: merge's `--help` no longer lists `--feature` at all.

**Example flip for test_merge_still_accepts_feature_alias:**
```python
# BEFORE (old behavior):
result = runner.invoke(app, ["merge", "--feature", "some-slug"])
assert result.exit_code == 0  # or asserts no error

# AFTER (new behavior):
result = runner.invoke(app, ["merge", "--feature", "some-slug"])
assert result.exit_code == 2
assert "No such option" in result.output or "--feature" in result.output
```

**Validation:**
- `pytest tests/contract/test_feature_alias_scope.py -v` → all tests pass.
- Zero tests deleted from this file.

---

## Subtask T020 — Add zero-feature-flags assertion to test_no_visible_feature_alias.py

**Purpose**: Replace or supplement the "all `--feature` flags are hidden" test with a stronger
assertion: zero `--feature` Typer parameters exist anywhere in the CLI tree (FR-009).

**Steps:**
1. Open `tests/specify_cli/cli/test_no_visible_feature_alias.py`.
2. Find `test_every_feature_flag_is_hidden`. Do NOT delete it — it now passes trivially
   (no `--feature` flags exist to be visible or hidden). Add a docstring explaining this.
3. Add a NEW test function `test_zero_feature_flags_exist_cli_wide`:
   ```python
   def test_zero_feature_flags_exist_cli_wide():
       """After alias removal, no --feature Typer option should exist anywhere in the CLI."""
       from typer.testing import CliRunner
       from specify_cli.cli.main import app  # or wherever the top-level app lives

       # Walk the CLI tree and collect all option names
       def collect_options(command, prefix=""):
           options = []
           if hasattr(command, "params"):
               for param in command.params:
                   options.extend(param.opts)
           if hasattr(command, "commands"):
               for name, sub in command.commands.items():
                   options.extend(collect_options(sub, prefix + name + " "))
           return options

       all_options = collect_options(app)
       feature_options = [o for o in all_options if o == "--feature"]
       assert feature_options == [], (
           f"Found {len(feature_options)} '--feature' option(s) in CLI tree: "
           f"{feature_options}. All --feature aliases must be removed."
       )
   ```
   Adjust the import path if `app` is not at `specify_cli.cli.main`.

**Validation:**
- `pytest tests/specify_cli/cli/test_no_visible_feature_alias.py -v` → both tests pass.
- Adding a `--feature` option back to any command causes `test_zero_feature_flags_exist_cli_wide`
  to fail.

---

## Branch Strategy

```
planning branch: feat/feature-alias-removal
merge target:    feat/feature-alias-removal
depends on:      WP03 (all 8 source files cleaned first)
```

---

## Definition of Done

- [ ] `pytest tests/contract/test_terminology_guards.py -v` passes.
- [ ] `pytest tests/contract/test_feature_alias_scope.py -v` passes; zero tests deleted.
- [ ] `pytest tests/specify_cli/cli/test_no_visible_feature_alias.py -v` passes.
- [ ] `INSCOPE_FEATURE_FREE_FILES` has 18 entries (10 original + 8 new).
- [ ] `test_zero_feature_flags_exist_cli_wide` function exists and passes.
- [ ] No test deletions in any of the three files.

## Risks

- `test_feature_alias_scope.py`'s `_INSCOPE_FILES` tuple may need to stay in sync with
  `INSCOPE_FEATURE_FREE_FILES` — if they diverge, the cross-check assertion may fail.
- The CLI tree walker in `test_zero_feature_flags_exist_cli_wide` may need adjusting if the
  top-level app import path is non-standard. Look at the existing test in the same file for
  the correct import.

## Reviewer Guidance

1. Verify no test was deleted — only assertions flipped or new tests added.
2. Confirm `INSCOPE_FEATURE_FREE_FILES` now has exactly 18 entries.
3. Confirm the merge test assertions now assert rejection (exit 2, "No such option"), not acceptance.
4. Confirm `test_zero_feature_flags_exist_cli_wide` covers the full CLI tree (not just a subset).

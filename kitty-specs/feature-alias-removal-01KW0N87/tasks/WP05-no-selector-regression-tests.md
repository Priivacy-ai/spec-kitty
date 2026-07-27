---
work_package_id: WP05
title: No-selector regression tests (FR-008)
dependencies:
- WP04
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: feat/feature-alias-removal
merge_target_branch: feat/feature-alias-removal
branch_strategy: Planning artifacts for this mission were generated on feat/feature-alias-removal. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/feature-alias-removal unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
agent: claude
shell_pid: '1914606'
history:
- timestamp: '2026-06-26T00:56:06Z'
  agent: system
  action: Prompt generated via spec-kitty tasks
agent_profile: python-pedro
authoritative_surface: tests/contract/
create_intent:
- tests/contract/test_no_selector_guard.py
execution_mode: code_change
owned_files:
- tests/contract/test_no_selector_guard.py
role: implementer
tags: []
---

# Work Package Prompt: WP05 – No-selector regression tests (FR-008)

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Create `tests/contract/test_no_selector_guard.py` with 8 focused regression tests — one per
in-scope command — that lock the no-selector behavior and prevent the PR #1985 `TypeError`
regression class from recurring.

Each test asserts:
1. `result.exit_code != 0` (prefer `== 2`)
2. `"--mission" in result.output or "required" in result.output.lower()`
3. `not isinstance(result.exception, TypeError)`

**File created by this WP:**
- `tests/contract/test_no_selector_guard.py` (new file)

---

## Context

**Contract spec** (from `contracts/no-selector-error-contract.md`):

| Command | Invocation | Expected exit code |
|---------|-----------|-------------------|
| `spec-kitty implement <WP>` | `["implement", "WP01"]` — no `--mission` | 2 |
| `spec-kitty merge` | `["merge"]` — no `--mission` | 2 |
| `spec-kitty next` | `["next"]` — no `--mission` | 2 |
| `spec-kitty research` | `["research"]` — no `--mission` | 2 |
| `spec-kitty context mission-resolve` | `["context", "mission-resolve"]` — no `--mission` | 2 |
| `spec-kitty accept` | `["accept"]` — no `--mission` | 2 |
| `spec-kitty lifecycle plan` | `["lifecycle", "plan"]` — no `--mission` | 2 |
| `spec-kitty lifecycle tasks` | `["lifecycle", "tasks"]` — no `--mission` | 2 |
| `spec-kitty mission-type current` | `["mission-type", "current"]` — no `--mission`, run from `tmp_path` | 2 |

**Important invocation notes:**
- `implement` requires a positional `wp_id` argument; pass `"WP01"` (a valid WP ID format).
  The test is checking that the missing `--mission` produces an error, not that WP01 doesn't exist.
- `lifecycle plan` and `lifecycle tasks` are sub-commands; invoke as
  `runner.invoke(app, ["lifecycle", "plan"])`.
- `mission-type current` without `--mission` and without a project context: run from a temp dir
  that has no `.kittify/` to prevent auto-detection from succeeding.

**Test file structure:**
```python
# tests/contract/test_no_selector_guard.py
"""Regression tests: every in-scope command exits cleanly on no --mission (FR-008)."""
import pytest
from typer.testing import CliRunner
from specify_cli.cli.main import app  # adjust if needed

runner = CliRunner()

def _assert_no_selector_contract(result):
    """Assert the no-selector-error contract for any command."""
    assert result.exit_code != 0, f"Expected non-zero exit, got {result.exit_code}"
    assert not isinstance(result.exception, TypeError), (
        f"Got TypeError (traceback risk): {result.exception}"
    )
    assert (
        "--mission" in result.output
        or "required" in result.output.lower()
        or "error" in result.output.lower()
    ), f"No user-readable error in output: {result.output!r}"
```

---

## Subtask T021 — Create file and add tests for `implement` and `merge`

**Purpose**: Scaffold the test file and add the first two regression tests.

**Steps:**
1. Create `tests/contract/test_no_selector_guard.py` with the structure from the Context section.
2. Add `test_implement_no_mission_exits_cleanly`:
   ```python
   def test_implement_no_mission_exits_cleanly():
       """implement WP01 without --mission must exit non-zero cleanly (no TypeError)."""
       result = runner.invoke(app, ["implement", "WP01"])
       _assert_no_selector_contract(result)
   ```
3. Add `test_merge_no_mission_exits_cleanly`:
   ```python
   def test_merge_no_mission_exits_cleanly():
       """merge without --mission must exit non-zero cleanly."""
       result = runner.invoke(app, ["merge"])
       _assert_no_selector_contract(result)
   ```

**Note on `implement` test**: The test invokes `implement WP01` with no `--mission`. The
no-selector guard in `detect_feature_context` should trigger. If `implement` requires a project
directory to exist, wrap the invocation:
```python
import os, tempfile
with tempfile.TemporaryDirectory() as tmp:
    result = runner.invoke(app, ["implement", "WP01"], catch_exceptions=False)
```
(Use `catch_exceptions=True` — the default — so that unexpected exceptions are captured in
`result.exception` rather than propagating.)

**Validation:**
- `pytest tests/contract/test_no_selector_guard.py::test_implement_no_mission_exits_cleanly -v` → pass.
- `pytest tests/contract/test_no_selector_guard.py::test_merge_no_mission_exits_cleanly -v` → pass.

---

## Subtask T022 — Add tests for `next` and `research`

**Purpose**: Cover the two commands cleaned in WP02 (next_cmd.py, research.py).

**Steps:**
1. Add `test_next_no_mission_exits_cleanly`:
   ```python
   def test_next_no_mission_exits_cleanly():
       """next without --mission must exit non-zero cleanly."""
       result = runner.invoke(app, ["next"])
       _assert_no_selector_contract(result)
   ```
2. Add `test_research_no_mission_exits_cleanly`:
   ```python
   def test_research_no_mission_exits_cleanly():
       """research without --mission must exit non-zero cleanly."""
       result = runner.invoke(app, ["research"])
       _assert_no_selector_contract(result)
   ```

**Validation:**
- Both tests pass with `pytest tests/contract/test_no_selector_guard.py -k "next or research" -v`.

---

## Subtask T023 — Add tests for `context mission-resolve` and `accept`

**Purpose**: Cover context.py and accept.py cleaned in WP02.

**Steps:**
1. Add `test_context_mission_resolve_no_mission_exits_cleanly`:
   ```python
   def test_context_mission_resolve_no_mission_exits_cleanly():
       """context mission-resolve without --mission must exit non-zero cleanly."""
       result = runner.invoke(app, ["context", "mission-resolve"])
       _assert_no_selector_contract(result)
   ```
2. Add `test_accept_no_mission_exits_cleanly`:
   ```python
   def test_accept_no_mission_exits_cleanly():
       """accept without --mission must exit non-zero cleanly."""
       result = runner.invoke(app, ["accept"])
       _assert_no_selector_contract(result)
   ```
   Note: `accept` uses `typer.Exit(2)` (after WP02's D-02 fix), so `result.exit_code` should be 2.

**Validation:**
- Both tests pass.

---

## Subtask T024 — Add tests for `lifecycle plan`, `lifecycle tasks`, `mission-type current`

**Purpose**: Cover lifecycle.py and mission_type.py cleaned in WP03. Nine tests total
(8 commands, but `lifecycle plan` and `lifecycle tasks` are distinct sub-commands, so
9 commands = 9 tests counting `mission-type current`).

Wait — re-count: the contract table has 8 entries + `lifecycle tasks` is included via
`lifecycle plan`/`lifecycle tasks` (2 tests) plus `mission-type current` (1 test). This
subtask covers the remaining 3 tests to bring the total to 9 (or adjust to match exactly
the 8-command contract: implement, merge, next, research, context, accept, lifecycle plan,
lifecycle tasks = 8; mission-type current is a bonus 9th per the contract table).

**Steps:**
1. Add `test_lifecycle_plan_no_mission_exits_cleanly`:
   ```python
   def test_lifecycle_plan_no_mission_exits_cleanly():
       """lifecycle plan without --mission must exit non-zero cleanly."""
       result = runner.invoke(app, ["lifecycle", "plan"])
       _assert_no_selector_contract(result)
   ```
2. Add `test_lifecycle_tasks_no_mission_exits_cleanly`:
   ```python
   def test_lifecycle_tasks_no_mission_exits_cleanly():
       """lifecycle tasks without --mission must exit non-zero cleanly."""
       result = runner.invoke(app, ["lifecycle", "tasks"])
       _assert_no_selector_contract(result)
   ```
3. Add `test_mission_type_current_no_mission_exits_cleanly` using a tmp_path to prevent
   auto-detection from succeeding:
   ```python
   def test_mission_type_current_no_mission_exits_cleanly(tmp_path, monkeypatch):
       """mission-type current without --mission and without project must exit non-zero cleanly."""
       monkeypatch.chdir(tmp_path)
       result = runner.invoke(app, ["mission-type", "current"])
       _assert_no_selector_contract(result)
   ```
   If `monkeypatch.chdir` is not available (non-pytest context), use `os.chdir(tmp_path)` with
   cleanup in a fixture.

**Validation:**
- `pytest tests/contract/test_no_selector_guard.py -v` → all 9 tests pass.

---

## Branch Strategy

```
planning branch: feat/feature-alias-removal
merge target:    feat/feature-alias-removal
depends on:      WP04 (terminology guard must be green before adding new contract tests)
```

---

## Definition of Done

- [ ] `tests/contract/test_no_selector_guard.py` exists.
- [ ] `pytest tests/contract/test_no_selector_guard.py -v` → all tests pass (9 tests: 8 in-scope commands + mission-type current).
- [ ] Each test asserts: `exit_code != 0`, `not isinstance(exception, TypeError)`, and a readable message in output.
- [ ] `ruff check tests/contract/test_no_selector_guard.py` → 0 errors.
- [ ] `mypy tests/contract/test_no_selector_guard.py` → 0 errors.

## Risks

- `implement WP01` may check for a valid project directory before reaching the no-selector
  guard. If it does, the test may exit with a different error. Assert `exit_code != 0` instead
  of `== 2` for this test if needed, but still assert no TypeError.
- `mission-type current` auto-detect: if the test runner's CWD happens to be inside a project
  with a `.kittify/` directory, auto-detect may succeed and bypass the guard. Use `monkeypatch.chdir`
  to a clean `tmp_path`.
- If the CLI's `app` import path is different from `specify_cli.cli.main`, look at existing
  tests in the same `tests/contract/` directory for the correct import.

## Reviewer Guidance

1. Confirm each test invocation format matches the contract table (correct sub-command nesting).
2. Confirm `_assert_no_selector_contract` helper is used consistently.
3. Confirm the `mission-type current` test uses a clean tmp directory.
4. Confirm no test calls `catch_exceptions=False` (which would cause uncaught exceptions to
   propagate and break the TypeError assertion).

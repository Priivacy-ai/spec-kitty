---
work_package_id: WP03
title: Caller Integration Tests and Suite Validation
dependencies:
- WP01
- WP02
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-009
- FR-010
- NFR-001
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: feat/locate-project-root-consolidation
merge_target_branch: feat/locate-project-root-consolidation
branch_strategy: Planning artifacts for this mission were generated on feat/locate-project-root-consolidation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/locate-project-root-consolidation unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
agent: "claude:sonnet-4-6:reviewer-riley:reviewer"
shell_pid: "83941"
history:
- date: '2026-06-15'
  event: Created during /spec-kitty.tasks by Architect Alphonso
agent_profile: implementer-ivan
authoritative_surface: tests/specify_cli/cli/
create_intent:
- tests/specify_cli/cli/test_helpers.py
- tests/specify_cli/cli/commands/test_lint.py
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/test_helpers.py
- tests/specify_cli/cli/commands/test_lint.py
- tests/specify_cli/compat/test_planner.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Add targeted integration-level tests for two of the four affected callers — `get_project_root_or_exit` (worktree scenario) and `lint_command` (`SPECIFY_REPO_ROOT` scenario) — then run the full suite to confirm zero regressions and ≥90% coverage for all changed files.

**Prerequisites:** WP01 (shim) and WP02 (unit tests) must be complete before this WP's validation in T009 is meaningful.

---

## Context

**Coverage gap (Stenographer, 2026-06-15):**
- `get_project_root_or_exit` is universally mocked in all existing tests (8 locations across 4 test files). It has never been tested with a real worktree filesystem.
- `lint_command` has no test for `SPECIFY_REPO_ROOT` behavior.
- Without these tests, the shim from WP01 is invisible to the test suite — a future reversion would pass all tests.

**Active failures this closes (Matrix-Maker rows 3 and 4):**
- Row 3: `get_project_root_or_exit` exits 1 from a git worktree (no `SPECIFY_REPO_ROOT`) — any `spec-kitty status`, `merge`, `review` command fails from a worktree
- Row 4: `lint_command` falls back to `Path.cwd()` when `SPECIFY_REPO_ROOT` is set and CWD is outside the project — `ruff`/`mypy` run with the wrong working directory

---

## Branch Strategy

**Planning base branch:** `feat/locate-project-root-consolidation`  
**Final merge target:** `feat/locate-project-root-consolidation`  
**Execution workspace:** allocated per `lanes.json` — resolve via `spec-kitty agent action implement WP03 --agent claude`.

---

## Subtask T007 — Add test_get_project_root_or_exit_succeeds_in_worktree

**Purpose:** Verify that `get_project_root_or_exit` returns the main repo root (does not call `typer.Exit`) when the caller is in a git worktree and the main repo has `.kittify`.

**File:** `tests/specify_cli/cli/test_helpers.py` (create if absent; if `tests/specify_cli/cli/` does not exist, use the nearest existing test file for `cli/helpers.py`)

**Step 1 — Find or create the test file:**
```bash
find tests/ -name "test_helpers.py" | head -5
find tests/ -name "*helper*" | head -5
```
If `tests/specify_cli/cli/test_helpers.py` exists, add to it. If it doesn't, create it.

**Step 2 — Read `src/specify_cli/cli/helpers.py`** to understand `get_project_root_or_exit`'s signature and error behavior before writing the test.

**Test to add:**
```python
import pytest
from pathlib import Path
from specify_cli.cli.helpers import get_project_root_or_exit


def test_get_project_root_or_exit_succeeds_in_worktree(tmp_path: Path) -> None:
    """get_project_root_or_exit returns main repo root when called from a git worktree."""
    # Build fake main repo with .kittify
    main_repo = tmp_path / "main_repo"
    (main_repo / ".kittify").mkdir(parents=True)
    worktrees_dir = main_repo / ".git" / "worktrees" / "test_lane"
    worktrees_dir.mkdir(parents=True)

    # Build fake worktree — .git is a file pointer
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {worktrees_dir}\n")

    # Call without mocking — exercises the real delegation chain
    result = get_project_root_or_exit(start=worktree)
    assert result == main_repo
```

**Important:** `get_project_root_or_exit` calls `typer.Exit(1)` when it cannot find the root. If the function signature does not accept a `start` parameter, check how the existing function is defined — you may need to `monkeypatch` the `locate_project_root` it calls internally, OR verify that `get_project_root_or_exit` passes its argument through to `locate_project_root`. Do not mock `locate_project_root` itself — that would defeat the purpose.

**Steps:**
1. Read `src/specify_cli/cli/helpers.py` to understand `get_project_root_or_exit` signature.
2. If the function accepts `start: Path | None = None`, use it directly as shown above.
3. If it does not, check if there's a way to pass the start via the `locate_project_root` call inside.
4. Run: `pytest tests/specify_cli/cli/test_helpers.py::test_get_project_root_or_exit_succeeds_in_worktree -v`

**Catching typer.Exit:** If `get_project_root_or_exit` raises `SystemExit` (which `typer.Exit` does), the test will fail with an unexpected exception. If the worktree construction is correct and WP01 is in place, the function should NOT raise — it should return the main repo path. A `SystemExit` in this test means the shim is not working correctly.

**Validation:**
- [ ] Test passes without mocking `locate_project_root`
- [ ] `result == main_repo`
- [ ] Test does not catch or suppress `SystemExit` — let it fail loudly if the shim is broken

---

## Subtask T008 — Add test_lint_uses_spec_repo_root_as_cwd

**Purpose:** Verify that `lint_command` uses `SPECIFY_REPO_ROOT` as the working directory for `ruff`/`mypy` subprocess calls when the env var is set and CWD is outside the project.

**File:** `tests/specify_cli/cli/commands/test_lint.py` (create if absent)

**Step 1 — Find or create the test file:**
```bash
find tests/ -name "test_lint.py" | head -5
ls tests/specify_cli/cli/commands/ 2>/dev/null || echo "directory not found"
```
If the file exists, add to it. If not, create it at `tests/specify_cli/cli/commands/test_lint.py`.

**Step 2 — Read `src/specify_cli/cli/commands/lint.py`** to understand how `locate_project_root` result is used as `cwd=` in the subprocess call.

**Test to add:**
```python
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_lint_uses_spec_repo_root_as_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """lint_command uses SPECIFY_REPO_ROOT as subprocess cwd, not Path.cwd()."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(project_root))

    captured_calls: list[dict] = []

    def mock_subprocess_run(*args: object, **kwargs: object) -> MagicMock:
        captured_calls.append({"args": args, "kwargs": kwargs})
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        # Import and call lint_command — adjust import path to match actual location
        from specify_cli.cli.commands.lint import lint_command
        try:
            lint_command()
        except SystemExit:
            pass  # Acceptable if lint_command calls typer.Exit on success

    # At least one subprocess call should have used the SPECIFY_REPO_ROOT path as cwd
    assert any(
        str(call["kwargs"].get("cwd") or "") == str(project_root)
        or str(project_root) in str(call)
        for call in captured_calls
    ), f"Expected cwd={project_root} in subprocess calls, got: {captured_calls}"
```

**Steps:**
1. Read `src/specify_cli/cli/commands/lint.py` to understand the exact `subprocess.run` call signature, including which module path to patch.
2. Adjust the `patch` target to match the actual import path used in `lint.py` (e.g., `specify_cli.cli.commands.lint.subprocess.run` or `subprocess.run`).
3. Adjust the `lint_command()` call to match its actual signature (it may require CLI arguments via `typer.testing.CliRunner`).
4. Run: `pytest tests/specify_cli/cli/commands/test_lint.py::test_lint_uses_spec_repo_root_as_cwd -v`

**Alternate approach using CliRunner (if `lint_command` is a typer command):**
```python
from typer.testing import CliRunner
from specify_cli.cli.commands.lint import app  # adjust to actual export

def test_lint_uses_spec_repo_root_as_cwd(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(project_root))
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        runner = CliRunner()
        runner.invoke(app, [])
    
    # Verify cwd
    for call in mock_run.call_args_list:
        cwd = call.kwargs.get("cwd") or (call.args[1] if len(call.args) > 1 else None)
        if cwd == project_root:
            break
    else:
        pytest.fail(f"subprocess.run was never called with cwd={project_root}")
```

**Validation:**
- [ ] Test passes with WP01 shim in place
- [ ] `monkeypatch.setenv` is used (not `os.environ` mutation)
- [ ] At least one `subprocess.run` call had `cwd=project_root`
- [ ] Test fails if `SPECIFY_REPO_ROOT` is unset (regression guard)

---

## Subtask T009 — Full suite validation

**Purpose:** Run the complete test suite in parallel to confirm zero regressions and ≥90% coverage for all files changed by this mission.

**Steps:**
1. Run the full suite:
   ```bash
   PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider -q 2>&1 | tail -30
   ```
2. If failures: diagnose. Any failure in an existing test that was passing before this mission is a regression — do not merge until it is fixed.
3. Check coverage for changed files:
   ```bash
   pytest tests/runtime/test_project_resolver.py tests/specify_cli/cli/test_helpers.py tests/specify_cli/cli/commands/test_lint.py \
     --cov=src/specify_cli/core/project_resolver \
     --cov-report=term-missing \
     -q
   ```
4. If coverage < 90% for `project_resolver.py`: add the missing test case (likely the `SPECIFY_REPO_ROOT` path doesn't exist scenario).
5. Run `mypy --strict` on all new/modified test files:
   ```bash
   .venv/bin/mypy --strict tests/runtime/test_project_resolver.py
   .venv/bin/mypy --strict tests/specify_cli/cli/test_helpers.py
   .venv/bin/mypy --strict tests/specify_cli/cli/commands/test_lint.py
   ```

**Parallelism note:** Real-port and daemon tests run serially. If `test_orphan_sweep.py` or similar fails with a port conflict, run them separately: `pytest tests/sync/test_orphan_sweep.py -n0 -q`.

**Validation:**
- [ ] `pytest tests/ -n auto --dist loadfile` exits 0 with no new failures
- [ ] Coverage ≥ 90% for `src/specify_cli/core/project_resolver.py`
- [ ] `mypy --strict` passes on all new/modified test files
- [ ] No test was added that mocks `locate_project_root` in a way that defeats the purpose of this mission

---

## Subtask T010 — Add test_planner_default_resolver_in_worktree

**Purpose:** Verify that `plan()` with the default `project_root_resolver` (the `project_resolver.locate_project_root` shim) correctly classifies project state when the CWD is inside a git worktree. This is the only test that exercises FR-007 — the planner's Matrix-Maker row 9 failure — and makes a future shim reversion immediately detectable.

**File:** `tests/specify_cli/compat/test_planner.py` (add to existing file)

**Step 1 — Read the existing test helpers:**
```bash
# Check for _make_invocation and _make_project_root_resolver at the top of the file
head -120 tests/specify_cli/compat/test_planner.py
```

**Step 2 — Add the test** (it uses the existing `_make_invocation` helper):
```python
import pytest
from pathlib import Path
from specify_cli.compat.planner import plan, ProjectState


def test_planner_default_resolver_in_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """plan() with default project_root_resolver classifies project correctly from a worktree.

    Regression guard for FR-007 / issue #1971: before the shim, calling plan()
    from a worktree caused _scan_project to receive None root → NO_PROJECT.
    """
    # Build fake main repo with .kittify and a minimal schema file
    main_repo = tmp_path / "main_repo"
    kittify = main_repo / ".kittify"
    kittify.mkdir(parents=True)
    # Write a minimal schema_version so ProjectStatus has something to report
    (kittify / "schema_version").write_text("3")

    # Build fake worktree structure
    worktrees_dir = main_repo / ".git" / "worktrees" / "test_lane"
    worktrees_dir.mkdir(parents=True)
    (main_repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n")

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {worktrees_dir}\n")

    # Simulate being in the worktree (no SPECIFY_REPO_ROOT — tests worktree path)
    monkeypatch.chdir(worktree)
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)

    invocation = _make_invocation()
    # Call plan() with NO project_root_resolver → exercises the default shim
    result = plan(invocation)

    assert result.project_status.state != ProjectState.NO_PROJECT, (
        f"plan() resolved NO_PROJECT from worktree; shim may not be delegating "
        f"to paths.locate_project_root. project_root={result.project_status.project_root}"
    )
```

**Important notes:**
- `_make_invocation` is already defined in `test_planner.py` around line 91 — do not re-define it.
- Do NOT pass `project_root_resolver` to `plan()` — that's the whole point of this test.
- The test exercises the shim: `plan()` → `_plan_impl()` → `_scan_project(locate_project_root)` → `locate_project_root(worktree)` → `paths.locate_project_root` → worktree pointer → `main_repo`.
- If `paths.locate_project_root` checks for `.kittify/schema_version` or additional files beyond just `.kittify/`, adjust the fake repo setup accordingly. Read `src/specify_cli/core/paths.py` to confirm what the worktree scanner expects.

**Steps:**
1. Read `src/specify_cli/core/paths.py` worktree detection logic to confirm the exact `.git` file format and any additional `.kittify/` contents required.
2. Add the test above to `tests/specify_cli/compat/test_planner.py`.
3. Run: `pytest tests/specify_cli/compat/test_planner.py::test_planner_default_resolver_in_worktree -v`

**Validation:**
- [ ] Test passes with WP01 shim in place
- [ ] Test does NOT pass `project_root_resolver` to `plan()` — it must use the default
- [ ] `result.project_status.state != ProjectState.NO_PROJECT`
- [ ] `monkeypatch.chdir(worktree)` is used (not monkeypatching `Path.cwd`)
- [ ] `monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)` is present to isolate from CI env

---

## Definition of Done

- [ ] `tests/specify_cli/cli/test_helpers.py` contains `test_get_project_root_or_exit_succeeds_in_worktree` and it passes without mocking `locate_project_root`
- [ ] `tests/specify_cli/cli/commands/test_lint.py` contains `test_lint_uses_spec_repo_root_as_cwd` and it passes
- [ ] `tests/specify_cli/compat/test_planner.py` contains `test_planner_default_resolver_in_worktree` and it passes without passing `project_root_resolver` to `plan()`
- [ ] Full parallel suite exits 0 with zero new failures
- [ ] Coverage ≥ 90% for `src/specify_cli/core/project_resolver.py`
- [ ] `mypy --strict` passes on all new test files

## Risks

- **`get_project_root_or_exit` may not accept a `start` parameter.** If so, read the implementation carefully. It may call `locate_project_root()` with no argument, using `Path.cwd()` implicitly. In that case, `monkeypatch.chdir(worktree)` is the correct approach.
- **`lint_command` subprocess patch target.** If `lint.py` does `import subprocess` at module level and calls `subprocess.run`, patch `specify_cli.cli.commands.lint.subprocess.run`. If it does `from subprocess import run`, patch `specify_cli.cli.commands.lint.run`.
- **`typer.Exit` vs `SystemExit`.** Typer commands raise `SystemExit` when they call `Exit`. Tests calling `lint_command()` directly (not via `CliRunner`) should wrap with `pytest.raises(SystemExit)` or `CliRunner.invoke` (which catches it internally).

## Reviewer Guidance

- Confirm T007's test does NOT mock `locate_project_root` — the whole point is to exercise the real delegation chain
- Confirm T008 patches subprocess at the correct import path
- Confirm T009 shows zero new failures in the full suite output
- Confirm coverage report shows ≥ 90% for `project_resolver.py`
- Confirm T010 does NOT pass `project_root_resolver` to `plan()` — the test must exercise the default shim path, not an injected resolver

## Activity Log

- 2026-06-15T15:19:59Z – user – Unblocking WP03 to restart implementation; previous session moved to blocked during failed claim attempt
- 2026-06-15T15:59:07Z – claude – T007 T008 T009 T010 complete — caller integration tests pass; full suite clean; coverage 100% for project_resolver.py; mypy --strict clean on all new test files
- 2026-06-15T15:59:46Z – claude:sonnet-4-6:reviewer-riley:reviewer – shell_pid=83941 – Started review via action command
- 2026-06-15T16:04:41Z – user – shell_pid=83941 – Review passed: T007 exercises real delegation chain (no mock of locate_project_root); T008 patches at correct module path specify_cli.cli.commands.lint.subprocess.run and asserts both subprocess cwds equal SPECIFY_REPO_ROOT; T009 passes with 100% coverage on project_resolver.py (22/22 lines); T010 calls plan() with no project_root_resolver kwarg exercising the default shim; mypy --strict clean on all 3 new test files; ruff clean; no locate_project_root mocking defeats WP01 shim. Prior review-cycle-1.md rejection was a workflow reset artifact. kitty-specs/ net diff vs planning branch is zero — historical commits touched it for status transitions only.

---
work_package_id: WP08
title: Encoding + worktree + mission revalidation
dependencies:
- WP07
requirement_refs:
- C-007
- FR-014
- FR-016
- FR-017
- NFR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T046
- T047
- T048
- T049
- T050
- T051
history:
- timestamp: '2026-04-14T10:41:03Z'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/encoding.py
execution_mode: code_change
owned_files:
- src/specify_cli/encoding.py
- src/specify_cli/cli/__init__.py
- tests/regressions/test_issue_101_utf8_startup.py
- tests/regressions/test_issue_71_dashboard_empty.py
- tests/sync/test_issue_586_windows_import.py
- tests/core/test_worktree_symlink_fallback.py
- tests/mission/__init__.py
- tests/mission/test_active_mission_handle_windows.py
tags: []
---

# WP08 — Encoding + worktree + mission revalidation

## Branch strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: per-lane `.worktrees/windows-compatibility-hardening-01KP5R6K-lane-<id>/`.
- Implement command: `spec-kitty agent action implement WP08 --agent <name>`. Begin after WP07 is merged to main.

## Objective

Close the historical Windows regression tail by:
1. Enforcing UTF-8 at the CLI entrypoint on Windows (regression for #101).
2. Upgrading the simulated `fcntl`-import test (#586) to real native execution under `windows_ci`.
3. Adding a native regression test for dashboard-empty-on-Windows (#71).
4. Adding native tests for the worktree symlink-vs-copy fallback (`.kittify/memory`, `AGENTS.md`).
5. Adding native tests for the active-mission handle round-trip on Windows (no symlink support).

## Context

- **Spec IDs covered**: FR-014 (worktree + symlink fallback), FR-016 (curated Windows-critical suite contents), FR-017 (every fix has a native test), NFR-001 (cold-start regression ≤ 150 ms), SC-004 (every confirmed bug covered).
- **Research**: [`research.md` R-08, R-09](../research.md)

## Detailed subtasks

### T046 — UTF-8 enforcement at CLI entrypoint

**Purpose**: Prevent encoding crashes on Windows code pages (closes the #101 class).

**Steps**:
1. Create `src/specify_cli/encoding.py`:
   ```python
   """CLI startup encoding helpers.

   On Windows, forces UTF-8 stdout/stderr to avoid crashes on non-UTF-8 code
   pages when printing paths or status lines that contain non-ASCII characters.
   """
   from __future__ import annotations
   import sys


   def ensure_utf8_on_windows() -> None:
       """Reconfigure stdout/stderr to UTF-8 on Windows. No-op on POSIX."""
       if not sys.platform.startswith("win"):
           return
       for stream in (sys.stdout, sys.stderr):
           reconfigure = getattr(stream, "reconfigure", None)
           if reconfigure is None:
               continue
           try:
               reconfigure(encoding="utf-8", errors="replace")
           except (OSError, ValueError):
               # Stream may not be a TextIOWrapper (e.g. redirected). Safe to skip.
               continue
   ```
2. Open `src/specify_cli/cli/__init__.py`.
3. At the very top of the typer app initialization (before any command imports that might write to stdout), call:
   ```python
   from specify_cli.encoding import ensure_utf8_on_windows
   ensure_utf8_on_windows()
   ```
4. Do NOT set `PYTHONUTF8=1` programmatically — that's an environment-level concern (documented in CI workflow T040 and `docs/explanation/windows-state.md` in WP09).

**Validation**:
- T047 regression test runs under a simulated non-UTF-8 codepage and does not crash.

### T047 — Regression test for #101: UTF-8 startup on Windows [P]

**Purpose**: Reproduce #101 against pre-fix code; pass against post-fix code.

**Steps**:
1. Create `tests/regressions/test_issue_101_utf8_startup.py`:
   ```python
   import subprocess, sys, os
   from pathlib import Path
   import pytest


   @pytest.mark.windows_ci
   def test_cli_startup_under_non_utf8_codepage_does_not_crash(tmp_path):
       # Run a subprocess that emits a non-ASCII path via spec-kitty, under
       # an explicit legacy code page (windows-1252 "Latin-1").
       script = tmp_path / "smoke.py"
       script.write_text(
           'from specify_cli.encoding import ensure_utf8_on_windows\n'
           'ensure_utf8_on_windows()\n'
           'print("path: ñámé — café/Ω")\n',
           encoding="utf-8",
       )
       env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
       # Deliberately do NOT set PYTHONUTF8=1 — we are testing the in-process fix.
       env.pop("PYTHONUTF8", None)
       proc = subprocess.run(
           [sys.executable, str(script)],
           capture_output=True, text=False, env=env,
       )
       # Expect zero exit even though cp1252 can't encode all characters.
       # 'errors=replace' should have produced replacement chars, not a crash.
       assert proc.returncode == 0, (
           f"CLI startup crashed on non-UTF-8 codepage: stderr={proc.stderr!r}"
       )
   ```

**Validation**:
- Runs on `windows-latest`.

### T048 — Regression test for #71: dashboard non-empty on Windows [P]

**Purpose**: #71 was a symptom of Windows-specific IO/encoding bugs producing an empty dashboard response. Verify that a basic dashboard invocation on Windows returns non-empty output.

**Steps**:
1. Create `tests/regressions/test_issue_71_dashboard_empty.py`:
   ```python
   import pytest
   from typer.testing import CliRunner


   @pytest.mark.windows_ci
   def test_dashboard_returns_non_empty_on_windows(tmp_path, monkeypatch):
       # Set up a minimal fixture repo state so the dashboard has something
       # to render. Exact fixture shape depends on dashboard requirements;
       # consult src/specify_cli/cli/commands/dashboard.py for minimal inputs.
       monkeypatch.chdir(tmp_path)
       # Create a scaffolded mission directory if dashboard requires it
       mission_dir = tmp_path / "kitty-specs" / "demo-mission"
       mission_dir.mkdir(parents=True)
       (mission_dir / "spec.md").write_text("# Demo spec", encoding="utf-8")
       (mission_dir / "meta.json").write_text(
           '{"mission_id":"01XXXX","slug":"demo-mission","mission_slug":"demo-mission",'
           '"friendly_name":"demo","mission_type":"software-dev","target_branch":"main",'
           '"vcs":"git","created_at":"2026-04-14T00:00:00+00:00"}',
           encoding="utf-8",
       )

       from specify_cli.cli import app
       runner = CliRunner()
       result = runner.invoke(app, ["dashboard"])
       # Non-empty output = at least one non-whitespace character
       assert result.stdout.strip() != "", (
           f"Dashboard returned empty output on Windows. rc={result.exit_code} "
           f"stderr={result.stderr}"
       )
   ```
2. If the dashboard has a stronger fixture requirement (e.g. a specific config or repo structure), extend the fixture to meet it. Do NOT skip the test — the whole point of FR-017 is ending the "empty on Windows" regression class.

**Validation**:
- Runs on `windows-latest`.

### T049 — Upgrade `test_issue_586_windows_import.py` to native [P]

**Purpose**: The existing test is a simulated import check. Upgrade to real native import under `windows_ci`.

**Steps**:
1. Open existing `tests/sync/test_issue_586_windows_import.py`.
2. Current (simulated) form likely monkeypatches `sys.platform` or similar. Replace with a native import-and-exercise test:
   ```python
   import importlib
   import sys
   import pytest


   @pytest.mark.windows_ci
   def test_sync_daemon_imports_on_windows_without_fcntl():
       # On Windows, fcntl is not available. The sync daemon module must
       # import cleanly and expose its surface without depending on fcntl
       # at import time.
       import specify_cli.sync.daemon as daemon_mod
       importlib.reload(daemon_mod)
       assert hasattr(daemon_mod, "__name__")
       # Exercise the locking surface — must not raise ModuleNotFoundError
       if hasattr(daemon_mod, "acquire_lock"):
           # Call with a bogus path; we care about *import-time* errors, not
           # runtime acquisition success.
           try:
               daemon_mod.acquire_lock  # reference; do not invoke
           except ModuleNotFoundError as e:  # pragma: no cover
               pytest.fail(f"Windows sync/daemon has fcntl dependency: {e}")
   ```
3. Remove any `monkeypatch.setattr(sys, "platform", "win32")` or simulated import assertions — they're now covered by running on the real `windows-latest` runner.

**Validation**:
- Runs natively on `windows-latest`. Reproduces #586 against pre-fix code if the fix is reverted.

### T050 — Worktree symlink-vs-copy fallback on Windows [P]

**Purpose**: Native verification that the existing copy fallback for `.kittify/memory` and `AGENTS.md` actually works.

**Steps**:
1. Create `tests/core/test_worktree_symlink_fallback.py`:
   ```python
   import subprocess
   from pathlib import Path
   import pytest


   def _init_repo_with_kittify(repo: Path) -> None:
       subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
       subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=repo, check=True)
       subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
       kittify = repo / ".kittify" / "memory"
       kittify.mkdir(parents=True)
       (kittify / "memory.md").write_text("memory content", encoding="utf-8")
       (repo / "AGENTS.md").write_text("agents content", encoding="utf-8")
       subprocess.run(["git", "add", "."], cwd=repo, check=True)
       subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)


   @pytest.mark.windows_ci
   def test_worktree_materializes_kittify_memory_and_agents_on_windows(tmp_path):
       from specify_cli.core.worktree import create_worktree

       repo = tmp_path / "repo"
       repo.mkdir()
       _init_repo_with_kittify(repo)

       # Adjust invocation to match the real create_worktree signature
       wt_path = tmp_path / "repo-wt"
       create_worktree(repo, wt_path, branch="test-branch")

       # Both files must exist in the worktree and have readable content
       assert (wt_path / ".kittify" / "memory" / "memory.md").read_text(encoding="utf-8") == "memory content"
       assert (wt_path / "AGENTS.md").read_text(encoding="utf-8") == "agents content"


   @pytest.mark.windows_ci
   def test_worktree_on_path_with_spaces_on_windows(tmp_path):
       from specify_cli.core.worktree import create_worktree

       repo = tmp_path / "repo with spaces"
       repo.mkdir()
       _init_repo_with_kittify(repo)

       wt_path = tmp_path / "wt with spaces"
       create_worktree(repo, wt_path, branch="test-branch-spaces")
       assert (wt_path / "AGENTS.md").read_text(encoding="utf-8") == "agents content"
   ```
2. Adjust `create_worktree` invocation to match the real public API in `src/specify_cli/core/worktree.py`. The test body — existence + content of the two files — is the real assertion.

**Validation**:
- Runs on `windows-latest`.

### T051 — Active-mission handle round-trip on Windows [P]

**Purpose**: Verify `mission.py` active-mission fallback works on Windows without symlink support.

**Steps**:
1. Create `tests/mission/__init__.py` (empty).
2. Create `tests/mission/test_active_mission_handle_windows.py`:
   ```python
   import pytest


   @pytest.mark.windows_ci
   def test_active_mission_handle_round_trip_on_windows(tmp_path, monkeypatch):
       from specify_cli import mission as mission_mod

       # Adjust to match the real API in mission.py
       # Typical shape: set_active_mission(path, handle) + get_active_mission()
       monkeypatch.chdir(tmp_path)
       mission_mod.set_active_mission_handle("windows-compatibility-hardening-01KP5R6K")
       active = mission_mod.get_active_mission_handle()
       assert active == "windows-compatibility-hardening-01KP5R6K"
   ```
3. If `mission.py` uses different function names, adjust per the real API. The invariant is: write + read round-trips to the same value.

**Validation**:
- Runs on `windows-latest`.

## Definition of done

- [ ] All 6 subtasks complete.
- [ ] `pytest tests/regressions tests/core tests/mission tests/sync/test_issue_586_windows_import.py -v -m "not windows_ci"` passes on POSIX (tests without the marker continue to work).
- [ ] CLI cold-start on `windows-latest` does not regress by more than 150 ms vs. pre-mission baseline (NFR-001).
- [ ] `ensure_utf8_on_windows()` is called from the CLI entrypoint BEFORE any user-facing print.
- [ ] Commit message references FR-014, FR-016, FR-017, plus #101, #71, #586.

## Risks

- **`sys.stdout.reconfigure` availability**: Python 3.11+ supports it on `TextIOWrapper`. If the CLI's stdout is wrapped by rich or similar at the time `ensure_utf8_on_windows()` runs, the call may be a no-op. Run T047 to confirm it has teeth.
- **Dashboard fixture brittleness**: T048 may require a more elaborate fixture to actually exercise the dashboard's real rendering path. If it turns out the existing dashboard code is too tightly coupled to external state, scope a sub-fixture in this WP; do NOT skip the test.
- **`create_worktree` API**: The signature in `src/specify_cli/core/worktree.py` may differ from `(repo, wt_path, branch=...)` — use whatever the real API is.
- **Mission handle API**: `set_active_mission_handle` / `get_active_mission_handle` are placeholder names — use the real public functions.

## Reviewer guidance

Focus on:
1. Does `ensure_utf8_on_windows()` actually get called at the CLI entrypoint?
2. Does the #101 regression test genuinely reproduce the crash against pre-fix code? (Run against `main` HEAD before this WP's fix landed and confirm it fails.)
3. Do the worktree tests create a REAL git repo and worktree, or do they mock? (Must be real.)

Do NOT ask about:
- Full dashboard implementation — the test asserts non-empty output, not full correctness.
- Mission model redesign — out of scope; test asserts round-trip only.

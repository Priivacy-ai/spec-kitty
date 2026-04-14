---
work_package_id: WP04
title: Path messaging sweep + migrate_cmd wiring
dependencies:
- WP01
- WP02
requirement_refs:
- FR-006
- FR-012
- FR-013
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
history:
- timestamp: '2026-04-14T10:41:03Z'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/migrate_cmd.py
- src/specify_cli/cli/commands/agent/status.py
- tests/cli/test_migrate_cmd_messaging.py
- tests/cli/test_agent_status_messaging.py
- tests/audit/__init__.py
- tests/audit/test_no_legacy_path_literals.py
tags: []
---

# WP04 — Path messaging sweep + `migrate_cmd` wiring

## Branch strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: per-lane `.worktrees/windows-compatibility-hardening-01KP5R6K-lane-<id>/`.
- Implement command: `spec-kitty agent action implement WP04 --agent <name>`. Begin after WP01 and WP02 are merged to main.

## Objective

Replace every `~/.kittify` / `~/.spec-kitty` literal in CLI user-facing output with calls to `render_runtime_path(...)` from WP01. Wire `migrate_cmd.py` to invoke `migrate_windows_state()` from WP02 on first post-upgrade Windows invocation and emit the single-summary message contracted in [`contracts/cli-migrate.md`](../contracts/cli-migrate.md). Add a static audit test that blocks reintroduction of legacy literals in the CLI command tree.

## Context

- **Spec IDs covered**: FR-006 (migration surfaced via CLI), FR-012 (path rendering), FR-013 (specific stale-literal fixes in `migrate_cmd.py` and `agent/status.py`), SC-002 (zero legacy literals in Windows user-facing output).
- **Contracts**: [`contracts/cli-migrate.md`](../contracts/cli-migrate.md), [`contracts/cli-agent-status.md`](../contracts/cli-agent-status.md)
- **WP01 helper**: `render_runtime_path(path, *, for_user=True)`.
- **WP02 function**: `migrate_windows_state(dry_run=False) -> list[MigrationOutcome]`.

## Detailed subtasks

### T019 — Replace literals in `migrate_cmd.py`

**Purpose**: `spec-kitty migrate` user-facing output must be platform-correct on Windows.

**Steps**:
1. Read current `src/specify_cli/cli/commands/migrate_cmd.py`.
2. Grep inside the file for `~/.kittify`, `~/.spec-kitty`, `.config/spec-kitty` string literals in user-facing messages (console/echo/print/rich output).
3. For each hit, derive the underlying `Path` that the literal represents, then replace the literal with `render_runtime_path(path)`.
4. Import: `from specify_cli.paths import render_runtime_path, get_runtime_root`.
5. Do NOT change any filesystem-operating code. Only the rendered strings shown to the user.

**Validation**:
- T024 static audit test returns zero hits for legacy literals in this file.

### T020 — Replace literals in `agent/status.py` [P]

**Purpose**: Same as T019, for `spec-kitty agent status` output.

**Steps**:
1. Read current `src/specify_cli/cli/commands/agent/status.py`.
2. Grep for the same literals as T019.
3. Replace each with `render_runtime_path(...)` call.
4. Import: `from specify_cli.paths import render_runtime_path`.
5. Do NOT change status-data logic, only user-visible rendering.

**Validation**:
- T022 Windows-native test asserts no legacy substring in output.

### T021 — Wire migration auto-run into `migrate_cmd.py`

**Purpose**: First `spec-kitty migrate` invocation on Windows must pick up legacy state.

**Steps**:
1. Inside `migrate_cmd.py`, at the top of the main migrate command handler, add a Windows-only branch:
   ```python
   import sys
   from specify_cli.paths import render_runtime_path
   from specify_cli.paths.windows_migrate import migrate_windows_state

   if sys.platform == "win32":
       outcomes = migrate_windows_state()
       _render_windows_migration_summary(console, outcomes)
   ```
2. Implement `_render_windows_migration_summary(console, outcomes)` as a helper inside the module. Match the contracted output shapes in [`contracts/cli-migrate.md`](../contracts/cli-migrate.md). Use `render_runtime_path` for every path shown.
3. If `outcomes` is empty (non-Windows — shouldn't happen here but guard) skip rendering.
4. If any outcome has `status="error"` related to lock contention, exit 69 (EX_UNAVAILABLE). If `%LOCALAPPDATA%` unresolvable, exit 78 (EX_CONFIG). Otherwise continue with the rest of the command's work.
5. The Windows migration step must run BEFORE any code that reads tracker credentials, sync state, or daemon files — those reads in post-upgrade state would otherwise hit the wrong root.

**Validation**:
- T023 Windows-native tests cover happy-path + conflict-path output.

### T022 — Windows-native messaging test for `agent status` [P]

**Purpose**: Pin the "no legacy literals in Windows output" invariant.

**Steps**:
1. Create `tests/cli/test_agent_status_messaging.py`:
   ```python
   import pytest
   from typer.testing import CliRunner


   @pytest.mark.windows_ci
   def test_agent_status_no_legacy_literals_on_windows():
       from specify_cli.cli import app  # or the root typer app entrypoint
       runner = CliRunner()
       result = runner.invoke(app, ["agent", "status"])
       # Command may exit non-zero if there's no active mission; we only care
       # about the substring content.
       output = result.stdout + result.stderr
       assert "~/.kittify" not in output
       assert "~/.spec-kitty" not in output
       # On Windows, some AppData-style path MUST be present in the status output
       # when status has any path to report. If output is empty for the "no
       # mission" case, this assertion is relaxed.
       if "spec-kitty" in output.lower():
           # At least one path should be rendered in Windows-native form
           assert "\\" in output or ":" in output, (
               "Windows status output names spec-kitty but contains no native Windows path form."
           )
   ```
2. Adjust the `app` import path to match the real typer app entrypoint (likely `specify_cli.cli:app` or similar — verify in the execution worktree).

**Validation**:
- Runs on `windows-latest`.

### T023 — Windows-native messaging tests for `migrate_cmd` [P]

**Purpose**: Cover the happy-path (moved) and conflict-path (quarantined) output contracts.

**Steps**:
1. Create `tests/cli/test_migrate_cmd_messaging.py`:
   ```python
   import pytest
   import os
   from pathlib import Path
   from typer.testing import CliRunner


   @pytest.mark.windows_ci
   def test_migrate_windows_moved_output(tmp_path, monkeypatch):
       # Point HOME/LOCALAPPDATA into tmp; create a legacy dir with content
       monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
       monkeypatch.setenv("USERPROFILE", str(tmp_path / "User"))
       monkeypatch.setenv("HOME", str(tmp_path / "User"))
       legacy = tmp_path / "User" / ".spec-kitty"
       legacy.mkdir(parents=True)
       (legacy / "data.txt").write_text("legacy")

       from specify_cli.cli import app
       runner = CliRunner()
       result = runner.invoke(app, ["migrate"])
       # Expect zero exit and the "Migrated Spec Kitty runtime state" banner
       assert "Migrated Spec Kitty runtime state" in result.stdout
       assert "Canonical location:" in result.stdout
       assert "AppData" in result.stdout or "spec-kitty" in result.stdout.lower()
       assert "~/.kittify" not in result.stdout
       assert "~/.spec-kitty" not in result.stdout


   @pytest.mark.windows_ci
   def test_migrate_windows_quarantined_output(tmp_path, monkeypatch):
       monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
       monkeypatch.setenv("USERPROFILE", str(tmp_path / "User"))
       monkeypatch.setenv("HOME", str(tmp_path / "User"))
       legacy = tmp_path / "User" / ".spec-kitty"
       legacy.mkdir(parents=True)
       (legacy / "data.txt").write_text("legacy")
       dest = tmp_path / "LocalAppData" / "spec-kitty"
       dest.mkdir(parents=True)
       (dest / "existing.txt").write_text("existing")

       from specify_cli.cli import app
       runner = CliRunner()
       result = runner.invoke(app, ["migrate"])
       assert "Destination already contained state" in result.stdout or \
              "preserved as backups" in result.stdout
       assert ".bak-" in result.stdout
       assert "~/.kittify" not in result.stdout
       assert "~/.spec-kitty" not in result.stdout
   ```

**Validation**:
- Both tests run on `windows-latest` and assert contracted output shapes.

### T024 — Static audit test: no legacy literals in CLI command tree [P]

**Purpose**: Block any future PR that reintroduces `~/.kittify` or `~/.spec-kitty` user-facing literals in `src/specify_cli/cli/`.

**Steps**:
1. Create `tests/audit/__init__.py` (empty).
2. Create `tests/audit/test_no_legacy_path_literals.py`:
   ```python
   import pathlib
   import re


   def test_no_legacy_path_literals_in_cli_commands():
       root = pathlib.Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "cli"
       legacy_pattern = re.compile(r'["\'](~/\.kittify|~/\.spec-kitty)[/"\' ]')
       violations = []
       for py in root.rglob("*.py"):
           # Skip test/helper fixtures if any land under src/ by mistake
           text = py.read_text(encoding="utf-8")
           for i, line in enumerate(text.splitlines(), start=1):
               if legacy_pattern.search(line):
                   violations.append(f"{py.relative_to(root.parents[2])}:{i}: {line.strip()}")
       assert not violations, (
           "Legacy Windows-unsafe path literals reintroduced in CLI command tree:\n  "
           + "\n  ".join(violations)
       )
   ```
3. No `windows_ci` marker — this is a static check, runs everywhere.

**Validation**:
- Passes on current tree (after T019/T020 sweeps).
- If any future PR adds `"~/.kittify"` in `src/specify_cli/cli/`, this test fails.

## Definition of done

- [ ] All 6 subtasks complete.
- [ ] `pytest tests/cli/ tests/audit/ -v -m "not windows_ci"` passes on POSIX.
- [ ] `mypy --strict src/specify_cli/cli/commands/migrate_cmd.py src/specify_cli/cli/commands/agent/status.py` passes.
- [ ] Manual check: `grep -rn '~/\.kittify\|~/\.spec-kitty' src/specify_cli/cli/` returns zero hits.
- [ ] `migrate_cmd` Windows path executes `migrate_windows_state()` before any tracker/sync read.
- [ ] Commit message references FR-006, FR-012, FR-013, SC-002.

## Risks

- **Missed call-sites outside these two files**: The static audit test in T024 catches future regressions in `src/specify_cli/cli/` but not in other packages. WP09's repo-wide audit closes that gap.
- **Existing `migrate_cmd.py` complexity**: The command may already handle kernel-level migrations (for `~/.kittify` → `%LOCALAPPDATA%\kittify` semantics). Do not regress existing non-Windows migration behavior. Run the existing test suite against the change to verify.
- **Typer app import path**: The `from specify_cli.cli import app` line in tests assumes a specific entrypoint — adjust per actual module.

## Reviewer guidance

Focus on:
1. Does every user-facing `echo`/`print`/`rich` call in the two CLI files pass its path through `render_runtime_path`?
2. Is `migrate_windows_state()` invoked BEFORE any tracker/sync/daemon read in the `migrate` command flow?
3. Does the error-exit code match FR-008 expectations (69 for lock, 78 for unresolvable LOCALAPPDATA)?
4. Does the static audit test (T024) have zero false positives and zero false negatives on the touched files?

Do NOT ask about:
- Migration internals — that's WP02.
- Path helper internals — that's WP01.
- CI configuration — that's WP07.

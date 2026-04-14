---
work_package_id: WP02
title: Windows runtime state migration module
dependencies:
- WP01
requirement_refs:
- C-006
- C-007
- FR-006
- FR-007
- FR-008
- NFR-003
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude:opus-4.6:implementer:implementer"
shell_pid: "46585"
history:
- timestamp: '2026-04-14T10:41:03Z'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/paths/windows_migrate.py
execution_mode: code_change
owned_files:
- src/specify_cli/paths/windows_migrate.py
- tests/paths/test_windows_migrate.py
tags: []
---

# WP02 — Windows runtime state migration module

## Branch strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: per-lane `.worktrees/windows-compatibility-hardening-01KP5R6K-lane-<id>/` (resolved from `lanes.json`).
- Implement command: `spec-kitty agent action implement WP02 --agent <name>`. Begin only after WP01 is merged to main.

## Objective

Implement `src/specify_cli/paths/windows_migrate.py`: a one-time, idempotent migration that moves legacy Windows state from `~/.spec-kitty/`, `~/.kittify/`, and `~/.config/spec-kitty/` to `%LOCALAPPDATA%\spec-kitty\`. Destination wins: if the new root already contains state, the legacy tree is preserved by renaming it to `*.bak-<ISO-UTC-timestamp>`. Safe under concurrent CLI invocation via a `msvcrt`-based file lock.

## Context

- **Spec IDs covered**: FR-006 (migration), FR-007 (contention safety), FR-008 (actionable errors), NFR-003 (≤5 s / ≤100 files / ≤50 MB), NFR-004 (concurrent-access safety), C-006 (one-direction).
- **Research**: [`research.md` R-02, R-03](../research.md)
- **Data model**: [`data-model.md` E-02 `LegacyWindowsRoot`, E-03 `MigrationOutcome`](../data-model.md)
- **Contract**: [`contracts/cli-migrate.md`](../contracts/cli-migrate.md)
- **Key invariants from spec/research**:
  - Never deletes source or destination content.
  - Idempotent: second run on clean state is a no-op.
  - POSIX callers are no-ops (migration runs only on `sys.platform == "win32"`).

## Detailed subtasks

### T006 — Implement `MigrationOutcome` + `LegacyWindowsRoot` dataclasses

**Purpose**: Structured results that CLI callers render and tests assert against.

**Steps**:
1. In `src/specify_cli/paths/windows_migrate.py`, replace the WP01 stub with real implementation.
2. Define dataclasses per [`data-model.md` E-02, E-03](../data-model.md):
   ```python
   from __future__ import annotations
   from dataclasses import dataclass, field
   from pathlib import Path
   from typing import Literal


   @dataclass(frozen=True)
   class LegacyWindowsRoot:
       id: Literal["spec_kitty_home", "kittify_home", "auth_xdg_home"]
       path: Path
       dest: Path | None  # None == messaging-only, no state to move


   @dataclass(frozen=True)
   class MigrationOutcome:
       legacy_id: str
       status: Literal["absent", "moved", "quarantined", "error"]
       legacy_path: str
       dest_path: str | None
       quarantine_path: str | None
       timestamp_utc: str
       error: str | None = None
   ```
3. Define the three known legacy roots via a factory function (avoid module-level `Path.home()` evaluation — test hostile):
   ```python
   def _known_legacy_roots(root_base: Path, auth_dir: Path) -> list[LegacyWindowsRoot]:
       home = Path.home()
       return [
           LegacyWindowsRoot(id="spec_kitty_home", path=home / ".spec-kitty", dest=root_base),
           LegacyWindowsRoot(id="kittify_home", path=home / ".kittify", dest=None),
           LegacyWindowsRoot(id="auth_xdg_home", path=home / ".config" / "spec-kitty", dest=auth_dir),
       ]
   ```

**Validation**:
- Instances of both dataclasses frozen.
- `mypy --strict` passes.

### T007 — Implement `migrate_windows_state(dry_run=False)` core

**Purpose**: The actual migration function. Idempotent, destination-wins, never destroys.

**Steps**:
1. Implement signature exactly:
   ```python
   def migrate_windows_state(dry_run: bool = False) -> list[MigrationOutcome]:
   ```
2. Early-exit on non-Windows:
   ```python
   import sys
   if sys.platform != "win32":
       return []
   ```
3. Resolve `RuntimeRoot` and legacy root list:
   ```python
   from specify_cli.paths import get_runtime_root
   root = get_runtime_root()
   legacy = _known_legacy_roots(root.base, root.auth_dir)
   ```
4. For each legacy root:
   - If `legacy.path` does not exist → emit `status="absent"`.
   - If `dest` is `None` (kittify_home) → emit `status="absent"` (messaging-only, no move).
   - If `dest` exists and is non-empty → rename legacy to `legacy.path.parent / f"{legacy.path.name}.bak-{ts}"` with ISO-UTC timestamp. Emit `status="quarantined"`.
   - Otherwise → `os.replace(legacy.path, dest)` (create dest parent dirs if needed). Emit `status="moved"`.
5. Cross-volume fallback: `os.replace` raises `OSError` with `errno.EXDEV` when source and destination live on different volumes. On `EXDEV`, use `shutil.copytree` + rename source to quarantine (**never** delete source).
6. Wrap all file ops in `try/except OSError` and emit `status="error"` with a descriptive message on failure.
7. `dry_run=True`: compute what *would* happen without touching the filesystem.
8. On successful moves/quarantines, emit a single CLI summary via `rich.console.Console` using `render_runtime_path` for all paths shown. The contracted output format lives in [`contracts/cli-migrate.md`](../contracts/cli-migrate.md); follow it exactly.

**Helper**:
```python
from datetime import datetime, timezone
def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def _is_non_empty_dir(p: Path) -> bool:
    try:
        return p.is_dir() and any(p.iterdir())
    except OSError:
        return False
```

**Quarantine name collision handling**: if `legacy.path.parent / f"{name}.bak-{ts}"` already exists (two migrations in the same UTC second), append `_1`, `_2`, … until unique.

**Validation**:
- All five T009 tests pass.
- No code path calls `shutil.rmtree` on either source or destination.

### T008 — Add `msvcrt.locking`-based contention lock

**Purpose**: Two concurrent CLI invocations must not race into half-migrated state.

**Steps**:
1. Implement a context manager:
   ```python
   from contextlib import contextmanager
   from typing import Iterator

   @contextmanager
   def _migration_lock(root_base: Path, timeout_s: float = 3.0) -> Iterator[None]:
       if sys.platform != "win32":
           yield
           return
       import msvcrt, time
       root_base.mkdir(parents=True, exist_ok=True)
       lock_path = root_base / ".migrate.lock"
       lock_file = open(lock_path, "a+b")
       try:
           deadline = time.monotonic() + timeout_s
           while True:
               try:
                   msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                   break
               except OSError:
                   if time.monotonic() >= deadline:
                       raise TimeoutError("Another Spec Kitty CLI instance is migrating state.")
                   time.sleep(0.1)
           yield
       finally:
           try:
               msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
           except OSError:
               pass
           lock_file.close()
   ```
2. Wrap the per-root migration loop in `with _migration_lock(root.base)`.
3. On `TimeoutError`, return a list of `MigrationOutcome(status="error", error="Another Spec Kitty CLI instance is migrating runtime state. Please retry in a moment.")` for all three roots and exit code 69 (caller decides).

**Validation**:
- On POSIX, the lock context manager is a no-op (yielded, no file operations).
- Concurrency test (T010) exercises the real lock on `windows-latest`.

### T009 — Tests: absent / moved / quarantined / idempotent / dry-run [P]

**Purpose**: Cover the primary outcome matrix. These tests use platform mocking and `tmp_path` so they run on POSIX locally.

**Steps**:
1. Create `tests/paths/test_windows_migrate.py`.
2. Tests to write (each is a separate function):
   - `test_absent_noop`: no legacy dirs exist; all three outcomes `status="absent"`; no filesystem writes under fake `%LOCALAPPDATA%`.
   - `test_move_to_empty_destination`: create `~/.spec-kitty/file.txt`; destination empty; assert outcome `status="moved"`, source gone, destination populated.
   - `test_quarantine_on_conflict`: create both legacy and a non-empty destination; assert legacy renamed to `*.bak-<ts>`, destination untouched, outcome `status="quarantined"`.
   - `test_idempotent_second_run`: run twice; second run returns all `status="absent"`.
   - `test_dry_run_no_side_effects`: create legacy; dry-run; outcomes reflect intent; filesystem unchanged.
3. Use `monkeypatch.setattr(sys, "platform", "win32")` + `monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))` + patch `platformdirs.user_data_dir` to return a tmp path.
4. Mark NONE of these with `windows_ci` — they run on all platforms via mocking.

**Validation**:
- `pytest tests/paths/test_windows_migrate.py -v` passes on POSIX.
- Each test asserts filesystem state BEFORE and AFTER using `Path.exists()` and directory listing.

### T010 — Concurrency stress test [P]

**Purpose**: Verify the `msvcrt.locking` lock actually serializes two concurrent processes.

**Steps**:
1. In the same `test_windows_migrate.py`, add `test_concurrent_lock_contention`.
2. Mark `@pytest.mark.windows_ci` — this test uses real `msvcrt` and must run on `windows-latest`.
3. Shape:
   ```python
   import pytest
   import subprocess, sys, textwrap
   from pathlib import Path

   @pytest.mark.windows_ci
   def test_concurrent_lock_contention(tmp_path, monkeypatch):
       # Point %LOCALAPPDATA% and %HOME% into tmp_path via env vars; both
       # subprocesses must see the same paths.
       env = {**os.environ, "LOCALAPPDATA": str(tmp_path / "LocalAppData"),
              "USERPROFILE": str(tmp_path / "User"), "HOME": str(tmp_path / "User")}
       (tmp_path / "User" / ".spec-kitty").mkdir(parents=True)
       (tmp_path / "User" / ".spec-kitty" / "file.txt").write_text("legacy")

       runner = textwrap.dedent("""
           import json, sys
           from specify_cli.paths.windows_migrate import migrate_windows_state
           outcomes = migrate_windows_state()
           print(json.dumps([o.__dict__ if hasattr(o, '__dict__') else o.status for o in outcomes]))
       """)
       p1 = subprocess.Popen([sys.executable, "-c", runner], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
       p2 = subprocess.Popen([sys.executable, "-c", runner], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
       rc1 = p1.wait(timeout=10); rc2 = p2.wait(timeout=10)
       # Exactly one should see a successful move; the other should see either
       # all-absent (lost the race after first won) or an error outcome for
       # lock contention. No corruption.
       assert rc1 == 0 and rc2 == 0
   ```
4. The exact assertions depend on timing: acceptable outcomes are either (a) P1 moved, P2 absent; (b) P1 moved, P2 error-lock; (c) P2 moved, P1 absent. Assert the invariant: the destination ends up populated, the source is either gone or quarantined, and no data is missing.

**Validation**:
- Runs on `windows-latest` CI job.

## Definition of done

- [ ] All 5 subtasks complete.
- [ ] `pytest tests/paths/test_windows_migrate.py -v -m "not windows_ci"` passes on POSIX.
- [ ] `mypy --strict src/specify_cli/paths/windows_migrate.py` passes.
- [ ] Coverage ≥ 90% for the new module.
- [ ] Migration is pure (no CLI I/O imported directly; CLI wiring lives in WP04).
- [ ] No deletion of any file on any code path (reviewer: grep the diff for `unlink`, `rmtree`, `remove`).
- [ ] Commit message references FR-006, FR-007, FR-008, C-006.

## Risks

- **`msvcrt` not importable on POSIX**: Guard the import inside the lock context manager (only import when `sys.platform == "win32"`).
- **Cross-volume moves**: `os.replace` across volumes raises `EXDEV`. Use `shutil.copytree` + rename to quarantine as fallback. Never delete.
- **Open SQLite handles during migration**: The tracker DB may be locked by another Spec Kitty process. Detect by `OSError` during `os.replace`, surface an actionable message, do not delete.

## Reviewer guidance

Focus on:
1. Is any file deleted on any branch? (Must be: no.)
2. Do `test_absent_noop` and `test_idempotent_second_run` both pass? (Idempotency is the whole point.)
3. Does the quarantine rename happen BEFORE any touch of the destination? (Destination-wins = destination is never modified by migration.)
4. Does the lock release in the `finally` block? (Leak-free.)
5. Does the function return `[]` promptly on non-Windows? (Must not call `platformdirs` or `msvcrt`.)

Do NOT ask about:
- CLI output formatting or where migration is invoked — that's WP04.
- Whether `migrate_cmd.py` should call this — that's WP04.

## Activity Log

- 2026-04-14T11:25:54Z – claude:opus-4.6:implementer:implementer – shell_pid=46585 – Started implementation via action command

---
work_package_id: WP01
title: Windows paths subpackage + render helper
dependencies: []
requirement_refs:
- C-005
- FR-005
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-windows-compatibility-hardening-01KP5R6K
base_commit: 1fcc638deed73374a7c7b678639ddd2f4d820077
created_at: '2026-04-14T10:58:37.777404+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
shell_pid: '29321'
history:
- timestamp: '2026-04-14T10:41:03Z'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/paths/
execution_mode: code_change
owned_files:
- src/specify_cli/paths/__init__.py
- src/specify_cli/paths/windows_paths.py
- tests/paths/__init__.py
- tests/paths/test_windows_paths.py
- tests/paths/test_render_runtime_path.py
tags: []
---

# WP01 — Windows paths subpackage + render helper

## Branch strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: allocated per lane after `finalize-tasks`; commands inside your worktree operate on `kitty/mission-windows-compatibility-hardening-01KP5R6K-lane-<id>`.
- Implement command: `spec-kitty agent action implement WP01 --agent <name>` (no dependencies).

## Objective

Create a new `src/specify_cli/paths/` subpackage that exposes two things:

1. A single canonical resolver for the Windows runtime state root (`RuntimeRoot` + `get_runtime_root()`), backed by `platformdirs` on Windows and preserving existing POSIX paths unchanged.
2. A single user-facing path rendering helper (`render_runtime_path`) that downstream CLI surfaces call instead of hardcoding `~/.kittify` or `~/.spec-kitty` literals.

This WP is foundational: WP02, WP03, WP04, and WP05 all depend on it.

## Context

- **Spec IDs covered**: FR-005 (single Windows root), FR-012 (user-facing path rendering correctness).
- **Research source of truth**: [`research.md` R-01, R-10](../research.md)
- **Data model**: [`data-model.md` E-01 `RuntimeRoot`](../data-model.md)
- **Related contract**: [`contracts/cli-agent-status.md`](../contracts/cli-agent-status.md)
- **WSL policy**: WSL is Linux. `sys.platform` inside WSL is `"linux"`, so WSL installs take the POSIX branch. No special handling needed.

## Detailed subtasks

### T001 — Create paths package skeleton

**Purpose**: Give the project a single import surface for Windows path resolution.

**Steps**:
1. Create `src/specify_cli/paths/__init__.py`.
2. Re-export the three public names: `RuntimeRoot`, `get_runtime_root`, `render_runtime_path`.
3. Add a short module docstring explaining: "This subpackage is the single source of truth for Windows runtime state paths. Windows-specific logic lives here so that consumers (auth, tracker, sync, daemon, CLI) can remain platform-agnostic."
4. Also add an empty `src/specify_cli/paths/windows_migrate.py` placeholder so that WP02 can land without touching `__init__.py` again. Do not implement migration yet — that is WP02.

**Files created**:
- `src/specify_cli/paths/__init__.py` (~20 lines)
- `src/specify_cli/paths/windows_paths.py` (created empty now; populated in T002)
- `src/specify_cli/paths/windows_migrate.py` (stub with `def migrate_windows_state(*args, **kwargs): raise NotImplementedError` — real impl in WP02)

**Validation**:
- `python -c "from specify_cli.paths import get_runtime_root, render_runtime_path, RuntimeRoot"` succeeds.
- `mypy --strict src/specify_cli/paths/` passes.

### T002 — Implement `RuntimeRoot` + `get_runtime_root()`

**Purpose**: One function returns the correct runtime state root for the current platform.

**Steps**:
1. In `windows_paths.py`, define:
   ```python
   from __future__ import annotations
   import sys
   from dataclasses import dataclass
   from pathlib import Path
   from typing import Literal
   import platformdirs


   @dataclass(frozen=True)
   class RuntimeRoot:
       platform: Literal["win32", "darwin", "linux"]
       base: Path

       @property
       def auth_dir(self) -> Path:
           return self.base / "auth"

       @property
       def tracker_dir(self) -> Path:
           return self.base / "tracker"

       @property
       def sync_dir(self) -> Path:
           return self.base / "sync"

       @property
       def daemon_dir(self) -> Path:
           return self.base / "daemon"

       @property
       def cache_dir(self) -> Path:
           return self.base / "cache"


   def get_runtime_root() -> RuntimeRoot:
       platform = _current_platform()
       if platform == "win32":
           base = Path(platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False))
       else:
           base = Path.home() / ".spec-kitty"
       return RuntimeRoot(platform=platform, base=base)


   def _current_platform() -> Literal["win32", "darwin", "linux"]:
       if sys.platform.startswith("win"):
           return "win32"
       if sys.platform == "darwin":
           return "darwin"
       return "linux"
   ```
2. Do NOT create directories here. Creation is the caller's job — this function is pure.
3. Keep `RuntimeRoot` frozen (immutable) so it can be safely cached by callers.

**Validation**:
- Unit test (T004) asserts correct `base` per mocked `sys.platform`.
- `mypy --strict` passes.

### T003 — Implement `render_runtime_path()` helper [P]

**Purpose**: Single helper for user-facing path rendering. Windows shows real absolute paths; POSIX uses tilde compression.

**Steps**:
1. In `windows_paths.py`:
   ```python
   def render_runtime_path(path: Path, *, for_user: bool = True) -> str:
       """Render a runtime-state path for user-facing output.

       On Windows: returns the real absolute path (e.g. C:\\Users\\alice\\AppData\\Local\\spec-kitty\\auth).
       On POSIX: returns a tilde-compressed form (~/...) when under $HOME and for_user=True, else absolute.
       """
       abs_path = Path(path).resolve(strict=False)
       if not for_user:
           return str(abs_path)
       if _current_platform() == "win32":
           return str(abs_path)
       # POSIX tilde compression
       try:
           home = Path.home().resolve(strict=False)
           rel = abs_path.relative_to(home)
           return "~/" + str(rel).replace("\\", "/")
       except ValueError:
           return str(abs_path)
   ```
2. Re-export from `__init__.py`.

**Validation**:
- Unit test (T005) covers Windows (mocked), POSIX tilde-compression path, POSIX non-home path.

### T004 — Unit tests for `RuntimeRoot` + `get_runtime_root` [P]

**Purpose**: Ensure platform dispatch is correct without requiring a native Windows runner.

**Steps**:
1. Create `tests/paths/__init__.py` (empty).
2. Create `tests/paths/test_windows_paths.py`:
   ```python
   import sys
   from pathlib import Path
   from unittest.mock import patch

   from specify_cli.paths import RuntimeRoot, get_runtime_root


   def test_get_runtime_root_on_windows(tmp_path, monkeypatch):
       monkeypatch.setattr(sys, "platform", "win32")
       fake_localappdata = tmp_path / "LocalAppData"
       with patch(
           "specify_cli.paths.windows_paths.platformdirs.user_data_dir",
           return_value=str(fake_localappdata / "spec-kitty"),
       ):
           root = get_runtime_root()
       assert root.platform == "win32"
       assert root.base == fake_localappdata / "spec-kitty"
       assert root.auth_dir == root.base / "auth"
       assert root.tracker_dir == root.base / "tracker"
       assert root.sync_dir == root.base / "sync"
       assert root.daemon_dir == root.base / "daemon"
       assert root.cache_dir == root.base / "cache"


   def test_get_runtime_root_on_linux(monkeypatch):
       monkeypatch.setattr(sys, "platform", "linux")
       root = get_runtime_root()
       assert root.platform == "linux"
       assert root.base == Path.home() / ".spec-kitty"


   def test_get_runtime_root_on_darwin(monkeypatch):
       monkeypatch.setattr(sys, "platform", "darwin")
       root = get_runtime_root()
       assert root.platform == "darwin"
       assert root.base == Path.home() / ".spec-kitty"


   def test_runtime_root_is_frozen():
       import dataclasses
       root = get_runtime_root()
       assert dataclasses.is_dataclass(root)
       # Attempting mutation must fail
       import pytest
       with pytest.raises(dataclasses.FrozenInstanceError):
           root.base = Path("/tmp/other")  # type: ignore[misc]
   ```
3. No `windows_ci` marker — these tests run on every platform via mocking.

**Validation**:
- All four tests pass on POSIX.
- Coverage ≥ 90% for `windows_paths.py` RuntimeRoot logic.

### T005 — Unit tests for `render_runtime_path` [P]

**Purpose**: Pin rendering behavior per platform.

**Steps**:
1. Create `tests/paths/test_render_runtime_path.py`:
   ```python
   import sys
   from pathlib import Path

   from specify_cli.paths import render_runtime_path


   def test_windows_returns_absolute(monkeypatch):
       monkeypatch.setattr(sys, "platform", "win32")
       # Simulate Windows absolute path semantics on a POSIX test runner by using
       # a concrete path that exists. The helper uses resolve(strict=False) so
       # rendering stays stable.
       p = Path("/tmp/fake-windows-path/spec-kitty/auth")
       rendered = render_runtime_path(p)
       assert not rendered.startswith("~/")
       assert "spec-kitty" in rendered


   def test_posix_tilde_compression_under_home(monkeypatch, tmp_path):
       monkeypatch.setattr(sys, "platform", "linux")
       monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
       p = tmp_path / ".spec-kitty" / "auth"
       assert render_runtime_path(p) == "~/.spec-kitty/auth"


   def test_posix_absolute_outside_home(monkeypatch, tmp_path):
       monkeypatch.setattr(sys, "platform", "linux")
       monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
       p = Path("/var/lib/spec-kitty")
       rendered = render_runtime_path(p)
       assert not rendered.startswith("~/")
       assert "spec-kitty" in rendered


   def test_for_user_false_always_absolute(monkeypatch, tmp_path):
       monkeypatch.setattr(sys, "platform", "linux")
       monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
       p = tmp_path / ".spec-kitty" / "auth"
       rendered = render_runtime_path(p, for_user=False)
       assert not rendered.startswith("~/")
   ```

**Validation**:
- All four tests pass on POSIX.

## Definition of done

- [ ] All 5 subtasks complete; WP checklist in `tasks.md` ticked.
- [ ] `pytest tests/paths/ -v` passes (no `windows_ci` marker tests run on local machine).
- [ ] `mypy --strict src/specify_cli/paths/` passes with zero errors.
- [ ] Coverage for `src/specify_cli/paths/windows_paths.py` ≥ 90%.
- [ ] No behavioral change on macOS/Linux (verify by running existing auth/tracker tests — should still pass).
- [ ] No `[NEEDS CLARIFICATION]` markers introduced.
- [ ] Commit message references FR-005 and FR-012.

## Risks

- **`platformdirs` API drift**: Pin the version in `pyproject.toml` if not already pinned. Use `user_data_dir` (not `user_data_path`) for portability across platformdirs versions.
- **Circular imports**: Do not import from `specify_cli.auth` or `specify_cli.tracker` from within `paths/`. This package is a leaf.

## Reviewer guidance

Focus on:
1. Does `get_runtime_root()` behave correctly when `sys.platform` is mocked? (tests T004)
2. Does `render_runtime_path()` produce the exact string expected by downstream message contracts? (tests T005)
3. Is `RuntimeRoot` frozen and therefore safe to cache? (tests T004)
4. Any accidental directory creation or filesystem access in `get_runtime_root()`? (Should be pure.)
5. Any import cycle risk? (`paths/` must stay leaf.)

Do NOT ask about:
- Migration behavior (that's WP02).
- Auth storage (that's WP03).
- CLI messaging changes (that's WP04).

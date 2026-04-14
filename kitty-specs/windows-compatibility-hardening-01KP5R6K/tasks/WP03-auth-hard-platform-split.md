---
work_package_id: WP03
title: Auth hard platform split + pyproject markers
dependencies:
- WP01
requirement_refs:
- C-001
- C-007
- FR-001
- FR-002
- FR-015
- FR-016
- FR-019
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T017
- T018
agent: "claude:opus-4.6:reviewer:reviewer"
shell_pid: "46403"
history:
- timestamp: '2026-04-14T10:41:03Z'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/auth/secure_storage/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/secure_storage/__init__.py
- src/specify_cli/auth/secure_storage/abstract.py
- src/specify_cli/auth/secure_storage/file_fallback.py
- src/specify_cli/auth/secure_storage/windows_storage.py
- tests/auth/secure_storage/test_from_environment_platform_split.py
- tests/auth/secure_storage/test_file_fallback_windows_root.py
- tests/packaging/__init__.py
- tests/packaging/test_windows_no_keyring.py
- pyproject.toml
tags: []
---

# WP03 — Auth hard platform split + `pyproject.toml` markers

## Branch strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: per-lane `.worktrees/windows-compatibility-hardening-01KP5R6K-lane-<id>/` (resolved from `lanes.json`).
- Implement command: `spec-kitty agent action implement WP03 --agent <name>`. Begin only after WP01 is merged to main.

## Objective

Close GitHub #603 by removing the Windows code path's dependency on Credential Manager / `keyring`. Implement a hard platform split in `SecureStorage.from_environment()` so Windows instantiates a file-backed store directly and never imports the `keychain` module. Declare `keyring` as a non-Windows conditional dependency in `pyproject.toml`. Register the `windows_ci` pytest marker so WP07's CI job can select by marker.

## Context

- **Spec IDs covered**: FR-001 (Windows file-backed store), FR-002 (explicit platform selection), FR-015 / FR-016 (marker registration is required for CI to select tests), FR-019 (docs — via keyring marker explanation in pyproject comment), C-001 (no keyring on Windows).
- **Discovery decision**: Q1=A (hard split).
- **Research**: [`research.md` R-04, R-11](../research.md)
- **Data model**: [`data-model.md` E-04 `SecureStorageSelection`](../data-model.md)
- **Contract**: [`contracts/auth-secure-storage.md`](../contracts/auth-secure-storage.md)

## Detailed subtasks

### T011 — Refactor `SecureStorage.from_environment()` to hard-dispatch on `sys.platform`

**Purpose**: Make the platform selection explicit instead of keychain-first-with-fallback.

**Steps**:
1. Open `src/specify_cli/auth/secure_storage/abstract.py`.
2. Read the current `from_environment()` implementation (review it in the execution worktree before touching it).
3. Replace the body with:
   ```python
   @classmethod
   def from_environment(cls) -> "SecureStorage":
       import sys
       if sys.platform == "win32":
           from .windows_storage import WindowsFileStorage
           return WindowsFileStorage()
       # Non-Windows: retain existing keychain-first behavior
       from .keychain import KeychainStorage
       try:
           return KeychainStorage()
       except Exception:
           from .file_fallback import EncryptedFileStorage
           return EncryptedFileStorage()
   ```
4. Preserve the existing macOS/Linux behavior exactly — do not change the keychain-first-try-fallback semantics on non-Windows.
5. If the current implementation has additional environment-variable overrides (e.g. `SPEC_KITTY_AUTH_BACKEND`), retain them.

**Validation**:
- T016 unit test confirms hard dispatch.

### T012 — Create `WindowsFileStorage`

**Purpose**: A thin Windows wrapper around the existing file-backed store, pointed at `%LOCALAPPDATA%\spec-kitty\auth\`.

**Steps**:
1. Create `src/specify_cli/auth/secure_storage/windows_storage.py`:
   ```python
   from __future__ import annotations
   from pathlib import Path
   from .file_fallback import EncryptedFileStorage


   class WindowsFileStorage(EncryptedFileStorage):
       """Windows-native secure storage.

       Uses the encrypted file-backed store at %LOCALAPPDATA%\\spec-kitty\\auth\\.
       Does NOT depend on keyring or Windows Credential Manager.
       """

       def __init__(self, store_path: Path | None = None) -> None:
           if store_path is None:
               from specify_cli.paths import get_runtime_root
               store_path = get_runtime_root().auth_dir
           super().__init__(store_path=store_path)
   ```
2. If `EncryptedFileStorage` does not currently accept a `store_path` kwarg, add one (this is why T013 is in the same WP).

**Validation**:
- T017 Windows-native round-trip test passes.

### T013 — Replace `_DEFAULT_DIR` constant with `default_store_dir()` function

**Purpose**: A module-level `Path.home()` constant evaluated at import time cannot respond to `sys.platform` — convert it to a function.

**Steps**:
1. Open `src/specify_cli/auth/secure_storage/file_fallback.py`.
2. Find the line `_DEFAULT_DIR = Path.home() / ".config" / "spec-kitty"`.
3. Replace with:
   ```python
   def default_store_dir() -> Path:
       """Default on-disk location for the encrypted file store."""
       import sys
       if sys.platform == "win32":
           from specify_cli.paths import get_runtime_root
           return get_runtime_root().auth_dir
       return Path.home() / ".config" / "spec-kitty"
   ```
4. Update every reference to `_DEFAULT_DIR` in `file_fallback.py` to call `default_store_dir()`.
5. If `EncryptedFileStorage.__init__` accepted `store_path: Path | None = None` and defaulted to `_DEFAULT_DIR`, change the default to `None` and resolve to `default_store_dir()` inside `__init__` at runtime:
   ```python
   def __init__(self, store_path: Path | None = None) -> None:
       self.store_path = store_path if store_path is not None else default_store_dir()
       ...
   ```

**Validation**:
- All existing non-Windows tests still pass (behavior on POSIX unchanged).

### T014 — Gate `keychain` import with `TYPE_CHECKING` + `sys.platform`

**Purpose**: Windows must never import `keychain.py` at runtime. Preserve mypy coverage on all platforms.

**Steps**:
1. Open `src/specify_cli/auth/secure_storage/__init__.py`.
2. Review current exports. Likely exports `KeychainStorage` at module level. That would import `keyring` transitively.
3. Change to lazy re-exports guarded by `sys.platform`:
   ```python
   from .abstract import SecureStorage
   from .file_fallback import EncryptedFileStorage
   from .windows_storage import WindowsFileStorage

   import sys
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from .keychain import KeychainStorage  # noqa: F401 — mypy coverage only

   if sys.platform != "win32":
       # Runtime-import keychain only on non-Windows
       from .keychain import KeychainStorage  # noqa: F401
       __all__ = ["SecureStorage", "EncryptedFileStorage", "WindowsFileStorage", "KeychainStorage"]
   else:
       __all__ = ["SecureStorage", "EncryptedFileStorage", "WindowsFileStorage"]
   ```
4. Grep the codebase for `from specify_cli.auth.secure_storage import KeychainStorage` — any Windows call-site that hits it will break. None should exist; if any do, switch them to `from specify_cli.auth.secure_storage.keychain import KeychainStorage` inside a non-Windows-guarded block.

**Validation**:
- T016 asserts `"specify_cli.auth.secure_storage.keychain" not in sys.modules` after `from_environment()` on `sys.platform="win32"`.
- `mypy --strict` passes on all platforms (TYPE_CHECKING import still gives keychain.py type coverage).

### T015 — Update `pyproject.toml`: `keyring` conditional + `windows_ci` pytest marker

**Purpose**: Packaging-level enforcement that `keyring` never installs on Windows, and pytest knows the `windows_ci` marker exists.

**Steps**:
1. Open `pyproject.toml`.
2. Find the `[project]` or `[project.dependencies]` block.
3. Change `"keyring>=XX"` to `"keyring>=XX; sys_platform != \"win32\""`. Preserve the existing minimum version (do not bump it as a side effect). If `keyring` is pulled via a transitive dep you don't directly declare, add the explicit conditional declaration alongside.
4. Find `[tool.pytest.ini_options]`. Add (or extend existing) `markers`:
   ```toml
   [tool.pytest.ini_options]
   markers = [
       "windows_ci: tests that must pass on the native windows-latest CI job",
       # ... preserve existing markers ...
   ]
   ```
5. If a top-level `markers` key does not exist, add it. Do not reorder or remove existing markers.

**Validation**:
- `pip install .` on a Windows box (or the CI `windows-latest` runner via WP07) does NOT list `keyring` in `pip list`.
- `pytest --markers` shows `windows_ci` listed.

### T016 — Unit test: platform split correctness [P]

**Purpose**: Pin the hard split with a test that doesn't require Windows.

**Steps**:
1. Create `tests/auth/secure_storage/test_from_environment_platform_split.py`:
   ```python
   import sys
   import importlib
   import pytest

   from specify_cli.auth.secure_storage import SecureStorage


   def test_from_environment_windows_returns_windows_file_storage(monkeypatch):
       monkeypatch.setattr(sys, "platform", "win32")
       # Unload any previously-imported keychain module
       for name in list(sys.modules):
           if name.startswith("specify_cli.auth.secure_storage.keychain"):
               del sys.modules[name]
       # Must reimport abstract to pick up the patched sys.platform
       import specify_cli.auth.secure_storage.abstract as abstract_mod
       importlib.reload(abstract_mod)

       storage = abstract_mod.SecureStorage.from_environment()
       from specify_cli.auth.secure_storage.windows_storage import WindowsFileStorage
       assert isinstance(storage, WindowsFileStorage)
       assert "specify_cli.auth.secure_storage.keychain" not in sys.modules


   def test_from_environment_posix_returns_keychain_or_file(monkeypatch):
       monkeypatch.setattr(sys, "platform", "linux")
       # On POSIX, the existing keychain-first-try-fallback behavior is preserved
       import specify_cli.auth.secure_storage.abstract as abstract_mod
       importlib.reload(abstract_mod)
       storage = abstract_mod.SecureStorage.from_environment()
       # Shape: either KeychainStorage or EncryptedFileStorage
       from specify_cli.auth.secure_storage import EncryptedFileStorage
       from specify_cli.auth.secure_storage.keychain import KeychainStorage
       assert isinstance(storage, (KeychainStorage, EncryptedFileStorage))
   ```
2. No `windows_ci` marker — this test uses mocking.

**Validation**:
- Passes on POSIX.

### T017 — Windows-native round-trip test [P]

**Purpose**: Actual store → load → delete on `windows-latest` with the encrypted file store.

**Steps**:
1. Create `tests/auth/secure_storage/test_file_fallback_windows_root.py`:
   ```python
   import pytest
   from pathlib import Path

   from specify_cli.auth.secure_storage import WindowsFileStorage


   @pytest.mark.windows_ci
   def test_windows_file_store_round_trip(tmp_path):
       store = WindowsFileStorage(store_path=tmp_path / "auth")
       store.store("key1", b"secret-payload")
       assert store.load("key1") == b"secret-payload"
       store.delete("key1")
       assert store.load("key1") is None


   @pytest.mark.windows_ci
   def test_windows_file_store_default_path_under_localappdata(monkeypatch):
       # When no store_path provided, defaults to %LOCALAPPDATA%\spec-kitty\auth
       from specify_cli.paths import get_runtime_root
       root = get_runtime_root()
       assert root.platform == "win32"
       assert "AppData" in str(root.auth_dir) or "LOCALAPPDATA" in str(root.auth_dir).upper()
   ```

**Validation**:
- Runs on `windows-latest`.

### T018 — Packaging assertion: keyring NOT installed on Windows [P]

**Purpose**: Closes the "keyring-still-transitively-pulled" loophole.

**Steps**:
1. Create `tests/packaging/__init__.py` (empty).
2. Create `tests/packaging/test_windows_no_keyring.py`:
   ```python
   import importlib.util
   import pytest


   @pytest.mark.windows_ci
   def test_keyring_not_installed_on_windows():
       spec = importlib.util.find_spec("keyring")
       assert spec is None, (
           "keyring MUST NOT be installed on Windows. The conditional "
           "marker in pyproject.toml (keyring; sys_platform != 'win32') is "
           "either missing or not being honored by the installer."
       )
   ```

**Validation**:
- Runs on `windows-latest`. Fails if `keyring` is somehow pulled.

## Definition of done

- [ ] All 8 subtasks complete.
- [ ] `pytest tests/auth/ -v -m "not windows_ci"` passes on POSIX.
- [ ] `mypy --strict src/specify_cli/auth/secure_storage/` passes.
- [ ] `importlib.util.find_spec("keyring")` returns `None` on `windows-latest` after `pip install .`.
- [ ] No non-Windows behavior change (existing macOS/Linux tests still pass).
- [ ] `pyproject.toml` diff adds exactly one marker line for `windows_ci` + one conditional on `keyring`.
- [ ] Commit message references FR-001, FR-002, C-001, plus FR-015 (marker registration).

## Risks

- **Existing transitive keyring dep**: If another dep pulls `keyring` transitively, the conditional marker won't help. Grep `pip freeze` on Windows for `keyring` and trace back.
- **`pyproject.toml` drift**: Preserve every other dep, marker, and tool configuration exactly. Use `git diff pyproject.toml` to verify only the two intended changes.
- **`abstract.py` reload brittleness**: T016 uses `importlib.reload` which is fragile. Document that this test is a platform-dispatch smoke test, not a general-purpose pattern.

## Reviewer guidance

Focus on:
1. Is `keychain` truly never imported on Windows? (`sys.modules` assertion in T016.)
2. Is the non-Windows behavior *unchanged*? Run existing `tests/auth/` against `main` and post-WP diff to compare.
3. Does the `pyproject.toml` marker use `sys_platform`, not `platform_system`? (PEP 508 canonical is `sys_platform`; both work but mixing is confusing.)
4. Is the `windows_ci` marker registered with a description that tells new contributors what it means?

Do NOT ask about:
- CI workflow shape (that's WP07).
- Path messaging (that's WP04).

## Activity Log

- 2026-04-14T11:14:15Z – claude:opus-4.6:implementer:implementer – shell_pid=40116 – Started implementation via action command
- 2026-04-14T11:24:21Z – claude:opus-4.6:implementer:implementer – shell_pid=40116 – WP03 complete: hard platform split, conditional keyring marker, windows_ci test support, keychain isolated from Windows code path. Commit 2c93de2b in lane-a. 258 tests pass (1 pre-existing failure unrelated to WP03). Ready for review.
- 2026-04-14T11:25:01Z – claude:opus-4.6:reviewer:reviewer – shell_pid=46403 – Started review via action command

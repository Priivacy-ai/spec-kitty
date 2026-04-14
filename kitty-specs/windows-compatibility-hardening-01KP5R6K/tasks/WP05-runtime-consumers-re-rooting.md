---
work_package_id: WP05
title: Tracker / sync / daemon / kernel.paths re-rooting
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-005
- NFR-004
- C-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
history:
- timestamp: '2026-04-14T10:41:03Z'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/tracker/credentials.py
execution_mode: code_change
owned_files:
- src/specify_cli/tracker/credentials.py
- src/specify_cli/sync/daemon.py
- src/kernel/paths.py
- tests/tracker/test_credentials_windows_paths.py
- tests/sync/test_daemon_windows_paths.py
- tests/kernel/test_paths_unified_windows_root.py
tags: []
---

# WP05 — Tracker / sync / daemon / `kernel.paths` re-rooting

## Branch strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: per-lane `.worktrees/windows-compatibility-hardening-01KP5R6K-lane-<id>/`.
- Implement command: `spec-kitty agent action implement WP05 --agent <name>`. Begin after WP01 is merged to main.

## Objective

Point the remaining Windows-state consumers at the unified `RuntimeRoot` so `auth`, `tracker`, `sync`, `daemon`, and `kernel.paths` all share a single Windows root (`%LOCALAPPDATA%\spec-kitty\`). Preserve POSIX behavior exactly. Add a cross-module consistency test that asserts single-root reality.

## Context

- **Spec IDs covered**: FR-003 (tracker re-root), FR-004 (sync/daemon re-root), FR-005 (single root), NFR-004 (concurrent-access safety), C-002 (no long-term dual root).
- **Discovery decision**: Q3=C (unified root including `kernel.paths`).
- **Research**: [`research.md` R-01](../research.md)
- **Data model**: [`data-model.md` E-01 RuntimeRoot](../data-model.md)

## Detailed subtasks

### T025 — Refactor `tracker/credentials.py` to use `get_runtime_root().tracker_dir` [P]

**Purpose**: Tracker credentials land under the unified Windows root.

**Steps**:
1. Open `src/specify_cli/tracker/credentials.py`.
2. Find every occurrence of `Path.home() / ".spec-kitty"` or similar legacy root constructions.
3. Replace with platform-aware resolution:
   ```python
   import sys
   from pathlib import Path

   def _tracker_root() -> Path:
       if sys.platform == "win32":
           from specify_cli.paths import get_runtime_root
           return get_runtime_root().tracker_dir
       return Path.home() / ".spec-kitty"  # preserve existing POSIX behavior exactly
   ```
4. Replace legacy literal expressions with calls to `_tracker_root()`.
5. If the file previously had Windows-specific locking branches using `msvcrt`, keep them — the locking logic is NOT in this WP's scope. Only the path resolution changes.

**Validation**:
- T028 asserts tracker paths resolve under `%LOCALAPPDATA%\spec-kitty\tracker\` on Windows.
- Existing tracker tests on POSIX still pass.

### T026 — Refactor `sync/daemon.py` to use `get_runtime_root().sync_dir` / `daemon_dir` [P]

**Purpose**: Sync and daemon state (PID files, lock files, queue DB) land under the unified Windows root.

**Steps**:
1. Open `src/specify_cli/sync/daemon.py`.
2. Find legacy root constructions.
3. Apply the same pattern as T025:
   ```python
   def _sync_root() -> Path:
       if sys.platform == "win32":
           from specify_cli.paths import get_runtime_root
           return get_runtime_root().sync_dir
       return Path.home() / ".spec-kitty" / "sync"  # preserve POSIX
   ```
4. If daemon PID/state uses a separate subdir (`daemon/`), use `get_runtime_root().daemon_dir` instead.
5. Do NOT change locking or process-management logic.

**Validation**:
- T029 asserts sync/daemon paths resolve correctly on Windows.

### T027 — Refactor `src/kernel/paths.py` for unified Windows root [P]

**Purpose**: `kernel.paths` currently uses `platformdirs` with an app name (possibly `"kittify"`). Align it with `get_runtime_root()` so Windows consumers never see two different Windows roots.

**Steps**:
1. Open `src/kernel/paths.py`.
2. Identify the existing platformdirs-based Windows resolution. It likely uses `platformdirs.user_data_dir("kittify", ...)` or similar.
3. Decide: either (a) change the app name to `"spec-kitty"` and consolidate, or (b) have `kernel.paths` import `get_runtime_root()` and derive from it.
4. Prefer (b): make `kernel.paths` a thin adapter that defers Windows root resolution to `specify_cli.paths.get_runtime_root()`. This keeps a single authoritative source.
5. On POSIX, preserve existing behavior exactly (may be `~/.kittify` or `~/.cache/kittify` — whatever it is, don't change).
6. **Important**: Other code across the repo may import from `kernel.paths`. Do not break those imports — only change the Windows return value.

**Validation**:
- T030 asserts all four consumers end up with paths under the same Windows root.
- Existing `tests/kernel/test_paths.py` still passes.

### T028 — Windows-native test for tracker credentials path [P]

**Purpose**: Real-runner assertion on tracker path resolution.

**Steps**:
1. Create `tests/tracker/test_credentials_windows_paths.py`:
   ```python
   import pytest


   @pytest.mark.windows_ci
   def test_tracker_credentials_path_under_localappdata():
       from specify_cli.tracker import credentials
       # Invoke the module's path resolver (adjust name to match real API)
       path = credentials._tracker_root()  # or the module's real public resolver
       s = str(path)
       assert "AppData" in s and "Local" in s
       assert "spec-kitty" in s.lower()
       assert "tracker" in s.lower()
   ```
2. If `_tracker_root()` is private, use whichever public function / object exposes the resolved path. Do not change the module's public API in this test.

**Validation**:
- Runs on `windows-latest`.

### T029 — Windows-native test for daemon paths [P]

**Purpose**: Same as T028, for `sync/daemon.py`.

**Steps**:
1. Create `tests/sync/test_daemon_windows_paths.py`:
   ```python
   import pytest


   @pytest.mark.windows_ci
   def test_sync_daemon_paths_under_localappdata():
       from specify_cli.sync import daemon
       # Adjust to match real resolver name/shape
       sync_root = daemon._sync_root() if hasattr(daemon, "_sync_root") else None
       assert sync_root is not None
       s = str(sync_root)
       assert "AppData" in s and "Local" in s
       assert "spec-kitty" in s.lower()
   ```

**Validation**:
- Runs on `windows-latest`.

### T030 — Cross-module single-root consistency test

**Purpose**: Prove C-002 / FR-005: on Windows, auth/tracker/sync/daemon/kernel.paths all resolve under the same `RuntimeRoot.base`.

**Steps**:
1. Create `tests/kernel/test_paths_unified_windows_root.py`:
   ```python
   import pytest
   from pathlib import Path


   @pytest.mark.windows_ci
   def test_all_consumers_share_single_windows_root():
       from specify_cli.paths import get_runtime_root
       root = get_runtime_root()
       assert root.platform == "win32"
       base_str = str(root.base).lower()

       # Auth
       from specify_cli.auth.secure_storage import WindowsFileStorage
       auth = WindowsFileStorage()
       assert base_str in str(auth.store_path).lower()

       # Tracker
       from specify_cli.tracker import credentials
       tracker_root = credentials._tracker_root() if hasattr(credentials, "_tracker_root") else None
       if tracker_root is not None:
           assert base_str in str(tracker_root).lower()

       # Sync/daemon
       from specify_cli.sync import daemon
       sync_root = daemon._sync_root() if hasattr(daemon, "_sync_root") else None
       if sync_root is not None:
           assert base_str in str(sync_root).lower()

       # kernel.paths
       from kernel import paths as kernel_paths
       # Use whatever the real public accessor is (user_data_dir(), get_runtime_dir(), etc.)
       # Adjust this assertion to the real API.
       for attr_name in ("user_data_dir", "runtime_dir", "get_user_data_dir"):
           accessor = getattr(kernel_paths, attr_name, None)
           if callable(accessor):
               resolved = Path(accessor())
               assert base_str in str(resolved).lower(), (
                   f"kernel.paths.{attr_name}() resolves to {resolved}, outside the "
                   f"unified Windows root {root.base}"
               )
               break
   ```
2. Resolver helpers are shown with private names (`_tracker_root`, `_sync_root`); adjust to the real public/private names in the repo. The assertion substance — "every resolved path is under `root.base`" — is the invariant.

**Validation**:
- Runs on `windows-latest`.

## Definition of done

- [ ] All 6 subtasks complete.
- [ ] `pytest tests/tracker tests/sync tests/kernel -v -m "not windows_ci"` passes on POSIX.
- [ ] `mypy --strict` passes on the three modified modules.
- [ ] POSIX paths for tracker/sync/daemon are UNCHANGED (diff review).
- [ ] Commit message references FR-003, FR-004, FR-005, C-002.

## Risks

- **`kernel.paths` has external consumers**: The refactor must not change POSIX returns or the public function signatures. Use git grep to find every importer before refactoring.
- **Live state at the time of migration**: WP02's migration runs first (via WP04's wiring) so by the time `tracker/sync/daemon` resolve on Windows, state is already in the unified root. Do not add fallback code that reads from legacy roots — per C-006 migration is one-direction.
- **`_tracker_root()` / `_sync_root()` naming assumptions in tests**: Verify the real API in the execution worktree before writing the tests.

## Reviewer guidance

Focus on:
1. Does every legacy `Path.home() / ".spec-kitty"` get replaced with a platform-aware call?
2. Are POSIX paths byte-for-byte unchanged?
3. Does T030 really assert the same base across all four consumers?
4. Did `kernel.paths` change app name from `"kittify"` to `"spec-kitty"` anywhere? (If so, that is a potentially breaking change — document it explicitly.)

Do NOT ask about:
- Migration behavior — that's WP02.
- Auth subsystem — that's WP03.

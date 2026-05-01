---
work_package_id: WP01
title: 'P1.2: Relocate ProjectIdentity'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-007
- NFR-001
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-p1-dependency-cycle-cleanup-01KQFXVC
base_commit: ff01ad7e4f20bfa40463c7a65ef7e4e7121dcb4d
created_at: '2026-05-01T04:30:58.570075+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "codex:gpt-4o:python-pedro:reviewer"
shell_pid: "4258"
history:
- date: '2026-04-30'
  event: Created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/identity/
execution_mode: code_change
owned_files:
- src/specify_cli/identity/__init__.py
- src/specify_cli/identity/project.py
- src/specify_cli/sync/project_identity.py
- src/specify_cli/dossier/drift_detector.py
- src/specify_cli/dossier/emitter_adapter.py
- src/specify_cli/dossier/events.py
- tests/architectural/test_dossier_sync_boundary.py
- tests/dossier/test_events.py
- tests/sync/test_events_namespace.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this file, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

This configures your Python implementation persona, coding standards, and tool preferences for this work package.

---

## Objective

Break the **P1.2 dossier ↔ sync circular import cycle** (GitHub issue #862) by relocating the `ProjectIdentity` type from `specify_cli.sync.project_identity` into the existing neutral leaf package `specify_cli.identity`. The original module becomes a backward-compatible shim. Only one dossier file needs updating. No behavioral changes.

After this WP:
- `grep -r "from specify_cli.sync" src/specify_cli/dossier/ --include="*.py"` returns **empty**
- All dossier/sync tests pass at 100%
- An architectural guard test enforces the boundary permanently

## Context

**The cycle today:**
```
specify_cli.dossier.drift_detector  ──runtime──▶  specify_cli.sync.project_identity
specify_cli.sync.dossier_pipeline   ──lazy──▶     specify_cli.dossier.*
```

The first edge (`dossier → sync`) is the forbidden one. `sync → dossier` (lazy/TYPE_CHECKING) is acceptable and doesn't need to change.

**Why `specify_cli.identity`?** This package already exists as a "leaf package with no dependencies on core or status". Its `__init__.py` documents this explicitly. `ProjectIdentity` is used by sync, dossier, tracker, and CLI simultaneously, so it cannot live in any domain package. The `identity/` leaf is the correct neutral home.

**What exactly moves?** Everything in `src/specify_cli/sync/project_identity.py`:
- `ProjectIdentity` dataclass
- `generate_project_uuid()`, `generate_build_id()`, `derive_project_slug()`
- `generate_node_id()` — **inlined** (replaces `sync.clock` import)
- `is_writable()`, `atomic_write_config()`, `load_identity()`, `ensure_identity()`, `_warn_in_memory()`

**Callers that keep using the old path (via shim — no changes needed):**

| Module | Import type |
|--------|-------------|
| `sync/client.py:34` | runtime module-level |
| `sync/dossier_pipeline.py:16` | TYPE_CHECKING |
| `sync/dossier_pipeline.py:229` | lazy function-body |
| `sync/namespace.py:18` | TYPE_CHECKING |
| `tracker/origin.py:449` | lazy function-body |
| `cli/commands/tracker.py:28` | runtime module-level |

Only `dossier/drift_detector.py` gets updated to import from the new canonical path.

---

## Subtask T001 — Create `src/specify_cli/identity/project.py`

**Purpose**: Establish the canonical home for `ProjectIdentity` with no `specify_cli.sync` dependency.

**Steps**:

1. Copy the full contents of `src/specify_cli/sync/project_identity.py` into a new file `src/specify_cli/identity/project.py`.

2. Replace the single sync dependency. Current line in `sync/project_identity.py`:
   ```python
   from specify_cli.sync.clock import generate_node_id as generate_machine_node_id
   ```
   Delete this import. Instead, add a standalone `generate_node_id()` function **in the body** of `identity/project.py` (place it near the other generator functions, before `is_writable`):
   ```python
   def generate_node_id() -> str:
       """Generate stable machine identifier from hostname + username.

       Returns first 12 characters of SHA-256 hash for anonymization.
       Same value across CLI restarts, different per user on shared machines.
       """
       import getpass
       import hashlib
       import socket
       hostname = socket.gethostname()
       username = getpass.getuser()
       raw = f"{hostname}:{username}"
       return hashlib.sha256(raw.encode()).hexdigest()[:12]
   ```
   (Prefer top-level imports; move `import getpass`, `import hashlib`, `import socket` to the module-level import block at the top of the file if they aren't already there.)

3. Find all uses of `generate_machine_node_id` inside the file (used in `generate_node_id()` — wait, verify this). In the original, `project_identity.py` has:
   ```python
   def generate_node_id() -> str:
       return generate_machine_node_id()
   ```
   After the change, `generate_node_id()` is self-contained; delete the wrapper delegation.

4. Verify `identity/project.py` has zero imports from `specify_cli.sync` or `specify_cli.dossier`:
   ```bash
   grep "from specify_cli.sync\|from specify_cli.dossier" src/specify_cli/identity/project.py
   # Expected: empty output
   ```

5. Add a convenience re-export to `src/specify_cli/identity/__init__.py`. Read the current `__init__.py` first, then append (do not replace existing content):
   ```python
   from specify_cli.identity.project import ProjectIdentity as ProjectIdentity  # noqa: F401
   ```
   This allows callers to use `from specify_cli.identity import ProjectIdentity` as a short-form import. Place it after any existing imports in `__init__.py`.

**Files**:
- `src/specify_cli/identity/project.py` (new, ~220 lines)
- `src/specify_cli/identity/__init__.py` (modified: 1-line re-export added)

**Validation**:
- [ ] File exists with all classes and functions from original `sync/project_identity.py`
- [ ] `generate_node_id()` is self-contained (no sync imports)
- [ ] `from __future__ import annotations` present at top
- [ ] All existing type annotations preserved
- [ ] `uv run python -c "from specify_cli.identity.project import ProjectIdentity; print('OK')"` succeeds
- [ ] `uv run python -c "from specify_cli.identity import ProjectIdentity; print('OK')"` succeeds

---

## Subtask T002 — Replace `src/specify_cli/sync/project_identity.py` with Shim

**Purpose**: Keep all existing callers working unchanged by re-exporting everything from the new canonical location.

**Steps**:

1. Replace the entire contents of `src/specify_cli/sync/project_identity.py` with:

   ```python
   """Backward-compatible shim.

   The canonical home for ProjectIdentity is specify_cli.identity.project.
   This module re-exports all public names for backward compatibility.
   Callers outside specify_cli.dossier may continue to import from here.
   """
   from specify_cli.identity.project import (  # noqa: F401
       ProjectIdentity,
       atomic_write_config,
       derive_project_slug,
       ensure_identity,
       generate_build_id,
       generate_node_id,
       generate_project_uuid,
       is_writable,
       load_identity,
   )

   __all__ = [
       "ProjectIdentity",
       "atomic_write_config",
       "derive_project_slug",
       "ensure_identity",
       "generate_build_id",
       "generate_node_id",
       "generate_project_uuid",
       "is_writable",
       "load_identity",
   ]
   ```

2. Do NOT add a `DeprecationWarning` at this stage — the constraint (C-002) says shims must not be removed until all callers have migrated; adding a warning would surface noise in CI before that migration is complete.

3. Verify the shim works for the original callers:
   ```bash
   uv run python -c "from specify_cli.sync.project_identity import ProjectIdentity, ensure_identity; print('shim OK')"
   ```

**Files**:
- `src/specify_cli/sync/project_identity.py` (replaced, ~25 lines)

**Validation**:
- [ ] File exists and has the re-export pattern (no logic)
- [ ] All 9 public names are re-exported
- [ ] Shim import works at runtime

---

## Subtask T003 — Update `src/specify_cli/dossier/drift_detector.py`

**Purpose**: The one and only dossier module with a sync import; update it to use the canonical path.

**Steps**:

1. Open `src/specify_cli/dossier/drift_detector.py`.

2. Find line 30 (or the line containing):
   ```python
   from specify_cli.sync.project_identity import ProjectIdentity
   ```

3. Change it to:
   ```python
   from specify_cli.identity.project import ProjectIdentity
   ```

4. That's it. The `ProjectIdentity` class is identical; no other code changes needed.

5. Verify the change:
   ```bash
   grep "from specify_cli.sync" src/specify_cli/dossier/drift_detector.py
   # Expected: empty output
   ```

**Files**:
- `src/specify_cli/dossier/drift_detector.py` (1-line change)

**Validation**:
- [ ] No `from specify_cli.sync` anywhere in the file
- [ ] `uv run python -c "from specify_cli.dossier.drift_detector import detect_drift; print('OK')"` succeeds

---

## Subtask T004 — Create `tests/architectural/test_dossier_sync_boundary.py`

**Purpose**: Permanently enforce that no `specify_cli.dossier` module imports `specify_cli.sync`, including lazy function-body imports and TYPE_CHECKING blocks.

**Steps**:

1. Create `tests/architectural/test_dossier_sync_boundary.py`:

   ```python
   """Architectural guard: no dossier → sync import edges.

   Enforces the boundary fixed in GitHub issue #862 (P1.2).
   This test must remain in CI permanently to prevent regression.
   Uses stdlib ``ast`` to walk ALL imports in every .py file under
   src/specify_cli/dossier/, including:
   - Module-level imports
   - Imports inside ``if TYPE_CHECKING:`` blocks
   - Lazy function-body imports
   """
   from __future__ import annotations

   import ast
   from pathlib import Path

   import pytest

   SRC = Path(__file__).resolve().parents[2] / "src"
   DOSSIER_PATH = SRC / "specify_cli" / "dossier"

   pytestmark = pytest.mark.architectural


   def _collect_imports(package_path: Path) -> list[tuple[str, str]]:
       """Return (source_file, imported_module) for all imports in a package.

       Walks the full AST including function bodies and TYPE_CHECKING blocks.
       """
       edges: list[tuple[str, str]] = []
       for py_file in sorted(package_path.rglob("*.py")):
           try:
               tree = ast.parse(py_file.read_text(encoding="utf-8"))
           except SyntaxError:
               continue
           for node in ast.walk(tree):
               if isinstance(node, ast.ImportFrom) and node.module:
                   edges.append((str(py_file.relative_to(SRC)), node.module))
               elif isinstance(node, ast.Import):
                   for alias in node.names:
                       edges.append((str(py_file.relative_to(SRC)), alias.name))
       return edges


   class TestDossierSyncBoundary:
       """specify_cli.dossier must not import specify_cli.sync."""

       def test_dossier_does_not_import_sync(self) -> None:
           """No dossier module may import from specify_cli.sync (any sub-module)."""
           edges = _collect_imports(DOSSIER_PATH)
           violations = [
               f"  {src}: imports '{mod}'"
               for src, mod in edges
               if mod == "specify_cli.sync" or mod.startswith("specify_cli.sync.")
           ]
           assert not violations, (
               "specify_cli.dossier must not import specify_cli.sync.\n"
               "Violations found (including lazy and TYPE_CHECKING imports):\n"
               + "\n".join(violations)
               + "\n\nFix: import from specify_cli.identity.project instead of sync."
           )

       def test_dossier_path_exists(self) -> None:
           """Sanity check: dossier package must exist so the boundary test is non-vacuous."""
           assert DOSSIER_PATH.is_dir(), (
               f"specify_cli.dossier not found at {DOSSIER_PATH}. "
               "Update SRC or DOSSIER_PATH if the package moved."
           )
   ```

2. Run it immediately (should pass after T001-T003 are done):
   ```bash
   uv run pytest tests/architectural/test_dossier_sync_boundary.py -v
   ```

**Files**:
- `tests/architectural/test_dossier_sync_boundary.py` (new, ~65 lines)

**Validation**:
- [ ] Test file exists
- [ ] `test_dossier_does_not_import_sync` passes
- [ ] `test_dossier_path_exists` passes
- [ ] Running the test against the pre-fix codebase (before T003) would FAIL

---

## Subtask T005 — Verification Run

**Purpose**: Confirm the full WP01 change set is clean before marking done.

**Steps**:

Run each check in order. All must exit 0:

```bash
# 1. Ruff on affected paths
uv run ruff check \
  src/specify_cli/identity/project.py \
  src/specify_cli/identity/__init__.py \
  src/specify_cli/sync/project_identity.py \
  src/specify_cli/dossier/drift_detector.py \
  tests/architectural/test_dossier_sync_boundary.py

# 2. mypy --strict on new files (charter requirement: zero new type errors)
uv run mypy --strict \
  src/specify_cli/identity/project.py \
  src/specify_cli/identity/__init__.py

# 3. Confirm no dossier → sync imports remain
grep -r "from specify_cli.sync" src/specify_cli/dossier/ --include="*.py"
# Expected: empty

# 4. Dossier test suite
uv run pytest tests/dossier -q

# 5. Sync test suite (shim must not break sync callers)
uv run pytest tests/sync -q

# 6. Architectural guard
uv run pytest tests/architectural/test_dossier_sync_boundary.py -v

# 7. Quick smoke test of import chains
uv run python -c "
from specify_cli.identity.project import ProjectIdentity, ensure_identity
from specify_cli.sync.project_identity import ProjectIdentity as PI2, ensure_identity as ei2
from specify_cli.dossier.drift_detector import detect_drift
assert ProjectIdentity is PI2, 'shim and canonical must be same class'
print('All import chains OK')
"
```

**Validation**:
- [ ] All ruff checks pass (0 violations)
- [ ] mypy --strict passes on `identity/project.py` and `identity/__init__.py`
- [ ] grep for `from specify_cli.sync` in dossier returns empty
- [ ] `tests/dossier` suite green
- [ ] `tests/sync` suite green
- [ ] Architectural guard test green
- [ ] Import smoke test prints "All import chains OK"

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: Allocated by `spec-kitty agent action implement WP01 --agent claude`. The workspace is a worktree under `.worktrees/` computed from `lanes.json`. Do not hard-code any path.
- Do NOT modify files outside `owned_files` listed in this frontmatter.

## Definition of Done

- [ ] `src/specify_cli/identity/project.py` exists, contains all logic from former `sync/project_identity.py`, has zero `specify_cli.sync` imports
- [ ] `src/specify_cli/sync/project_identity.py` is a shim (re-exports only, ~25 lines)
- [ ] `src/specify_cli/dossier/drift_detector.py` imports `ProjectIdentity` from `specify_cli.identity.project`
- [ ] `tests/architectural/test_dossier_sync_boundary.py` exists and passes
- [ ] All verification commands in T005 exit 0
- [ ] No changes to any file outside the `owned_files` list

## Risks

- **`generate_node_id` output mismatch**: The inlined function must use the same algorithm as `sync.clock.generate_node_id` (SHA-256 of `"{hostname}:{username}"`, first 12 hex chars). Verify with a spot check.
- **Missing public names in shim**: If any name exported by `sync.project_identity` is missed in the shim, existing callers will get `ImportError`. Run the smoke test in T005.
- **`_warn_in_memory` is private**: It should NOT be in `__all__` but may be referenced internally. Check for any external callers before deciding whether to include it in the shim.

## Reviewer Guidance

1. Confirm `identity/project.py` has NO `from specify_cli.sync` imports (use grep, not visual inspection).
2. Confirm `sync/project_identity.py` contains ONLY re-export statements, no logic.
3. Confirm `drift_detector.py` has exactly ONE changed line (import path).
4. Run the T005 verification commands directly — do not accept the PR without running them.
5. The architectural guard test should FAIL if you revert T003 and run it again. Verify this manually once.

## Activity Log

- 2026-05-01T04:38:24Z – claude – shell_pid=88144 – WP01 complete: all 5 subtasks done, 311 dossier + 1456 sync tests pass, architectural guard green
- 2026-05-01T04:58:12Z – claude – shell_pid=88144 – Reopening: dossier/events.py still has 4 sync imports; FR-002/NFR-001 not yet satisfied. Expanding scope to invert the emitter dependency.
- 2026-05-01T05:10:59Z – claude – shell_pid=88144 – Amended: dossier/events.py inverted to use emitter_adapter; guard test no longer carries pre-existing exceptions; 1769 dossier+sync tests pass
- 2026-05-01T05:11:41Z – codex:gpt-4o:python-pedro:reviewer – shell_pid=4258 – Started review via action command

---
work_package_id: WP02
title: 'P1.3: Status Fan-out Adapter'
dependencies: []
requirement_refs:
- C-001
- FR-005
- FR-006
- FR-007
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Feature branch from main; merged back to main after review
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: claude
history:
- date: '2026-04-30'
  event: Created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/adapters.py
execution_mode: code_change
owned_files:
- src/specify_cli/status/adapters.py
- src/specify_cli/status/emit.py
- src/specify_cli/sync/__init__.py
- tests/architectural/test_status_sync_boundary.py
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

Break the **P1.3 status → sync import cycle** (GitHub issue #862) by introducing a lightweight callback-registry adapter in `status/adapters.py`. `status/emit.py` calls the adapters instead of lazy-importing from `specify_cli.sync`. The sync package registers its handlers at startup, reversing the dependency direction to the clean `sync → status.adapters` shape. No behavioral changes to fan-out or status persistence.

After this WP:
- `grep -r "from specify_cli.sync" src/specify_cli/status/ --include="*.py"` returns **empty**
- All status/sync/contract tests pass at 100% (including with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`)
- An architectural guard test enforces the boundary permanently

## Context

**The cycles today (both in `status/emit.py`):**

```python
# Step 8 — dossier sync trigger (lazy, inside emit_status_transition):
from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
trigger_feature_dossier_sync_if_enabled(feature_dir, mission_slug, repo_root)

# Step 9 / _saas_fan_out() — SaaS telemetry (lazy, inside try/except):
from specify_cli.sync.events import emit_wp_status_changed
emit_wp_status_changed(wp_id=..., ...)
```

Both are lazy (function-body) imports. Static scanners still count them as `status → sync` edges.

**Target design:**

```
status/emit.py  ──imports──▶  status/adapters.py  ◀──registers──  sync/__init__.py
                                     │
                                fire_*(...)  ──calls──▶  registered handlers
```

`status/adapters.py` has zero imports from `specify_cli.sync`. Sync imports from `status.adapters` to register (sync → status is the clean direction).

**Behavioral guarantees that MUST be preserved:**

| Guarantee | How it's preserved |
|-----------|-------------------|
| Canonical status persistence is never blocked by fan-out failures | `fire_*` wraps each handler call in `try/except Exception` |
| Dossier sync is fire-and-forget | `fire_dossier_sync` does not inspect return value |
| SaaS fan-out is best-effort | Same `try/except` approach in `fire_saas_fanout` |
| No handlers = no-ops | Empty registry → loop body never executes |
| Sync disabled = no fan-out | `trigger_feature_dossier_sync_if_enabled` checks `is_saas_sync_enabled()` internally |

---

## Subtask T006 — Create `src/specify_cli/status/adapters.py`

**Purpose**: The decoupling layer — a simple callback registry that `emit.py` can call without importing sync.

**Steps**:

1. Create `src/specify_cli/status/adapters.py` with the following content:

   ```python
   """Fan-out adapter registry for status events.

   Provides a decoupled callback boundary so that status/emit.py
   does not need to import from specify_cli.sync. The sync package
   registers its handlers at startup (sync -> status.adapters is the
   clean dependency direction).

   All fire_* functions are non-raising: exceptions from handlers are
   caught and logged, never re-raised to the caller.
   """
   from __future__ import annotations

   import logging
   from pathlib import Path
   from typing import Any, Callable

   logger = logging.getLogger(__name__)

   # Callback type: (feature_dir, mission_slug, repo_root) → None
   DossierSyncHandler = Callable[[Path, str, Path], None]

   # Callback type: called with keyword args matching emit_wp_status_changed
   SaasFanOutHandler = Callable[..., None]

   _dossier_handlers: list[DossierSyncHandler] = []
   _saas_handlers: list[SaasFanOutHandler] = []


   def register_dossier_sync_handler(cb: DossierSyncHandler) -> None:
       """Register a dossier-sync callback.

       Called once at sync package startup. Not thread-safe by design
       (registration happens before concurrent access begins).
       """
       _dossier_handlers.append(cb)


   def register_saas_fanout_handler(cb: SaasFanOutHandler) -> None:
       """Register a SaaS fan-out callback.

       Called once at sync package startup.
       """
       _saas_handlers.append(cb)


   def fire_dossier_sync(
       feature_dir: Path,
       mission_slug: str,
       repo_root: Path,
   ) -> None:
       """Call all registered dossier-sync handlers.

       Guarantees:
       - Handlers called in registration order.
       - Exceptions are caught per-handler, logged at DEBUG level,
         and never propagate to the caller.
       - If no handlers are registered, this is a no-op.
       """
       for handler in _dossier_handlers:
           try:
               handler(feature_dir, mission_slug, repo_root)
           except Exception:
               logger.debug(
                   "Dossier sync handler failed; never blocks status transitions",
                   exc_info=True,
               )


   def fire_saas_fanout(**kwargs: Any) -> None:
       """Call all registered SaaS fan-out handlers with **kwargs.

       Guarantees:
       - Handlers called in registration order.
       - Exceptions are caught per-handler, logged at WARNING level,
         and never propagate to the caller.
       - If no handlers are registered, this is a no-op.
       """
       for handler in _saas_handlers:
           try:
               handler(**kwargs)
           except Exception:
               logger.warning(
                   "SaaS fan-out handler failed; canonical status log unaffected",
                   exc_info=True,
               )
   ```

2. Verify zero `specify_cli.sync` imports:
   ```bash
   grep "from specify_cli.sync\|import specify_cli.sync" src/specify_cli/status/adapters.py
   # Expected: empty
   ```

**Files**:
- `src/specify_cli/status/adapters.py` (new, ~75 lines)

**Validation**:
- [ ] File exists with both registry lists and all 4 public functions
- [ ] `uv run python -c "from specify_cli.status.adapters import fire_dossier_sync, fire_saas_fanout; print('OK')"` succeeds
- [ ] No `specify_cli.sync` imports in file
- [ ] `uv run ruff check src/specify_cli/status/adapters.py` exits 0

---

## Subtask T007 — Update `src/specify_cli/status/emit.py`

**Purpose**: Remove the two lazy sync imports from `emit.py` and replace them with calls to the new adapter.

**Steps**:

1. Add the adapter import near the top of `emit.py` (with the other status-internal imports, after the existing `.models` and `.transitions` imports):
   ```python
   from specify_cli.status.adapters import fire_dossier_sync, fire_saas_fanout
   ```

2. **Step 8 replacement** (dossier sync trigger, inside `emit_status_transition()`):

   Find the current block (around line 487):
   ```python
   # Step 8: Dossier sync (fire-and-forget, never blocks)
   if sync_dossier and repo_root is not None:
       try:
           from specify_cli.sync.dossier_pipeline import (
               trigger_feature_dossier_sync_if_enabled,
           )

           trigger_feature_dossier_sync_if_enabled(
               feature_dir,
               mission_slug,
               repo_root,
           )
       except Exception:
           logger.debug("Dossier sync failed; never blocks status transitions", exc_info=True)
   ```

   Replace with:
   ```python
   # Step 8: Dossier sync (fire-and-forget, never blocks)
   if sync_dossier and repo_root is not None:
       fire_dossier_sync(feature_dir, mission_slug, repo_root)
   ```

   The try/except moves inside `fire_dossier_sync`; the guard `if sync_dossier and repo_root is not None` stays here.

3. **`_saas_fan_out()` replacement** (around line 518):

   Find the entire `_saas_fan_out()` function. Its body currently does:
   ```python
   try:
       from specify_cli.sync.events import emit_wp_status_changed
       emit_wp_status_changed(
           wp_id=event.wp_id,
           from_lane=str(event.from_lane),
           to_lane=str(event.to_lane),
           actor=event.actor,
           mission_slug=mission_slug,
           mission_id=event.mission_id,
           causation_id=event.event_id,
           policy_metadata=policy_metadata,
           force=event.force,
           reason=event.reason,
           review_ref=event.review_ref,
           execution_mode=event.execution_mode,
           evidence=event.evidence.to_dict() if event.evidence else None,
           ensure_daemon=ensure_sync_daemon,
       )
   except ImportError:
       pass  # SaaS sync not available (0.1x branch)
   except Exception:
       logger.warning(
           "SaaS fan-out failed for event %s; canonical log unaffected",
           ...
       )
   ```

   Replace the body with:
   ```python
   fire_saas_fanout(
       wp_id=event.wp_id,
       from_lane=str(event.from_lane),
       to_lane=str(event.to_lane),
       actor=event.actor,
       mission_slug=mission_slug,
       mission_id=event.mission_id,
       causation_id=event.event_id,
       policy_metadata=policy_metadata,
       force=event.force,
       reason=event.reason,
       review_ref=event.review_ref,
       execution_mode=event.execution_mode,
       evidence=event.evidence.to_dict() if event.evidence else None,
       ensure_daemon=ensure_sync_daemon,
   )
   ```

   The `try/except ImportError` is no longer needed (no import to fail). The `try/except Exception` moves inside `fire_saas_fanout`. The function signature of `_saas_fan_out` stays unchanged.

4. Confirm zero `from specify_cli.sync` imports remain in the file:
   ```bash
   grep "from specify_cli.sync" src/specify_cli/status/emit.py
   # Expected: empty
   ```

**Files**:
- `src/specify_cli/status/emit.py` (modified)

**Validation**:
- [ ] `from specify_cli.status.adapters import fire_dossier_sync, fire_saas_fanout` added at top
- [ ] Step 8 block no longer contains any sync import
- [ ] `_saas_fan_out()` body no longer contains any sync import
- [ ] grep for `from specify_cli.sync` in file returns empty
- [ ] `uv run ruff check src/specify_cli/status/emit.py` exits 0

---

## Subtask T008 — Register Sync Handlers at Startup

**Purpose**: Make sync register its own callbacks into the adapter registry, so fan-out still works end-to-end even though `emit.py` no longer imports from sync.

**Steps**:

1. First, read `src/specify_cli/sync/__init__.py` to understand its current content. If it is empty or minimal, adding registration there is correct. If it has an explicit `__all__` or re-export structure, add the registration at the end.

2. Add handler registration. The sync package is allowed to import from `status.adapters` (sync → status is the clean direction):

   ```python
   # At the bottom of src/specify_cli/sync/__init__.py
   # Register status fan-out handlers so that canonical status events
   # continue to trigger SaaS sync and dossier-sync side effects
   # without status/emit.py importing from sync directly.
   from __future__ import annotations

   import contextlib

   with contextlib.suppress(Exception):
       from specify_cli.status.adapters import (
           register_dossier_sync_handler,
           register_saas_fanout_handler,
       )
       from specify_cli.sync.dossier_pipeline import (
           trigger_feature_dossier_sync_if_enabled,
       )
       from specify_cli.sync.events import emit_wp_status_changed

       register_dossier_sync_handler(trigger_feature_dossier_sync_if_enabled)
       register_saas_fanout_handler(emit_wp_status_changed)
   ```

   **Why `contextlib.suppress(Exception)`?** The registration is best-effort at module import time. If any of the sync sub-modules fail to import (e.g., in a minimal test environment without all dependencies), the registration is silently skipped and `fire_*` remains a no-op. This preserves the existing behavior where SaaS fan-out is absent in 0.1x environments.

3. **Important**: Check for circular import. When `sync/__init__.py` imports `status.adapters`, and `status/emit.py` imports `status.adapters` — there is no circular dependency because `adapters.py` does NOT import from sync. Verify this reasoning by running:
   ```bash
   uv run python -c "import specify_cli.sync; print('sync import OK')"
   uv run python -c "import specify_cli.status.emit; print('emit import OK')"
   ```

4. If registration in `__init__.py` causes issues (e.g., the module is imported very early before sync deps are ready), an alternative is to register inside the sync daemon startup function. Inspect `src/specify_cli/sync/` for the daemon entry point and add registration there instead. Document the decision in a comment.

**Files**:
- `src/specify_cli/sync/__init__.py` (modified)

**Validation**:
- [ ] Registration code added (with `contextlib.suppress` guard)
- [ ] `uv run python -c "import specify_cli.sync; print('OK')"` succeeds
- [ ] `uv run python -c "from specify_cli.status.adapters import _dossier_handlers; import specify_cli.sync; print(len(_dossier_handlers), 'dossier handlers registered')"` prints `1 dossier handlers registered`
- [ ] No circular import errors

---

## Subtask T009 — Create `tests/architectural/test_status_sync_boundary.py`

**Purpose**: Permanently enforce that no `specify_cli.status` module imports `specify_cli.sync`.

**Steps**:

1. Create `tests/architectural/test_status_sync_boundary.py`:

   ```python
   """Architectural guard: no status → sync import edges.

   Enforces the boundary fixed in GitHub issue #862 (P1.3).
   This test must remain in CI permanently to prevent regression.
   Uses stdlib ``ast`` to walk ALL imports in every .py file under
   src/specify_cli/status/, including:
   - Module-level imports
   - Imports inside ``if TYPE_CHECKING:`` blocks
   - Lazy function-body imports
   """
   from __future__ import annotations

   import ast
   from pathlib import Path

   import pytest

   SRC = Path(__file__).resolve().parents[2] / "src"
   STATUS_PATH = SRC / "specify_cli" / "status"

   pytestmark = pytest.mark.architectural


   def _collect_imports(package_path: Path) -> list[tuple[str, str]]:
       """Return (source_file, imported_module) for all imports in a package."""
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


   class TestStatusSyncBoundary:
       """specify_cli.status must not import specify_cli.sync."""

       def test_status_does_not_import_sync(self) -> None:
           """No status module may import from specify_cli.sync (any sub-module)."""
           edges = _collect_imports(STATUS_PATH)
           violations = [
               f"  {src}: imports '{mod}'"
               for src, mod in edges
               if mod == "specify_cli.sync" or mod.startswith("specify_cli.sync.")
           ]
           assert not violations, (
               "specify_cli.status must not import specify_cli.sync.\n"
               "Violations found (including lazy and TYPE_CHECKING imports):\n"
               + "\n".join(violations)
               + "\n\nFix: use specify_cli.status.adapters.fire_* instead."
           )

       def test_status_path_exists(self) -> None:
           """Sanity check: status package must exist so the boundary test is non-vacuous."""
           assert STATUS_PATH.is_dir(), (
               f"specify_cli.status not found at {STATUS_PATH}. "
               "Update SRC or STATUS_PATH if the package moved."
           )
   ```

2. Run it:
   ```bash
   uv run pytest tests/architectural/test_status_sync_boundary.py -v
   ```

**Files**:
- `tests/architectural/test_status_sync_boundary.py` (new, ~65 lines)

**Validation**:
- [ ] Test file exists
- [ ] `test_status_does_not_import_sync` passes
- [ ] `test_status_path_exists` passes
- [ ] Running the test against unmodified `emit.py` (before T007) would FAIL

---

## Subtask T010 — Verification Run

**Purpose**: Full end-to-end confirmation that the WP02 change set is clean and behaviorally identical.

**Steps**:

Run each check in order. All must exit 0:

```bash
# 1. Ruff on affected paths
uv run ruff check \
  src/specify_cli/status/adapters.py \
  src/specify_cli/status/emit.py \
  src/specify_cli/sync/__init__.py \
  tests/architectural/test_status_sync_boundary.py

# 2. Confirm no status → sync imports remain
grep -r "from specify_cli.sync" src/specify_cli/status/ --include="*.py"
# Expected: empty

# 3. Status test suite
uv run pytest tests/status -q

# 4. Sync test suite (registration must not break sync internals)
uv run pytest tests/sync -q

# 5. Contract tests (body sync and tracker bind behavior must be preserved)
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest \
  tests/contract/test_body_sync.py \
  tests/contract/test_tracker_bind.py \
  -q

# 6. Architectural guard
uv run pytest tests/architectural/test_status_sync_boundary.py -v

# 7. Handler registration smoke test
uv run python -c "
from specify_cli.status.adapters import _dossier_handlers, _saas_handlers
import specify_cli.sync  # triggers registration
print(f'Dossier handlers: {len(_dossier_handlers)}')
print(f'SaaS handlers: {len(_saas_handlers)}')
assert len(_dossier_handlers) == 1, 'Expected 1 dossier handler'
assert len(_saas_handlers) == 1, 'Expected 1 SaaS handler'
print('Handler registration OK')
"
```

**Validation**:
- [ ] All ruff checks pass (0 violations)
- [ ] grep for `from specify_cli.sync` in status returns empty
- [ ] `tests/status` green
- [ ] `tests/sync` green
- [ ] Contract tests green (with SAAS_SYNC enabled)
- [ ] Architectural guard green
- [ ] Handler registration smoke test passes

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: Allocated by `spec-kitty agent action implement WP02 --agent claude`. Workspace is a worktree computed from `lanes.json`. Do not hard-code any path.
- Do NOT modify files outside `owned_files` listed in this frontmatter.

## Definition of Done

- [ ] `src/specify_cli/status/adapters.py` exists with two registries and four public functions; zero sync imports
- [ ] `src/specify_cli/status/emit.py` has no `from specify_cli.sync.*` imports anywhere in the file
- [ ] `src/specify_cli/sync/__init__.py` registers both handlers (with `contextlib.suppress` guard)
- [ ] `tests/architectural/test_status_sync_boundary.py` exists and passes
- [ ] All verification commands in T010 exit 0
- [ ] No changes to any file outside the `owned_files` list

## Risks

- **Handler registration timing**: If `sync/__init__.py` is not imported before the first `emit_status_transition()` call in a test, no handlers are registered and SaaS fan-out silently doesn't fire. This is correct behavior in pure status tests (they don't want sync side effects), but contract tests with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` must import sync first.
- **`_saas_fan_out` function signature**: If `_saas_fan_out` has additional callers beyond `emit_status_transition`, they must also pass kwargs that match `emit_wp_status_changed`. Verify there is only one call site.
- **`contextlib.suppress` hiding real errors**: If `sync/__init__.py` registration fails silently due to a real bug (not just missing deps), the fan-out will be a no-op. The smoke test in T010 catches this.

## Reviewer Guidance

1. Confirm `status/adapters.py` has ZERO `from specify_cli.sync` imports (grep, not visual inspection).
2. Confirm `status/emit.py` has ZERO `from specify_cli.sync` imports (grep).
3. Confirm `sync/__init__.py` contains registration with `contextlib.suppress` guard.
4. Run T010 verification commands directly — do not accept the PR without them.
5. Check that contract tests pass with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (this exercises the handler registration path).
6. The architectural guard test should FAIL if you revert T007 and run it. Verify once.

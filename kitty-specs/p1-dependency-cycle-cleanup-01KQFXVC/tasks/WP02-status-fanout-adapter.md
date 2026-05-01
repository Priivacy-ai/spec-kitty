---
work_package_id: WP02
title: 'P1.3: Status Fan-out Adapter'
dependencies:
- WP01
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
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-p1-dependency-cycle-cleanup-01KQFXVC
base_commit: ff01ad7e4f20bfa40463c7a65ef7e4e7121dcb4d
created_at: '2026-05-01T04:38:59.096157+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "codex:gpt-4o:python-pedro:reviewer"
shell_pid: "79820"
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
- tests/status/test_emit.py
- tests/status/test_emit_fanout_after_adapter.py
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

**Purpose**: Make sync register its own callbacks into the adapter registry (and the dossier emitter adapter from WP01), so fan-out still works end-to-end even though `emit.py` no longer imports from sync.

**Steps**:

1. Read `src/specify_cli/sync/__init__.py` first. The current file has a docstring and module-level imports/exports. The `from __future__ import annotations` directive (if any) **must** stay at the top of the file after the docstring. Do **NOT** add a duplicate future import at the bottom of the file — Python will raise `SyntaxError: from __future__ imports must occur at the beginning of the file`.

2. Append handler registration **after** all existing imports and `__all__` (i.e., at the very end of the file). Use only standard library names that are already in scope; do not add a `from __future__ import` here. The sync package is allowed to import from `status.adapters` and `dossier.emitter_adapter` (sync → status, sync → dossier are the clean directions):

   ```python
   # ─── Adapter registration (run at import time) ──────────────────────
   # Register handlers so that canonical status events trigger SaaS sync
   # and dossier-sync side effects, and dossier event emission routes
   # through the existing sync emitter, without status/emit.py or
   # dossier/events.py importing from specify_cli.sync directly.
   #
   # NOTE: This block must remain at the BOTTOM of the file. The
   # contextlib.suppress is intentional: if any sync sub-module fails to
   # import in a minimal/test environment, registration is silently
   # skipped and the fire_* / fire_dossier_event functions become no-ops.
   # That preserves the existing behavior where SaaS sync is absent in
   # 0.1x environments.
   import contextlib as _contextlib

   with _contextlib.suppress(Exception):
       from specify_cli.status.adapters import (
           register_dossier_sync_handler,
           register_saas_fanout_handler,
       )
       from specify_cli.sync.dossier_pipeline import (
           trigger_feature_dossier_sync_if_enabled,
       )
       from specify_cli.sync.events import emit_wp_status_changed, get_emitter

       register_dossier_sync_handler(trigger_feature_dossier_sync_if_enabled)
       register_saas_fanout_handler(emit_wp_status_changed)

   with _contextlib.suppress(Exception):
       # Register dossier emitter (WP01 inversion). The lambda routes
       # through get_emitter() lazily so the late-binding behavior of the
       # emitter singleton is preserved.
       from specify_cli.dossier.emitter_adapter import register_dossier_emitter

       def _dossier_emit_via_sync(
           *, event_type: str, aggregate_id: str, aggregate_type: str, payload: dict
       ) -> dict:
           return get_emitter()._emit(  # type: ignore[no-any-return]
               event_type=event_type,
               aggregate_id=aggregate_id,
               aggregate_type=aggregate_type,
               payload=payload,
           )

       register_dossier_emitter(_dossier_emit_via_sync)
   ```

3. **Verify no circular import**: `status/adapters.py` and `dossier/emitter_adapter.py` both have zero imports from `specify_cli.sync`, so the new edge is `sync → status.adapters` and `sync → dossier.emitter_adapter`, both clean. Verify:
   ```bash
   uv run python -c "import specify_cli.sync; print('sync import OK')"
   uv run python -c "import specify_cli.status.emit; print('emit import OK')"
   uv run python -c "import specify_cli.dossier.events; print('dossier events import OK')"
   ```

4. **Verify all four registrations happen on a fresh sync import**:
   ```bash
   uv run python -c "
   from specify_cli.status.adapters import _dossier_handlers, _saas_handlers
   from specify_cli.dossier.emitter_adapter import _emitter
   import specify_cli.sync  # triggers registration
   assert len(_dossier_handlers) == 1, f'expected 1 dossier-sync handler, got {len(_dossier_handlers)}'
   assert len(_saas_handlers) == 1, f'expected 1 saas handler, got {len(_saas_handlers)}'
   from specify_cli.dossier import emitter_adapter
   assert emitter_adapter._emitter is not None, 'dossier emitter not registered'
   print('All 3 handlers + 1 emitter registered OK')
   "
   ```

5. **Bootstrap caveat for tests**: Status transitions called from a test process that has not imported `specify_cli.sync` will silently lose fan-out (`fire_*` becomes a no-op, `fire_dossier_event` returns `None`). This is correct for unit tests of status that don't want sync side effects. For integration tests that DO want fan-out (e.g., contract tests with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`), import `specify_cli.sync` once during fixture setup. The CLI itself imports sync transitively through its commands, so production paths are not affected.

**Files**:
- `src/specify_cli/sync/__init__.py` (modified)

**Validation**:
- [ ] Registration code added at the BOTTOM of the file (no `from __future__` at the bottom)
- [ ] `uv run python -c "import specify_cli.sync"` succeeds without `SyntaxError`
- [ ] All four registrations succeed on fresh import (verification step 4)
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

# 2. mypy --strict on the new adapter file (charter requirement: zero new type errors)
uv run mypy --strict src/specify_cli/status/adapters.py

# 3. Confirm no status → sync imports remain
grep -r "from specify_cli.sync" src/specify_cli/status/ --include="*.py"
# Expected: empty

# 4. Status test suite
uv run pytest tests/status -q

# 5. Sync test suite (registration must not break sync internals)
uv run pytest tests/sync -q

# 6. Contract tests (body sync and tracker bind behavior must be preserved)
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest \
  tests/contract/test_body_sync.py \
  tests/contract/test_tracker_bind.py \
  -q

# 7. Architectural guard
uv run pytest tests/architectural/test_status_sync_boundary.py -v

# 8. Handler + emitter registration smoke test (verifies the
#    inversion wired up by sync/__init__.py for both WP01 dossier
#    emitter and WP02 status fan-out)
uv run python -c "
from specify_cli.status.adapters import _dossier_handlers, _saas_handlers
from specify_cli.dossier import emitter_adapter
import specify_cli.sync  # triggers registration of all 3
print(f'Dossier sync handlers: {len(_dossier_handlers)}')
print(f'SaaS handlers: {len(_saas_handlers)}')
print(f'Dossier emitter: {emitter_adapter._emitter is not None}')
assert len(_dossier_handlers) == 1, 'Expected 1 dossier-sync handler'
assert len(_saas_handlers) == 1, 'Expected 1 SaaS handler'
assert emitter_adapter._emitter is not None, 'Dossier emitter not registered'
print('All registrations OK')
"

# 9. Fan-out preservation regression test:
#    Run a normal status transition with sync pre-imported and verify
#    SaaS fan-out actually fires. This catches the failure mode where
#    fire_* becomes a silent no-op because no handler was registered
#    in time.
uv run pytest tests/status/test_emit_fanout_after_adapter.py -v
```

**Note**: subtask T009 must include a new test file `tests/status/test_emit_fanout_after_adapter.py` (added to owned_files) that:
1. Imports `specify_cli.sync` first (simulating CLI bootstrap),
2. Calls `emit_status_transition(...)` for a normal lane move,
3. Asserts the SaaS fan-out handler was invoked with the expected kwargs (use `unittest.mock.patch` on `specify_cli.sync.events.emit_wp_status_changed` to capture the call without actually contacting SaaS),
4. Also runs the same transition WITHOUT having imported `specify_cli.sync` and asserts fan-out is a silent no-op (documents the bootstrap requirement).

This test guards against the regression where the registry pattern silently drops fan-out because registration never ran.

**Validation**:
- [ ] All ruff checks pass (0 violations)
- [ ] mypy --strict passes on `status/adapters.py`
- [ ] grep for `from specify_cli.sync` in status returns empty
- [ ] `tests/status` green
- [ ] `tests/sync` green
- [ ] Contract tests green (with SAAS_SYNC enabled)
- [ ] Architectural guard green
- [ ] Handler + emitter registration smoke test passes
- [ ] Fan-out preservation regression test (`tests/status/test_emit_fanout_after_adapter.py`) green

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

## Activity Log

- 2026-05-01T07:14:46Z – claude – shell_pid=90882 – WP02 complete: status/adapters.py + emit.py + sync/__init__.py registration + 2 architectural tests + fan-out preservation regression test. 537 status + 1456 sync tests pass.
- 2026-05-01T07:15:16Z – codex:gpt-4o:python-pedro:reviewer – shell_pid=79820 – Started review via action command
- 2026-05-01T07:21:31Z – codex:gpt-4o:python-pedro:reviewer – shell_pid=79820 – Review passed: status fan-out adapter removes status-to-sync imports, registration smoke and status/sync/contract/architectural checks pass

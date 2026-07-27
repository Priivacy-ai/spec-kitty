# Research: Enforce the Integration/Core Boundary

**Mission**: `integration-boundary-01KW0PBE`
**Date**: 2026-06-26
**Branch**: `feat/integration-boundary`

---

## 1. Mandatory Ambiguity Resolution #1 — Leak #3 Startup-Registration Ordering

### Finding

The startup hook that registers the dossier-sync, SaaS-fanout, and lifecycle-SaaS
handlers is `sync/__init__.py::register_default_handlers()`. It is called at
module-level (bottom of `sync/__init__.py`) when
`SPEC_KITTY_SYNC_MINIMAL_IMPORT != "1"`, and exposed as a public function so tests
that wipe the registry (via `adapters.reset_handlers()`) can repair it.

Exact call sites of `register_dossier_sync_handler`, `register_saas_fanout_handler`,
`register_lifecycle_saas_fanout_handler`:

```
src/specify_cli/sync/__init__.py:290–294   (inside register_default_handlers())
src/specify_cli/sync/__init__.py:292–294   (called at import time when MINIMAL_IMPORT != "1")
```

**Plan**: The new `invocation/adapters.py` registrations (`register_sync_routing_resolver`,
`register_saas_client_factory`) MUST be co-located in `register_default_handlers()` in
`sync/__init__.py`. The `sync` package import triggers both sets of registrations in a
single call, maintaining the existing "register everything at sync import time" invariant.

### Import-Order Risk: What If `invocation/` Imports Before `sync/`?

Risk: `invocation/propagator.py` is imported (e.g., by the CLI entrypoint) before
`sync/__init__.py` has been imported and `register_default_handlers()` has run.
In that case, `invocation/adapters.py` has an empty registry.

**Safe-degradation contract** (MUST be enforced by `invocation/adapters.py` design):

| Absent registration | Adapter return value | Propagator behaviour |
|---|---|---|
| No routing resolver registered | `None` | `routing is None` → sync-disabled check skipped → propagator continues (identical to current `resolve_checkout_sync_routing` returning `None` on no project root) |
| No client factory registered | `None` | `client is None` → propagator returns early, no event sent (existing fast-path) |

Both None-fallback paths already exist in the current `_propagate_one` and
`_get_saas_client` logic. The adapter layer is a pure substitution: if resolver
is absent, the behaviour is the same as `resolve_checkout_sync_routing` returning
`None`. No crash, no data loss.

The `invocation/adapters.py` module MUST NOT import from `sync/` at module scope
(that would reintroduce the cycle). The concrete resolver/factory implementations
live in `sync/__init__.py` as local lambdas/closures and are injected via
`register_sync_routing_resolver(lambda path: ...)`.

---

## 2. Mandatory Ambiguity Resolution #2 — `emit_mission_created` Collapse / External-Consumer Audit

### Caller Table

All callers of `emit_mission_created` (both definitions, repo-wide):

| Location | Symbol | Module | Import path | Verdict |
|----------|--------|--------|-------------|---------|
| `src/specify_cli/core/mission_creation.py:30` | `emit_mission_created` | `sync.events` | `from specify_cli.sync.events import emit_mission_created` | **REMOVE** (Leak #1 fix) |
| `src/specify_cli/core/mission_creation.py:525` | `emit_mission_created(...)` | `sync.events` (top-level import) | called via the removed import | **REMOVE** (call site eliminated with import) |
| `src/specify_cli/sync/events.py:369` | `get_emitter().emit_mission_created(...)` | `sync.emitter.EventEmitter` | method call within `events.py` facade | **KEEP** — this is the facade calling its backing implementation |
| `src/specify_cli/sync/emitter.py:1190` | `def emit_mission_created(...)` | `sync.emitter.EventEmitter` | method definition on class | **KEEP** — canonical class-level implementation |
| `tests/sync/test_emit_mission_created_includes_mission_id.py:10` | `emit_mission_created` | `sync.events` | `from specify_cli.sync.events import emit_mission_created` | **KEEP** — tests the events facade directly; remains valid after Leak #1 fix because `sync.events` is INTEGRATION (allowed to use itself) |
| `tests/sync/test_events.py` (multiple lines) | `emitter.emit_mission_created(...)` | `sync.emitter.EventEmitter` | via fixture | **KEEP** — tests sync-internal emitter |
| `tests/sync/test_sync_e2e_integration.py:498` | `emitter.emit_mission_created(...)` | `sync.emitter.EventEmitter` | via fixture | **KEEP** |
| `tests/status/test_producer_conformance.py:241` | `emitter.emit_mission_created` | `sync.emitter.EventEmitter` | via `_get_emitter()` fixture | **KEEP** |

**Collapse-safety verdict**: No caller outside `src/specify_cli/` or `tests/` imports
`emit_mission_created` from the sync namespace. The only caller INSIDE `src/` that
is being removed is `core/mission_creation.py:30`. After removal, the `sync.events`
facade and `sync.emitter.EventEmitter.emit_mission_created` method remain for use
within the sync package and tests — both are legitimate since they are INTEGRATION
callers of INTEGRATION code (not CORE).

**What "collapse" means for this mission**: The Leak #1 fix collapses the two
independent SaaS fan-out paths for MissionCreated into one:
- BEFORE: path A (direct `core/` → `sync.events.emit_mission_created` → emitter
  singleton → WebSocket + OfflineQueue) AND path B (`emit_mission_created_local` →
  `fire_lifecycle_saas_fanout` → `_lifecycle_saas_fanout_handler` → OfflineQueue)
- AFTER: single path B. Path A's call site is removed from `core/`.

`sync.events.emit_mission_created` is NOT deleted — it remains a valid public
function for sync-internal use and tests. The collapse is the removal of its import
in `core/`.

---

## 3. Mandatory Ambiguity Resolution #3 — `emit_mission_created_local` Idempotency / No Double-Write

### Event-Write Count: Before and After

**Write path (current)**:

```
core/mission_creation.py
  Step 8a: emit_mission_created_local(feature_dir, ...)      ← Write #1 to status.events.jsonl
             └── append_lifecycle_event(log_path, ...)
                   └── _atomic_append(log_path, ...)         ← 1 write (with dedup gate)
                   └── _queue_lifecycle_event_if_enabled(...)
                         └── fire_lifecycle_saas_fanout(...)
                               └── _lifecycle_saas_fanout_handler → OfflineQueue  ← separate queue, NOT status.events.jsonl

  Step 8b: emit_mission_created(...)                         ← NOT a write to status.events.jsonl
             └── get_emitter().emit_mission_created(...)     ← writes to emitter's OfflineQueue
             └── _publish_event_via_sync_daemon(...)         ← WebSocket send
             └── _request_dashboard_sync(...)                ← sync-daemon trigger
```

**Write path (after Leak #1 fix)**:

```
core/mission_creation.py
  Step 8a: emit_mission_created_local(feature_dir, ...)      ← Write #1 to status.events.jsonl (UNCHANGED)
             └── append_lifecycle_event(log_path, ...)
                   └── _atomic_append(log_path, ...)         ← 1 write (dedup gate prevents double-write)
                   └── _queue_lifecycle_event_if_enabled(...)
                         └── fire_lifecycle_saas_fanout(...)
                               └── _lifecycle_saas_fanout_handler → OfflineQueue + (optionally) daemon sync

  Step 8b: [REMOVED] — no second write, no second OfflineQueue enqueue from core
```

**status.events.jsonl write count**: 1 before → 1 after. No regression.

The `append_lifecycle_event` dedup gate (`has_lifecycle_event` on `mission_slug`) already
provides idempotency for repeated calls. The Leak #1 fix does NOT add a second call to
`emit_mission_created_local` — it only removes the out-of-band `emit_mission_created` call.

**OfflineQueue note**: The OfflineQueue is a separate persistence store (not
`status.events.jsonl`). The `_lifecycle_saas_fanout_handler` was ALREADY writing to it via
Step 8a's `fire_lifecycle_saas_fanout`. After the fix, Step 8b's separate OfflineQueue
write is eliminated — net result: one fewer OfflineQueue entry per mission creation for
the SaaS path. This is correct because the observer path handles it.

### Daemon/WebSocket Path Preservation

The current `sync.events.emit_mission_created` also calls `_publish_event_via_sync_daemon`
and `_request_dashboard_sync`. After removing Step 8b from `core/`, these calls are
missing. **Resolution**: WP03 (IC-05) extends `_lifecycle_saas_fanout_handler` in
`sync/__init__.py` to also invoke `_publish_event_via_sync_daemon` and
`_request_dashboard_sync` when the incoming envelope's `event_type == "MissionCreated"`.
This keeps the behaviour inside the registered observer, never inside core.

---

## 4. Required Caller-Audit — Deletion-Safety / #1622 Guard

### Symbols to REMOVE from `core/mission_creation.py`

| Line | Symbol/Import | Replacement in `core/mission_creation.py` |
|------|--------------|-------------------------------------------|
| 30 | `from specify_cli.sync.events import emit_mission_created` | Remove entirely. No replacement at import level. |
| ~525 | `emit_mission_created(mission_slug_formatted, ...)` | Remove call site. SaaS fan-out now handled by `fire_lifecycle_saas_fanout` (triggered within `emit_mission_created_local` already at line 468). |
| ~540 | `from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled` | Replace with `fire_dossier_sync(feature_dir, mission_slug_formatted, resolved_root)` using `from specify_cli.status.adapters import fire_dossier_sync` (CORE importing CORE — allowed). |
| 593 | `from specify_cli.tracker.origin import OriginBindingError, bind_mission_origin` | Remove. `_consume_pending_origin_if_present` body replaces with `consume_pending_origin(repo_root, feature_dir, meta)` from `core/adapters.py`. |
| 594 | `from specify_cli.tracker.origin_models import OriginCandidate` | Remove. |
| 595 | `from specify_cli.tracker.ticket_context import clear_pending_origin, read_pending_origin` | Remove. |

### `emit_mission_created` Collapse — Surviving Definition

| Definition | File | Survives? | Note |
|------------|------|-----------|------|
| `def emit_mission_created(...)` module-level | `sync/events.py:354` | YES — function kept as public API | No longer called from `core/`; remains for tests and any future sync-internal callers |
| `def emit_mission_created(...)` method | `sync/emitter.py:1190` (on `EventEmitter`) | YES — kept as class implementation | Called by `events.py` facade |

Neither definition is deleted. The "collapse" is the removal of the CORE call site (line 525 in `mission_creation.py`), not the deletion of either function.

### `invocation/propagator.py` Seams Being Inverted

| Line | Current import | Inverted to | Safe degradation |
|------|---------------|-------------|-----------------|
| 39 | `from specify_cli.sync.routing import resolve_checkout_sync_routing` | `from specify_cli.invocation.adapters import resolve_sync_routing` | Returns `None` → same as current `resolve_checkout_sync_routing` returning `None` → sync check skipped |
| 66 | `from specify_cli.sync.client import WebSocketClient` (lazy, inside `_get_saas_client`) | `from specify_cli.invocation.adapters import get_saas_client` | Returns `None` → `_get_saas_client` returns `None` → propagator no-ops |

**BLESSED direction untouched**: `core.contract_gate.validate_outbound_payload` and
`status.*` facade imports in `invocation/propagator.py` (lines 37–38) are CORE←INTEGRATION
direction (invocation importing core/status) and are **not** touched by this mission.

---

## 5. Startup Registration — Verified Hook Locations

### Existing registrations in `sync/__init__.py::register_default_handlers()`

```python
# src/specify_cli/sync/__init__.py  lines ~289–294
def register_default_handlers() -> None:
    with _contextlib.suppress(ImportError):
        from specify_cli.status import (
            register_dossier_sync_handler,
            register_lifecycle_saas_fanout_handler,
            register_saas_fanout_handler,
        )
        register_dossier_sync_handler(_dossier_sync_handler)
        register_saas_fanout_handler(_saas_fanout_handler)
        register_lifecycle_saas_fanout_handler(_lifecycle_saas_fanout_handler)
```

### New registrations to add in WP01 (Leak #3)

```python
# Extend register_default_handlers() — same file, same pattern
with _contextlib.suppress(ImportError):
    from specify_cli.invocation.adapters import (
        register_saas_client_factory,
        register_sync_routing_resolver,
    )
    from specify_cli.sync.routing import resolve_checkout_sync_routing
    from specify_cli.sync.client import WebSocketClient as _WSClient

    register_sync_routing_resolver(
        lambda path: (r := resolve_checkout_sync_routing(path)) and r.effective_sync_enabled or None
    )
    register_saas_client_factory(_build_saas_client_factory())
```

Note: the lambda avoids importing `sync.routing` at `invocation/` scope — the lambda
is defined in `sync/__init__.py` where the import is legal (INTEGRATION importing INTEGRATION).

### New registrations to add in WP03 (Leak #1 tracker)

```python
# tracker/__init__.py or tracker/startup.py — triggered when tracker package is imported
from specify_cli.core.adapters import register_pending_origin_consumer
from specify_cli.tracker.origin_consumer import consume_pending_origin_impl

register_pending_origin_consumer(consume_pending_origin_impl)
```

---

## 6. #1622 Dead-Symbol Guard

Issue #1622 tracks `coordination.status_service` dead-symbol debt. This mission does
NOT touch `coordination/` and does NOT add or remove any symbols that are part of the
#1622 debt set. No action required.

---

## 7. Architectural Test Pattern Reference

The enforcement test follows `tests/architectural/test_status_sync_boundary.py` exactly:

```python
def _collect_imports(package_path: Path) -> list[tuple[str, str]]:
    """Return (source_file, imported_module) for ALL imports via AST walk."""
    edges: list[tuple[str, str]] = []
    for py_file in sorted(package_path.rglob("*.py")):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):  # ast.walk catches lazy + TYPE_CHECKING imports
            if isinstance(node, ast.ImportFrom) and node.module:
                edges.append((str(py_file.relative_to(SRC)), node.module))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append((str(py_file.relative_to(SRC)), alias.name))
    return edges
```

`ast.walk` (not `ast.NodeVisitor`) is the critical choice: it visits ALL nodes
recursively, including nodes inside `if TYPE_CHECKING:` blocks and function bodies,
so no import form can hide from the scan. pytestarch is NOT used (FR-002).

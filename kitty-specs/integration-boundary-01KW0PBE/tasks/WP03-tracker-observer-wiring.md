---
work_package_id: WP03
title: tracker/origin_consumer.py + observer wiring + emit_mission_created collapse
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-006
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: feat/integration-boundary
merge_target_branch: feat/integration-boundary
branch_strategy: Planning artifacts for this mission were generated on feat/integration-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/integration-boundary unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 3 - tracker observer + sync wiring
assignee: ''
agent: ''
shell_pid: '1788780'
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
authoritative_surface: src/specify_cli/tracker/
create_intent:
- src/specify_cli/tracker/origin_consumer.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/__init__.py
- src/specify_cli/tracker/__init__.py
- src/specify_cli/tracker/origin_consumer.py
- tests/sync/**
- tests/tracker/**
tags: []
---

# Work Package Prompt: WP03 – tracker/origin_consumer.py + observer wiring + emit_mission_created collapse

## Objective

After WP02 removed the tracker/sync imports from `core/mission_creation.py`, those
responsibilities must move to the integration side and be registered as observers:

1. Create `src/specify_cli/tracker/origin_consumer.py` — the concrete
   `PendingOriginConsumer` implementation (logic extracted verbatim from the
   now-deleted `_consume_pending_origin_if_present` body).
2. Register it with `core/adapters.py` at tracker startup.
3. Wire the invocation adapter registrations (sync-routing resolver + SaaS-client
   factory) into `sync/__init__.py::register_default_handlers`, inside the existing
   `contextlib.suppress(ImportError)` guard.
4. Confirm the single surviving `emit_mission_created` path and close any
   MissionCreated daemon/WebSocket gap without re-introducing CORE→INTEGRATION
   imports.

After this WP all three leaks are fully inverted. WP04 can be introduced and will
pass green.

---

## Prerequisites

WP02 must be merged first: `core/adapters.py` must exist, and
`core/mission_creation.py` must already call `consume_pending_origin`.

---

## Subtasks

### T011 — Create `src/specify_cli/tracker/origin_consumer.py`

Extract the logic from the deleted `_consume_pending_origin_if_present` body in
`core/mission_creation.py` (WP02) verbatim into:

```python
# src/specify_cli/tracker/origin_consumer.py

from __future__ import annotations

from pathlib import Path
from typing import Any


def consume_pending_origin_impl(
    repo_root: Path,
    feature_dir: Path,
    meta: dict[str, Any],
) -> tuple[bool, bool, str | None, dict[str, Any]]:
    """Concrete PendingOriginConsumer implementation.

    Kept in tracker/ so tracker imports remain on the integration side.
    Registered with core/adapters.py at tracker startup.
    """
    from specify_cli.tracker.origin import OriginBindingError, bind_mission_origin
    from specify_cli.tracker.origin_models import OriginCandidate
    from specify_cli.tracker.ticket_context import clear_pending_origin, read_pending_origin
    # ... extracted logic identical to the former _consume_pending_origin_if_present ...
```

The return tuple `(attempted, succeeded, error_msg, updated_meta)` MUST match the
`PendingOriginConsumer` signature in `core/adapters.py` exactly. The
`MissionCreationResult.origin_binding_*` fields that `mission_create.py:317-320`
reads MUST remain fully populated.

Verify `consume_pending_origin_impl.__module__ + "." + consume_pending_origin_impl.__qualname__`
is a stable identifier suitable for idempotent registration.

### T012 — Register `consume_pending_origin_impl` in `tracker/__init__.py`

In `src/specify_cli/tracker/__init__.py` (or the first-imported tracker module that
runs at startup), add:

```python
from specify_cli.core.adapters import register_pending_origin_consumer
from specify_cli.tracker.origin_consumer import consume_pending_origin_impl

register_pending_origin_consumer(consume_pending_origin_impl)
```

**Startup ordering check**: verify that the CLI entrypoints for mission creation
(`cli/commands/` mission-create path) import `specify_cli.tracker` before
`specify_cli.core.mission_creation` is called, so the consumer is registered before
it is first invoked. If not, add an explicit import in the CLI command module that
performs mission creation.

### T013 — Add invocation adapter registrations to `sync/__init__.py::register_default_handlers`

In `src/specify_cli/sync/__init__.py`, inside `register_default_handlers()` at
approximately lines 290–294, within the **existing** `contextlib.suppress(ImportError)`
guard (do not widen or remove the guard), add:

```python
from specify_cli.invocation.adapters import (
    register_sync_routing_resolver,
    register_saas_client_factory,
)
from specify_cli.sync.routing import resolve_checkout_sync_routing
from specify_cli.sync.client import WebSocketClient

register_sync_routing_resolver(
    lambda path: resolve_checkout_sync_routing(path).effective_sync_enabled
)
register_saas_client_factory(lambda path: WebSocketClient(path))
```

These imports are INTEGRATION→INTEGRATION (sync imports from invocation/adapters.py
is INTEGRATION→CORE, which is the allowed direction) — no boundary violation.

### T014 — Confirm single MissionCreated SaaS fan-out path; close daemon/WebSocket gap if needed

Trace the `emit_mission_created_local` code path in `status/lifecycle_events.py`:

1. Confirm it calls `append_lifecycle_event`.
2. Confirm `append_lifecycle_event` calls `fire_lifecycle_saas_fanout`.
3. Confirm `_lifecycle_saas_fanout_handler` in `sync/__init__.py` is registered
   and handles MissionCreated envelopes.

If the daemon/WebSocket push (`_publish_event_via_sync_daemon` /
`_request_dashboard_sync`) is NOT already triggered for MissionCreated envelopes
inside `_lifecycle_saas_fanout_handler`, extend it to handle those envelopes —
**inside the registered observer only**, zero direct INTEGRATION imports added to any
CORE module.

The two `emit_mission_created` implementations in `sync/events.py` (line 354) and
`sync/emitter.py` (line 1190) were duplicates; now that the CORE call-site is gone
(WP02), confirm by `git grep` that neither is imported from any CORE module. If one
is still used internally within the sync package, that is permitted. Document the
surviving path in an inline comment in `sync/__init__.py`.

**FR-005 collapse constraint**: the `emit_mission_created` name in `sync/` is now
integration-internal only. Confirm with:
```bash
git grep -n "emit_mission_created" src/specify_cli/core/ src/specify_cli/status/ \
  src/specify_cli/readiness/ src/specify_cli/invocation/
```
This MUST return zero results after WP02+WP03.

### T015 — Targeted regression tests (NFR-004)

Write or extend tests to prove all three projections still fire after the inversion:

1. **Dossier sync** (`tests/sync/` or `tests/core/`): mock `fire_dossier_sync`; call
   the mission-creation path; assert mock was called with the correct arguments.
2. **SaaS fan-out** (`tests/sync/` or `tests/status/`): mock
   `fire_lifecycle_saas_fanout`; call `emit_mission_created_local`; assert mock was
   called.
3. **Origin binding** (`tests/tracker/` or `tests/core/`): register a mock
   `PendingOriginConsumer` with `core/adapters.py`; call `consume_pending_origin`;
   assert the mock was called and the return tuple is propagated correctly to
   `MissionCreationResult.origin_binding_*`.

Tests must call `reset_origin_consumer()` / `reset_adapters()` in teardown.

---

## Acceptance Criteria

1. `src/specify_cli/tracker/origin_consumer.py` exists with `consume_pending_origin_impl`.
2. `src/specify_cli/tracker/__init__.py` registers `consume_pending_origin_impl` with
   `core/adapters.py`.
3. `sync/__init__.py::register_default_handlers` registers the routing resolver and
   SaaS-client factory with `invocation/adapters.py`.
4. `git grep -n "emit_mission_created" src/specify_cli/core/ src/specify_cli/status/ src/specify_cli/readiness/ src/specify_cli/invocation/`
   returns zero results.
5. `MissionCreationResult.origin_binding_*` fields are still populated for a mission
   with a pending origin.
6. `pytest tests/sync/ tests/tracker/ tests/core/` is green at pre-mission parity.
7. `ruff check` and `mypy` report zero new issues on changed files.
8. `pytest tests/` exits at pre-mission parity — no newly failing tests (NFR-003).

---
work_package_id: WP02
title: core/adapters.py + Leak
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-006
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: feat/integration-boundary
merge_target_branch: feat/integration-boundary
branch_strategy: Planning artifacts for this mission were generated on feat/integration-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/integration-boundary unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - core adapter registry + Leak 1
assignee: ''
agent: ''
shell_pid: '1500369'
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
authoritative_surface: src/specify_cli/core/
create_intent:
- src/specify_cli/core/adapters.py
- tests/core/test_adapters.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/__init__.py
- src/specify_cli/core/adapters.py
- src/specify_cli/core/mission_creation.py
- tests/core/**
- tests/status/**
tags: []
---

# Work Package Prompt: WP02 – core/adapters.py + Leak #1 fix in mission_creation.py

## Objective

Create `src/specify_cli/core/adapters.py` — a result-bearing pending-origin
consumer registry — and remove all three INTEGRATION import edges from
`src/specify_cli/core/mission_creation.py` that constitute **Leak #1**.

After this WP `core/mission_creation.py` imports nothing from the INTEGRATION set.
The single `status.events.jsonl` write invariant is preserved. The SaaS fan-out
path is untouched.

---

## Prerequisites

WP01 must be merged first: `invocation/adapters.py` must exist before any test run
verifying the propagator fix.

---

## Context — the three import edges to remove

| Location | Current import | Replacement |
|----------|---------------|-------------|
| Line 30 (module-level) | `from specify_cli.sync.events import emit_mission_created` | Remove; `emit_mission_created_local` already fires `fire_lifecycle_saas_fanout` |
| ~Line 525 (call site) | `emit_mission_created(...)` call | Remove (the local path fires SaaS fan-out automatically) |
| ~Line 540 (lazy) | `from specify_cli.sync.dossier_pipeline import ...` | Replace with `fire_dossier_sync(...)` from `status/adapters.py` |
| Lines 593–595 (lazy) | `from specify_cli.tracker.origin import ...` + `tracker.origin_models` + `tracker.ticket_context` | Replace body with `consume_pending_origin(...)` from `core/adapters.py` |

**Single-write invariant**: `emit_mission_created_local` (in `status/lifecycle_events.py:533`)
is the ONLY writer to `status.events.jsonl` for the MissionCreated event. Removing
the `emit_mission_created(...)` call does NOT add a second write — it removes a
duplicate that was previously bypassing the local path. The local path already calls
`fire_lifecycle_saas_fanout` internally.

---

## Subtasks

### T005 — Create `src/specify_cli/core/adapters.py`

Create a result-bearing pending-origin consumer registry (FR-004, FR-006):

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

PendingOriginConsumer = Callable[
    [Path, Path, dict[str, Any]],
    tuple[bool, bool, str | None, dict[str, Any]],
]
# Signature: (repo_root, feature_dir, meta) -> (attempted, succeeded, error_msg, updated_meta)

_origin_consumer: PendingOriginConsumer | None = None


def register_pending_origin_consumer(fn: PendingOriginConsumer) -> None:
    """Register the implementation. Idempotent by qualified name."""
    ...


def consume_pending_origin(
    repo_root: Path,
    feature_dir: Path,
    meta: dict[str, Any],
) -> tuple[bool, bool, str | None, dict[str, Any]]:
    """Dispatch to the registered consumer.
    Returns (False, False, None, meta) when no consumer is registered (safe default).
    Catches all exceptions; returns (True, False, str(exc), meta) on failure.
    """
    ...


def reset_origin_consumer() -> None:
    """Test-only: reset the registry to its initial state."""
    ...
```

Invariants:
- Non-raising: consumer exceptions are caught; error message is returned in the
  third tuple element.
- Idempotent: re-registration of the same qualified name replaces the existing entry.
- No imports from the INTEGRATION set.
- No third-party imports.

### T006 — Re-export from `core/__init__.py`

Add public re-exports of `PendingOriginConsumer`, `register_pending_origin_consumer`,
`consume_pending_origin`, and `reset_origin_consumer` to
`src/specify_cli/core/__init__.py` so that callers can use the package-level import
surface.

### T007 — Remove module-level `emit_mission_created` import and call site

Edit `src/specify_cli/core/mission_creation.py`:

1. **Delete line 30**: `from specify_cli.sync.events import emit_mission_created`.
2. Find and **delete the `emit_mission_created(...)` call** (~line 525 — the direct
   SaaS call that bypassed the local path). The `emit_mission_created_local` call
   that precedes it already fires `fire_lifecycle_saas_fanout`; no replacement
   needed.

Verify: after this edit, the only MissionCreated lifecycle-event writer is
`emit_mission_created_local`. Run the existing `tests/status/` suite to confirm
the single-write count does not change.

### T008 — Remove lazy `sync.dossier_pipeline` import; use `fire_dossier_sync`

Edit `src/specify_cli/core/mission_creation.py`:

1. **Find the lazy import block** at approximately line 540:
   `from specify_cli.sync.dossier_pipeline import ...`
2. **Delete the lazy import**.
3. Replace the dossier-pipeline call with:
   ```python
   from specify_cli.status.adapters import fire_dossier_sync
   fire_dossier_sync(feature_dir, mission_slug, repo_root)
   ```
   (`fire_dossier_sync` is already registered by `sync/__init__.py` for WP status
   transitions; it behaves identically for mission creation.)

### T009 — Remove lazy tracker imports; use `consume_pending_origin`

Edit `src/specify_cli/core/mission_creation.py`:

1. **Find the lazy import block** at lines 593–595:
   ```python
   from specify_cli.tracker.origin import ...
   from specify_cli.tracker.origin_models import ...
   from specify_cli.tracker.ticket_context import ...
   ```
2. **Delete all three lazy imports**.
3. Replace the body of `_consume_pending_origin_if_present` with:
   ```python
   from specify_cli.core.adapters import consume_pending_origin
   return consume_pending_origin(repo_root, feature_dir, meta)
   ```
4. Verify that `MissionCreationResult.origin_binding_attempted`,
   `origin_binding_succeeded`, `origin_binding_error_msg`, and
   `origin_binding_meta` are all still populated from the return tuple at the
   call site (`mission_create.py:317-320`). The `PendingOriginConsumer` return
   signature `(bool, bool, str | None, dict)` maps 1-to-1 to those fields.

After T007–T009:
`git grep -n "specify_cli.sync\|specify_cli.tracker\|specify_cli.saas\|specify_cli.orchestrator_api\|specify_cli.saas_client" src/specify_cli/core/mission_creation.py`
MUST return zero results.

### T010 — Unit tests for `core/adapters.py`

Write `tests/core/test_adapters.py` (new file) covering:
- `consume_pending_origin(...)` returns `(False, False, None, meta)` when no
  consumer is registered (safe default, non-mutating).
- After `register_pending_origin_consumer(fn)`, `consume_pending_origin(...)` calls
  `fn` with `(repo_root, feature_dir, meta)` and returns its result.
- If the registered consumer raises an exception, `consume_pending_origin` catches it
  and returns `(True, False, str(exc), meta)` (non-raising contract).
- Re-registering the same qualified name replaces the existing entry.
- Call `reset_origin_consumer()` in teardown to avoid state bleed.

---

## Acceptance Criteria

1. `src/specify_cli/core/adapters.py` exists and imports nothing from the
   INTEGRATION set.
2. `git grep "specify_cli.sync\|specify_cli.tracker\|specify_cli.saas" src/specify_cli/core/mission_creation.py`
   returns zero results.
3. `pytest tests/core/test_adapters.py` is green.
4. Existing `tests/status/` and `tests/core/` suites are green at pre-mission parity.
5. `ruff check` and `mypy` report zero new issues on changed files.
6. `pytest tests/` exits at pre-mission parity — no newly failing tests (NFR-003).

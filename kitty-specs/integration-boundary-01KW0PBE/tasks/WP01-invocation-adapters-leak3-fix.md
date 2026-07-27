---
work_package_id: WP01
title: invocation/adapters.py + Leak
dependencies: []
requirement_refs:
- FR-008
- C-007
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: feat/integration-boundary
merge_target_branch: feat/integration-boundary
branch_strategy: Planning artifacts for this mission were generated on feat/integration-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/integration-boundary unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-integration-boundary-01KW0PBE
base_commit: 48e61e1fd0cc34e05799df3d5e730a8fea1c4aed
created_at: '2026-06-26T01:26:43.651208+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - invocation adapter registry + Leak 3
assignee: ''
agent: ''
shell_pid: '1035054'
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
authoritative_surface: src/specify_cli/invocation/
create_intent:
- src/specify_cli/invocation/adapters.py
- tests/invocation/__init__.py
- tests/invocation/test_adapters.py
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/__init__.py
- src/specify_cli/invocation/adapters.py
- src/specify_cli/invocation/propagator.py
- tests/invocation/**
tags: []
---

# Work Package Prompt: WP01 – invocation/adapters.py + Leak #3 fix in propagator.py

## Objective

Create `src/specify_cli/invocation/adapters.py` — a sync-routing resolver and
SaaS-client factory registry that mirrors the `status/adapters.py` idiom — and
immediately remove the two INTEGRATION import edges from
`src/specify_cli/invocation/propagator.py` that constitute **Leak #3**.

This WP is the chain root. All subsequent WPs depend on it because
`invocation/adapters.py` must exist before the propagator is cleaned up, and the
propagator must be clean before the enforcement test (WP04) can pass.

---

## Context

`src/specify_cli/invocation/propagator.py` currently has two INTEGRATION leaks:
- **Line 39** (module-level): `from specify_cli.sync.routing import resolve_checkout_sync_routing`
- **Line 66** (lazy function-body): `from specify_cli.sync.client import WebSocketClient`

After this WP those two import edges are gone. `propagator.py` calls
`resolve_sync_routing(path)` and `get_saas_client(path)` from
`invocation/adapters.py` instead; both return `None` safely when no concrete
implementation is registered (safe-degrade guarantee).

The sync package registers concrete implementations in
`sync/__init__.py::register_default_handlers` — that registration is also wired
in this WP (T004).

---

## Subtasks

### T001 — Create `src/specify_cli/invocation/adapters.py`

Follow the `status/adapters.py` idiom **exactly** (FR-008, C-007). The module MUST:

- Define a `_sync_routing_resolver: Callable[[Path], bool | None] | None` module
  variable (initially `None`).
- Define a `_saas_client_factory: Callable[[Path], Any | None] | None` module
  variable (initially `None`).
- Expose `register_sync_routing_resolver(fn: Callable[[Path], bool | None]) -> None`:
  idempotent by qualified name (`fn.__module__ + "." + fn.__qualname__`);
  replaces an existing entry of the same qualified name; non-raising.
- Expose `register_saas_client_factory(fn: Callable[[Path], Any | None]) -> None`:
  same idempotency contract.
- Expose `resolve_sync_routing(path: Path) -> bool | None`: dispatches to the
  registered resolver; returns `None` if no resolver is registered; catches all
  exceptions and returns `None` on error (non-raising).
- Expose `get_saas_client(path: Path) -> Any | None`: dispatches to the registered
  factory; returns `None` if no factory is registered; catches all exceptions and
  returns `None` on error.
- Expose `reset_adapters() -> None`: **test-only** helper that sets both module
  variables back to `None`. Call only from test teardown.
- Import NOTHING from the INTEGRATION set (`orchestrator_api`, `sync`, `tracker`,
  `saas`, `saas_client`). Standard library and `pathlib.Path` only.
- No third-party library imports (C-007).

Verify zero new `ruff` and `mypy` issues on the new file.

### T002 — Re-export from `invocation/__init__.py`

Add public re-exports of the four dispatch functions
(`register_sync_routing_resolver`, `register_saas_client_factory`,
`resolve_sync_routing`, `get_saas_client`) and `reset_adapters` to
`src/specify_cli/invocation/__init__.py` so that callers can use the package-level
import surface.

### T003 — Remove INTEGRATION imports from `propagator.py` and route through `invocation/adapters.py`

Edit `src/specify_cli/invocation/propagator.py`:

1. **Remove line 39**: delete `from specify_cli.sync.routing import resolve_checkout_sync_routing`.
2. Add `from specify_cli.invocation.adapters import resolve_sync_routing, get_saas_client`
   at the module level (this import is within the CORE set — permitted).
3. **Remove the lazy import block at line 66** (`from specify_cli.sync.client import WebSocketClient`)
   inside whichever function body it lives in.
4. Replace both former usages:
   - Where `resolve_checkout_sync_routing(path)` was called, call
     `resolve_sync_routing(path)` instead. Note the return type is now `bool | None`
     (not `CheckoutSyncRouting | None`); the propagator only needs the
     `effective_sync_enabled` flag. Adjust any type annotations accordingly.
   - Where `WebSocketClient(...)` was instantiated, call `get_saas_client(path)`
     instead and handle the `None` case (propagator already has a None-check
     pattern from the routing resolver; follow the same pattern).

After this edit, `git grep -n "specify_cli.sync\|specify_cli.tracker\|specify_cli.saas\|specify_cli.orchestrator_api\|specify_cli.saas_client" src/specify_cli/invocation/propagator.py`
MUST return zero results.

### T004 — Register concrete implementations in `sync/__init__.py` + unit tests

1. **In `sync/__init__.py::register_default_handlers`** (at approximately lines
   290–294, inside the existing `contextlib.suppress(ImportError)` guard), add:
   ```python
   from specify_cli.invocation.adapters import (
       register_sync_routing_resolver,
       register_saas_client_factory,
   )
   register_sync_routing_resolver(
       lambda path: resolve_checkout_sync_routing(path).effective_sync_enabled
   )
   register_saas_client_factory(lambda path: WebSocketClient(path))
   ```
   The lambda captures `resolve_checkout_sync_routing` (from `sync.routing`) and
   `WebSocketClient` (from `sync.client`). These imports stay INSIDE the sync
   package — no CORE module imports from INTEGRATION.

2. **Write unit tests** in `tests/invocation/test_adapters.py` (new file) covering:
   - `resolve_sync_routing(path)` returns `None` when no resolver is registered.
   - `get_saas_client(path)` returns `None` when no factory is registered.
   - After `register_sync_routing_resolver(fn)`, `resolve_sync_routing(path)` calls
     `fn` with the path and returns its result.
   - After `register_saas_client_factory(fn)`, `get_saas_client(path)` calls `fn`
     with the path and returns its result.
   - Re-registering the same qualified name replaces the old entry (idempotency).
   - An exception raised by a registered handler is caught; the dispatch function
     returns `None`.
   - Call `reset_adapters()` in teardown to avoid state bleed between tests.

   Tests carry `pytest.mark.unit` if that marker is in use in the `tests/invocation/`
   suite; otherwise follow the existing marker convention.

---

## Acceptance Criteria

1. `src/specify_cli/invocation/adapters.py` exists and contains no imports from the
   INTEGRATION set.
2. `git grep "specify_cli.sync\|specify_cli.tracker\|specify_cli.saas" src/specify_cli/invocation/propagator.py`
   returns zero results.
3. `sync/__init__.py::register_default_handlers` registers both the routing resolver
   and the SaaS-client factory with `invocation/adapters.py`.
4. `pytest tests/invocation/test_adapters.py` is green.
5. `ruff check src/specify_cli/invocation/adapters.py src/specify_cli/invocation/propagator.py`
   and `mypy src/specify_cli/invocation/adapters.py` report zero issues.
6. `pytest tests/` exits at pre-mission parity — no newly failing tests (NFR-003).

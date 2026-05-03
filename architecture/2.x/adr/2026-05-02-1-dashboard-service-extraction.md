# ADR: Dashboard Service Extraction

**Date**: 2026-05-02
**Status**: Accepted
**Mission**: `dashboard-service-extraction-01KQMCA6`

## Context

The Spec Kitty dashboard handler layer (`src/specify_cli/dashboard/handlers/`) currently
embeds all business logic — mission scanning, kanban assembly, health status, sync
orchestration — directly inside HTTP request handlers. This coupling makes the logic
untestable in isolation and impossible to migrate to a modern transport framework
(FastAPI/OpenAPI, tracked as a sequenced follow-up mission).

The connascence analysis in
`kitty-specs/dashboard-service-extraction-01KQMCA6/research.md` identifies three
high-strength dynamic connascence clusters in the handler layer that exceed the
extraction threshold:

- **`handle_features_list` / `handle_kanban`** — execution-order coupling across
  scanner, legacy detector, and status subsystems. The methods construct complex
  response shapes by interleaving scanner calls with status state reads; no stable
  interface separates the data access from the HTTP response assembly.
- **`handle_sync_trigger`** — three-step orchestration mixing HTTP response concerns
  with daemon state: token validation, localhost-only invariant enforcement, and
  daemon request dispatch all live in the same method.
- **`handle_health`** — the health response shape depends on both path resolution and
  daemon status, with the assembly logic coupled tightly to HTTP response construction.

The dashboard is also absent from the functional ownership map, creating a governance
gap relative to the extraction pattern established by `src/charter/` and `src/doctrine/`.

## Decision

Extract dashboard business logic into a new canonical top-level package `src/dashboard/`,
following the strangler-fig extraction pattern established by `src/charter/` and
`src/doctrine/`. Three service objects are introduced:

- `MissionScanService` (`src/dashboard/services/mission_scan.py`) — features list with
  active mission resolution, kanban with weighted lane progress
- `ProjectStateService` (`src/dashboard/services/project_state.py`) — health response
  assembly (project path, sync daemon status)
- `SyncService` (`src/dashboard/services/sync.py`) — sync daemon orchestration
  (localhost-only invariant, daemon startup/trigger)

A file I/O utility `DashboardFileReader` (`src/dashboard/file_reader.py`) consolidates
repeated path-traversal-safe read logic from the file-serving handler methods.

`api_types.py` moves from `src/specify_cli/dashboard/api_types.py` to
`src/dashboard/api_types.py`. A backward-compat shim is installed at the old path:

```python
# src/specify_cli/dashboard/api_types.py (shim)
from dashboard.api_types import *  # noqa: F401, F403
__removal_release__ = "FastAPI transport migration milestone"
```

The handler layer in `src/specify_cli/dashboard/handlers/` becomes a thin delegation
adapter. Each extracted handler method contains only HTTP dispatch and a single call
to the corresponding service object.

## Rationale

- Resolves high-strength dynamic connascence (execution-order coupling) by giving each
  responsibility cluster a stable, testable interface
- Enables isolated unit testing of dashboard business logic without an HTTP server
- Unblocks the FastAPI transport migration (sequenced follow-up, not in scope here)
- Follows the extraction pattern from charter and doctrine extractions
- Registers the dashboard as a first-class governance slice in the ownership map
- `api_types.py` relocation to `src/dashboard/` prevents the circular import that
  would arise if service objects imported their own response types from `specify_cli`

## Consequences

- **Cross-layer imports**: `src/dashboard/` imports from `specify_cli.scanner`,
  `specify_cli.status`, `specify_cli.sync.daemon` — these are intentional cross-layer
  dependencies on subsystems not yet extracted. Full "no `specify_cli` imports"
  isolation requires scanner (#613) and status (#614) extraction missions as
  prerequisites.
- **Boundary test scope**: The architectural boundary test (`test_dashboard_boundary.py`)
  asserts the narrower practical invariant: no imports from `src/specify_cli/dashboard/`
  inside `src/dashboard/`. This prevents the circular dependency between the service
  layer and its own adapter without requiring the scanner/status extractions.
- **`DashboardRouter` unchanged**: The multiple-inheritance dispatch chain in `router.py`
  is not modified; only the handler method bodies are thinned.
- **Shim lifespan**: The `src/specify_cli/dashboard/api_types.py` shim remains until the
  FastAPI transport migration milestone removes the `specify_cli` transport layer entirely.
- **Auxiliary scanner shim**: `src/specify_cli/scanner.py` was added during this mission
  as a re-export shim that gives `src/dashboard/` an FR-010-compatible import path for
  scanner utilities (the canonical implementations remain in `specify_cli.dashboard.scanner`
  until the scanner extraction mission #613). Its ownership, removal trigger, and audit
  trail are documented separately at
  [`kitty-specs/dashboard-service-extraction-01KQMCA6/scanner-shim-ownership-addendum.md`](../../kitty-specs/dashboard-service-extraction-01KQMCA6/scanner-shim-ownership-addendum.md).
  Removal trigger: scanner extraction mission #613 completion.

## Rejected Alternatives

- **One monolithic `DashboardService`**: rejected — `MissionScanService` and `SyncService`
  have entirely different dependency sets (scanner+status vs. sync daemon). Bundling them
  inflates constructor coupling without any cohesion benefit (research.md §2).
- **One service object per handler class**: rejected — `FeatureHandler` contains two
  responsibility clusters (mission scan and file I/O). File-serving routes have no
  business logic above the extraction threshold and stay in the adapter layer (C-006).
- **Keep `api_types.py` in `src/specify_cli/dashboard/`**: rejected — service objects
  must import their response types, and importing from `specify_cli.dashboard` would
  create a circular dependency between the service layer and the CLI adapter.
- **Big-bang extraction (all routes at once)**: rejected — the strangler-fig pattern
  (per-route extraction with test verification at each step) keeps the test suite green
  throughout and minimises blast radius per PROJECT_003.

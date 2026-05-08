# Feature Specification: Dashboard Service Extraction

*Path: [kitty-specs/dashboard-service-extraction-01KQMCA6/spec.md](spec.md)*

**Mission ID**: 01KQMCA6PM8QZTQ3ZJ0RZPX708
**Created**: 2026-05-02
**Status**: Draft
**Target Branch**: feature/650-dashboard-ui-ux-overhaul

## Overview

The Spec Kitty dashboard handler layer currently embeds all business logic — mission scanning,
work-package state reads, charter path resolution, glossary queries, diagnostics — directly
inside HTTP request handler methods. This coupling makes the business logic untestable in
isolation, impossible to migrate to a modern transport framework, and absent from the
project's functional ownership map.

This mission extracts that logic into a new canonical top-level package `src/dashboard/`,
following the same strangler-fig extraction pattern established for `src/charter/` and
`src/doctrine/`. The handler layer becomes a thin delegation adapter. The dashboard is
registered as a first-class slice in the functional ownership map. The existing `dashboard.js`
frontend is adapted to consume the stabilised, typed endpoint contracts exposed by the
new service layer.

FastAPI/OpenAPI transport migration is explicitly out of scope and tracked as a sequenced
follow-up mission.

## Domain Language

| Term | Definition | Avoid |
|---|---|---|
| **Service layer** | The canonical `src/dashboard/` package; contains all business logic, query functions, and typed response assembly | "business logic layer", "backend" |
| **CLI adapter** | `src/specify_cli/dashboard/handlers/`; contains only HTTP dispatch and delegation to the service layer | "handler", "controller" |
| **Shim** | A re-export wrapper in `src/specify_cli/dashboard/` that routes callers to the canonical `src/dashboard/` package; carries a `removal_release` annotation | "alias", "proxy" |
| **Seam** | The explicit, testable crossing point between the CLI adapter and the service layer; each route has exactly one seam | "interface", "boundary" |
| **Extraction** | Moving canonical logic from `specify_cli` to a top-level package without changing observable behavior | "refactoring" (too vague), "migration" |
| **Ownership map** | `architecture/2.x/05_ownership_map.md` + `05_ownership_manifest.yaml`; the authoritative record of which package owns each functional slice | "architecture doc", "manifest" |
| **Endpoint contract** | The externally observable URL, HTTP method, response shape, and field names of a dashboard route; defined by `api_types.py` TypedDicts | "API schema", "response format" |

## User Scenarios & Testing

### User Story 1 — Operator using the dashboard without behavioral change (Priority: P0)

As a Spec Kitty operator, I want the dashboard to continue showing the same mission status,
work-package lanes, charter context, glossary, and diagnostics information after this
extraction, so that my workflow is not disrupted by the architectural restructuring.

**Acceptance scenarios:**

1. **Given** the dashboard is running after the extraction, **when** I open the mission
   overview panel, **then** all work packages appear with the correct lane status and
   weighted progress percentage — identical to pre-extraction behavior.
2. **Given** the dashboard is running, **when** I navigate to the glossary or diagnostics
   panel, **then** the content loads correctly with no regression in the displayed data.
3. **Given** `dashboard.js` is loaded against the stabilised endpoint contracts,
   **when** any panel makes an HTTP request, **then** the response shape and field names
   are identical to the pre-extraction response — no field renames, no structure changes.

### User Story 2 — Future developer consuming the service layer (Priority: P1)

As a developer working on the FastAPI follow-up mission, I want `src/dashboard/` to be
importable as a standalone Python package with no HTTP server dependency, so that I can
mount the service layer behind any transport framework without carrying the legacy server
along.

**Acceptance scenarios:**

1. **Given** `src/dashboard/` is installed in a fresh Python environment that does not
   include the HTTP server bootstrap code, **when** I import the dashboard service objects,
   **then** the import succeeds and the service layer is callable.
2. **Given** an architectural test that asserts `src/dashboard/` contains no imports from
   `src/specify_cli/dashboard/`, **when** the test suite runs, **then** the assertion passes
   with zero violations. (The broader `src/specify_cli/` exclusion requires scanner, status,
   and sync subsystems to be extracted first — a sequenced follow-up, not in scope here.)

### User Story 3 — Reviewer validating the ownership map entry (Priority: P1)

As a reviewer following the ownership map governance procedure, I want the dashboard slice
entry in `05_ownership_map.md` to specify the canonical package, adapter responsibilities,
shims, seams, and extraction sequencing notes, so that future extraction PRs can be
reviewed against a consistent, machine-readable standard.

**Acceptance scenarios:**

1. **Given** the ownership map is updated, **when** I apply the Audience B reviewer
   procedure from the map's usage guide to this extraction PR, **then** every mandatory
   field in the dashboard slice entry is verifiable — no field is absent or deferred.
2. **Given** the updated `05_ownership_manifest.yaml`, **when** the manifest-driven
   CI tooling parses it, **then** the `dashboard` key is present and valid.

### Edge cases

- Routes that perform file I/O (static asset serving, template rendering) remain in the
  CLI adapter; only business logic moves to the service layer.
- If a handler method performs both dispatch and a non-trivial computation, the computation
  must be extractable independently before the handler is thinned.
- The seam test for each route must remain green through every incremental extraction step,
  not only at the end.

## Functional Requirements

| ID | Description | Status |
|---|---|---|
| FR-001 | A `dashboard` slice entry is added to `architecture/2.x/05_ownership_map.md` following the Audience A procedure: specifying `canonical_package`, `adapter_responsibilities`, `shims`, `seams`, and `extraction_sequencing_notes` | Proposed |
| FR-002 | A corresponding `dashboard` key is added to `architecture/2.x/05_ownership_manifest.yaml` with machine-readable equivalents of all ownership map fields | Proposed |
| FR-003 | An Architectural Decision Record is drafted in `architecture/2.x/adr/` documenting the context, decision to extract `src/dashboard/`, rationale, consequences, and rejected alternatives; cross-linked from the ownership map entry | Proposed |
| FR-004 | A new top-level `src/dashboard/` package is created as the canonical home for all dashboard business logic | Proposed |
| FR-005 | All inline query, scan, and read logic currently embedded in `src/specify_cli/dashboard/handlers/features.py` and `src/specify_cli/dashboard/handlers/api.py` is moved to service objects inside `src/dashboard/` | Proposed |
| FR-006 | `src/dashboard/` exposes typed response objects that are compatible with the existing `api_types.py` TypedDict shapes — no shape or field name changes | Proposed |
| FR-007 | `src/specify_cli/dashboard/handlers/features.py` and `src/specify_cli/dashboard/handlers/api.py` are reduced to thin delegation adapters; each handler method contains only dispatch and a single call to a `src/dashboard/` service object | Proposed |
| FR-008 | Shim re-export files are added to `src/specify_cli/dashboard/` for any symbols that callers outside the handler layer import directly; each shim carries a `removal_release` annotation targeting the FastAPI migration milestone | Proposed |
| FR-009 | A seam test exists for each extracted route, verifying that the CLI adapter delegates correctly to the service layer and that the service layer returns the expected typed response | Proposed |
| FR-010 | An architectural boundary test in `tests/architectural/` asserts that no module inside `src/dashboard/` imports from `src/specify_cli/dashboard/` (the circular-import boundary for this mission; the broader `src/specify_cli/` exclusion is a sequenced follow-up requiring scanner/status/sync extraction) | Proposed |
| FR-011 | All existing dashboard tests continue to pass without modification after the extraction — zero behavioral regressions | Proposed |
| FR-012 | `dashboard.js` is updated so that all fetch calls and response-field references remain aligned with the stabilised endpoint contracts; no new fields are introduced or removed from the frontend perspective | Proposed |
| FR-013 | The `architecture/2.x/05_ownership_map.md` Audience B review checklist is applied to the extraction PR and every mandatory field is ticked off in the PR description | Proposed |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|---|---|---|---|
| NFR-001 | Dashboard startup time | `spec-kitty dashboard` startup time does not regress by more than 5 % compared to the pre-extraction baseline on the same machine | Proposed |
| NFR-002 | External dependency count | No new Python packages are added to `pyproject.toml` as a result of this extraction | Proposed |
| NFR-003 | Service layer import independence | `src/dashboard/` is importable in a Python environment that does not contain the HTTP server bootstrap code | Proposed |
| NFR-004 | Test suite execution time | Total test suite wall-clock time does not increase by more than 10 % after the new seam and architectural tests are added | Proposed |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | FastAPI/OpenAPI transport migration is out of scope; the HTTP server remains `BaseHTTPServer`-based after this mission | Confirmed |
| C-002 | The `api_types.py` TypedDict shapes are the authoritative endpoint contracts; no shape or field name changes are permitted | Confirmed |
| C-003 | `dashboard.js` behavior must be unchanged from the operator's perspective; no new UI features, no visible behavior changes | Confirmed |
| C-004 | The extraction must follow the Audience A procedure in `architecture/2.x/05_ownership_map.md` | Confirmed |
| C-005 | `src/specify_cli/` remains the CLI entrypoint; the `spec-kitty dashboard` command surface is unchanged | Confirmed |
| C-006 | Static asset serving (`handlers/static.py`), HTTP server bootstrap (`server.py`, `lifecycle.py`), and router dispatch (`router.py`) remain in `src/specify_cli/dashboard/`; only business logic moves | Confirmed |

## Key Entities

| Entity | Description |
|---|---|
| `src/dashboard/` | New canonical top-level package; owns all dashboard business logic and typed response assembly |
| `MissionScanService` | Service object in `src/dashboard/services/mission_scan.py`; exposes `get_features_list()` and `get_kanban(feature_id)` |
| `ProjectStateService` | Service object in `src/dashboard/services/project_state.py`; exposes `get_health()` |
| `SyncService` | Service object in `src/dashboard/services/sync.py`; exposes `trigger_sync()` |
| `DashboardFileReader` | File I/O utility in `src/dashboard/file_reader.py`; consolidates path-traversal-safe reads for research/artifact/contracts routes |
| `src/specify_cli/dashboard/handlers/` | Thin CLI adapter after extraction; each method contains only one delegation call to `src/dashboard/` |
| `api_types.py` | Existing TypedDict contract file; unchanged by this mission; consumed by `src/dashboard/` response assembly |
| `05_ownership_map.md` | Updated with `dashboard` slice entry following the Audience A procedure |
| `05_ownership_manifest.yaml` | Machine-readable companion; updated with `dashboard` key |
| ADR (new) | Architecture Decision Record documenting the extraction decision; stored in `architecture/2.x/adr/` |
| Seam tests | New tests verifying the CLI adapter → service layer delegation boundary for each route |
| Architectural boundary test | Asserts `src/dashboard/` has zero imports from `src/specify_cli/dashboard/` |

## Success Criteria

| # | Criterion | How verified |
|---|---|---|
| SC-001 | `src/dashboard/` contains no imports from `src/specify_cli/dashboard/` (circular-import boundary) | Architectural boundary test `test_dashboard_boundary.py` passes in CI |
| SC-002 | All dashboard routes return identical responses before and after extraction | Existing dashboard integration test suite passes with zero regressions |
| SC-003 | Every handler method in the CLI adapter delegates to a single service call with no inline business logic | Code review against FR-007; seam tests pass |
| SC-004 | The ownership manifest `dashboard` key is present and valid | Manifest-driven CI tooling parses without error |
| SC-005 | The extraction PR description ticks off every mandatory ownership map field | PR review using the Audience B checklist |
| SC-006 | `dashboard.js` displays correct data in the operator's browser after extraction | Manual smoke-test of the running dashboard against the stabilised endpoint contracts |

## Assumptions

- The current `api_types.py` TypedDict shapes accurately reflect the externally observed endpoint contracts; no undocumented field additions exist in `features.py` or `api.py`.
- Static asset serving and HTML template rendering are not business logic and remain in `src/specify_cli/dashboard/handlers/`.
- The strangler-fig extraction pattern (incremental per-route, not big-bang) is the intended approach, consistent with prior charter and glossary extractions.
- No concurrent in-flight PR is modifying `src/specify_cli/dashboard/handlers/` during this mission.

## Governance

### Active Directives

| Directive | Title | Application |
|---|---|---|
| `DIRECTIVE_001` | Architectural Integrity Standard | All new component boundaries in `src/dashboard/` must have explicit inputs, outputs, and dependencies documented before implementation begins. Boundary violations discovered in review must be resolved before merge. |
| `PROJECT_003` | Risk Appetite Directive | The extraction has a moderate blast radius (all dashboard routes). Changes must be staged incrementally (strangler-fig). Each intermediate step must leave the test suite green. Flag any step that touches more than one route boundary at once for explicit risk review. |
| `DIRECTIVE_024` | Locality of Change | Edits are scoped to `src/dashboard/`, `src/specify_cli/dashboard/handlers/`, `architecture/2.x/`, and `tests/`. Opportunistic cleanup of unrelated `specify_cli` modules is not permitted in this mission. |
| `DIRECTIVE_031` | Context-Aware Design | The `src/dashboard/` bounded context uses the canonical mission/work-package/lane terminology. The CLI adapter is the explicit translation layer between the HTTP transport context and the dashboard service context. No domain terms from the HTTP layer (`request`, `response`, `path`) may leak into `src/dashboard/`. |
| `DIRECTIVE_036` | Black-Box Integration Testing | Seam tests exercise the CLI adapter through its external HTTP interface and assert on observable response output. Tests must not import inside-boundary service objects directly to invoke business logic. |
| `DIRECTIVE_037` | Living Documentation Sync | The ownership map, ADR, and this spec must be updated in the same change as the code they describe. When an extraction step stabilises a route contract, `api_types.py` comments and relevant doc references are updated in the same commit. |

### Applied Tactics

| Tactic | Application |
|---|---|
| `refactoring-strangler-fig` | Extract one route at a time: protect current behavior with tests, introduce the service object alongside the inline handler logic, reroute the handler to delegate, verify, then remove the inline code. |
| `anti-corruption-layer` | `src/specify_cli/dashboard/handlers/` is the ACL between the HTTP transport context and `src/dashboard/`. All HTTP-specific concerns (`BaseHTTPRequestHandler`, status codes, header parsing) live in the adapter, never in the service layer. |
| `connascence-analysis` | Before designing the service boundary, classify the coupling in each handler method. Dynamic connascence (execution-order dependencies between scan and charter reads) must be resolved by the service layer interface design, not passed through as-is. |
| `refactoring-extract-class-by-responsibility-split` | Map handler methods to responsibility clusters (mission state queries, charter reads, glossary reads, diagnostics) before creating service objects. One responsibility cluster → one service object. |
| `test-boundaries-by-responsibility` | Seam tests treat the CLI adapter as inside-boundary (exercised for real) and external I/O (scanner, filesystem, charter) as outside-boundary (stubbed with fixtures). The architectural boundary test treats `src/dashboard/` as inside-boundary and `src/specify_cli/` as outside-boundary (asserted absent). |
| `adr-drafting-workflow` (via `how-we-apply-directive-003`) | Draft the ADR in the same PR as the ownership map entry (FR-003). Include context, decision, rationale, consequences, and rejected alternatives. Cross-link from the ownership map entry and from `architecture/adrs/README.md`. |

### Applied Styleguides

| Styleguide | Application |
|---|---|
| `python-style-guide` | All new `src/dashboard/` modules carry type annotations on every public function and class attribute. `ruff` passes with zero warnings on new code. No bare `except` clauses. |
| `testing-style-guide` | Seam and architectural tests are deterministic. Tests are named after the behavior they verify (`test_mission_panel_delegates_to_dashboard_service`), not after implementation details. Fixture-based approach for filesystem and scanner dependencies. |

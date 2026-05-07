# Research: Dashboard Service Extraction

*Phase 0 output for mission `dashboard-service-extraction-01KQMCA6`*

---

## 1. Connascence Analysis of Current Handler Layer

**Scope**: `src/specify_cli/dashboard/handlers/features.py` (402 lines) and
`src/specify_cli/dashboard/handlers/api.py` (263 lines).

### Dynamic connascence (high priority)

| Location | Type | Strength | Degree | Notes |
|---|---|---|---|---|
| `handle_features_list` assembles `MissionContext` inline after calling `scan_all_features` + `resolve_active_feature` + `get_mission_by_name` | Connascence of Execution | High | 3 modules | Execution order is implicitly required; failure in any step silently degrades the response |
| `handle_kanban` calls `scan_feature_kanban` then conditionally imports `compute_weighted_progress` + `materialize` | Connascence of Execution | High | 2 modules | Conditional import inside method body; tight temporal coupling to `status.reducer` |
| `handle_sync_trigger` calls `ensure_sync_daemon_running` then `get_sync_daemon_status` then constructs request | Connascence of Execution | High | 2 modules | 3-step orchestration with early-exit logic that mixes HTTP response concerns with daemon state |
| `handle_health` interleaves `get_sync_daemon_status` call with `HealthResponse` dict construction | Connascence of Value | Medium | 2 modules | Status dict shape depends on daemon response shape; both asserted in the same method |

**Decision**: All three method clusters above exceed the extraction threshold. Moving them
to dedicated service objects resolves the high-strength dynamic connascence by giving each
cluster a stable, testable interface.

### Static connascence (accepted)

| Location | Type | Strength | Notes |
|---|---|---|---|
| All handlers import TypedDict shapes from `api_types.py` | Connascence of Type | Low | Intentional contract coupling; resolved by relocating `api_types.py` to `src/dashboard/` |
| `handle_research`, `handle_artifact` use `resolve_feature_dir` | Connascence of Name | Low | File-serving delegation; stays in adapter |
| `DashboardRouter` inherits from all 5 handler classes | Connascence of Name | Low | Routing topology; not changed |

---

## 2. Service Boundary Design

### Decision: Three service objects, not one

**Options considered:**

| Option | Pros | Cons |
|---|---|---|
| One `DashboardService` with all extracted methods | Simple dependency injection; one seam to test | Responsibilities bleed together; `MissionScanService` and `SyncService` have entirely different dependencies — bundling them inflates constructor coupling |
| One service object per handler class | 1:1 mapping, easy to trace | `FeatureHandler` has two logical clusters (scan and file I/O); the file-serving cluster doesn't belong in a service object |
| Three service objects by responsibility cluster | Cohesive dependencies; independently testable; matches `refactoring-extract-class-by-responsibility-split` tactic | Slightly more wiring in the adapter |

**Decision**: Three service objects by responsibility cluster (`MissionScanService`,
`ProjectStateService`, `SyncService`). File-serving methods stay in the adapter per C-006.

### Decision: `api_types.py` moves to `src/dashboard/`

**Options considered:**

| Option | Pros | Cons |
|---|---|---|
| Move to `src/dashboard/api_types.py`; shim at old path | `src/dashboard/` can import response types without depending on `specify_cli`; one authoritative location | Requires shim file; shim needs `removal_release` annotation |
| Keep in `src/specify_cli/dashboard/`; service objects return dicts | No shim needed; no file move | Service objects must return `Any` or duplicated TypedDict shapes; type safety lost |
| Keep in `src/specify_cli/dashboard/`; service objects import from `specify_cli` | No file move | Violates the practical boundary rule (service layer imports from adapter package) |

**Decision**: Move to `src/dashboard/api_types.py`. Add backward-compat shim at
`src/specify_cli/dashboard/api_types.py` with `removal_release: FastAPI milestone`.

---

## 3. Prior Extraction Pattern Review

Reviewing `src/charter/` and `src/doctrine/` extractions for applicable precedents:

| Pattern | Applied in charter/doctrine | Applies here |
|---|---|---|
| Top-level canonical package | `src/charter/`, `src/doctrine/` | `src/dashboard/` |
| Shim at old import path | `src/specify_cli/charter/context.py` (thin re-export) | `src/specify_cli/dashboard/api_types.py` |
| Ownership map entry | Already in `05_ownership_map.md` | Dashboard slice to be added |
| ADR for extraction decision | `architecture/2.x/adr/2026-04-25-1-*` | `architecture/adrs/2026-05-02-1-*` |
| Architectural layer test update | `test_layer_rules.py` `_DEFINED_LAYERS` | Add `dashboard` to `_DEFINED_LAYERS` |
| Strangler-fig per method | Used in `charter-ownership-consolidation-*` | Per-route here |

---

## 4. FR-010 Boundary Test Scope Calibration

**Problem**: FR-010 as written requires `src/dashboard/` to have zero imports from
`src/specify_cli/`. But the extracted service objects must call `specify_cli.scanner`,
`specify_cli.status.reducer`, `specify_cli.sync.daemon`, etc. These subsystems are not
yet extracted to top-level packages.

**Resolution**: The practical boundary assertion for this mission is:

> No module inside `src/dashboard/` imports from `src/specify_cli/dashboard/`

This specifically prevents the circular dependency between the service layer and its own
adapter. The remaining `specify_cli.*` imports from `src/dashboard/` are intentional
dependencies on lower-layer subsystems that will be resolved in future extraction missions.

`test_dashboard_boundary.py` implements this narrower assertion using `pytestarch` or
direct `ast` import scanning (consistent with `test_events_tracker_public_imports.py`
which uses AST scanning for a similar boundary check).

The ADR documents this staged approach and names the future missions (scanner, status) as
prerequisites for the full boundary claim.

---

## 5. `dashboard.js` Contract Stabilisation

`dashboard.js` currently fetches from endpoints whose response shapes are defined by
`api_types.py`. After extraction, the shapes are unchanged (C-002). The adaptation work
in WP07 is a smoke-test + field-reference audit, not a behavioral change:

1. Verify all field references in `dashboard.js` (`fetch`, `response.json()`, property
   accesses) map to fields present in the `api_types.py` TypedDicts.
2. Verify no field has been silently dropped or renamed by the extraction (regression
   check against the pre-extraction snapshot).
3. Update any hardcoded path constants in `dashboard.js` if endpoint URLs change (they
   should not — C-001 holds the transport layer frozen).

**Expected outcome**: zero changes to `dashboard.js` beyond confirming the audit passed.
If any drift is found, it predates this mission and must be documented as a pre-existing
issue, not introduced by the extraction.

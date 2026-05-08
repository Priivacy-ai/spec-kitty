# Mission Specification: Dashboard Services Domain Migration (Phase B)

**Mission ID**: `01KR151PM9D00Z1YMP72DZBMVA`
**Mission slug**: `dashboard-services-domain-migration-01KR151P`
**Friendly name**: Dashboard Services Domain Migration (Phase B)
**Type**: software-dev
**Target branch**: `feature/645-api-surface-completion-mission-c`
**Epic**: [#645 — Stable Application API Surface](https://github.com/Priivacy-ai/spec-kitty/issues/645)
**Predecessor issues addressed**: [PR #970](https://github.com/Priivacy-ai/spec-kitty/pull/970) (Robert's P1/P2 review findings)
**Date**: 2026-05-07
**Status**: Draft

---

## Overview

This mission executes **Phase B** of Architect Alphonso's service-placement remediation
(`architecture/2.x/initiatives/2026-05-stable-application-api-surface/api-service-placement-assessment.md`).

Phase A (Mission C, `api-surface-completion-services-aliases-async-01KQSXDA`) placed the
two new domain services (`GlossaryService`, `LintService`) in their domain modules rather
than in `dashboard/services/`, proving the pattern at zero migration risk. Phase B
completes the structural repair by moving the four existing services:

| Current location | Target location |
|---|---|
| `dashboard/services/registry.py` | `specify_cli/missions/registry.py` |
| `dashboard/services/mission_scan.py` | `specify_cli/missions/scan_service.py` |
| `dashboard/services/project_state.py` | `specify_cli/missions/project_state.py` |
| `dashboard/services/sync.py` | `specify_cli/missions/sync_service.py` |

After the move, compatibility shims remain in `dashboard/services/` for one release cycle
(Phase C retires them). All callers inside `specify_cli/` update their imports in this
mission; `dashboard/api/` callers are updated as well so the shims have zero dependents
at merge time, making Phase C a mechanical deletion.

In addition to the structural move, this mission fixes two correctness bugs surfaced by
Robert Douglass in his review of PR #970:

- **P1** — `MissionRegistry.list_missions()` caches on the top-level `kitty-specs/`
  directory key only, making it blind to `status.events.jsonl` appends inside individual
  mission directories. The fix is to promote the per-mission cache key from
  `WorkPackageRegistry` up to the list-level cache so `list_missions()` detects event-log
  changes without requiring a top-level directory mutation.

- **P2** — Per-mission `WorkPackageRegistry` instances are stored in a
  `WeakValueDictionary`. Because FastAPI request handlers hold the registry only as a
  local variable, the instance can be GC'd between requests, silently defeating the
  per-mission filesystem-scan cache. The fix is to replace the `WeakValueDictionary`
  with an explicit strong-reference store with a documented eviction policy.

These fixes are in scope here because the migration is the lowest-risk moment to correct
them — the registries are already being touched, and landing the bugs in a new module
at their canonical home would be careless.

### Relationship to issue #992 (Queue Drain Epic)

Issue #992's north-star invariant 1 reads: *"A Work Package has exactly one lifecycle
authority."* The current architecture has at least three independent readers of
`kitty-specs/` data that can disagree:

1. `spec-kitty next` / `agent action implement` — reads via `specify_cli.status.*`
2. Dashboard API — reads via `MissionRegistry` → `scan_all_features` → legacy scanner
3. `spec-kitty dashboard --json` — reads via a direct `build_mission_registry` call

Phase B collapses readers 2 and 3 onto the same `specify_cli/missions/registry.py`
module that also serves the CLI. All transport-side consumers (FastAPI routers, CLI
commands, future MCP adapter) import from a single canonical service. The P1 fix
ensures that service is also *correct* — stale reads are the first symptom of the
multi-authority failure mode #992 diagnoses.

This mission is necessary but not sufficient to close #992; the write-path authority
(Workstreams 2–6) requires separate missions. It is the read-surface prerequisite those
missions depend on.

---

## Goals

1. Move the four services to `specify_cli/missions/` so the canonical mission/WP
   read path lives at the domain layer, never inside the presentation package.
2. Eliminate the inverted import: no module under `specify_cli/` or `kernel/` may
   import from `dashboard.*` after this mission; enforced by extending the existing
   `test_dashboard_boundary.py` architectural test.
3. Fix `list_missions()` cache staleness (P1) so lane counts in `MissionRecord` always
   reflect the current `status.events.jsonl` content.
4. Fix `WeakValueDictionary` (P2) so per-mission `WorkPackageRegistry` instances survive
   across requests within a single `MissionRegistry` lifetime.
5. Leave thin compatibility shims in `dashboard/services/` for each moved module, each
   registered in `architecture/2.x/shim-registry.yaml` with a `removal_release`.
6. Update every `specify_cli/` caller to the canonical path so the shims have zero
   dependents within `specify_cli/` at merge time.
7. Update every `dashboard/api/` caller to the canonical `specify_cli.missions.*` path
   (no caller should import through the shims at merge time; Phase C is then a pure deletion).

---

## Out of Scope

- **Phase C** — shim retirement and deletion of `dashboard/services/`. That is a
  separate one-WP housekeeping mission after at least one tagged release.
- **Write-path lifecycle authority** — this mission establishes the read surface only;
  the mutation authority (status transitions, merge lifecycle, review cycle) is #992's
  separate concern.
- **`specify_cli/dashboard/scanner.py` shim retirement** — governed by `shim-registry.yaml`
  with its own `removal_release`; not touched in this mission.
- **New API endpoints or response shape changes** — the move is transparent to HTTP
  consumers; wire shapes are unchanged.
- **Performance benchmarking** — the cache fixes are correctness fixes; the NFR-001/NFR-002
  measurement slots from the FastAPI migration release checklist remain operator-measured.

---

## Assumptions

1. `specify_cli/missions/` already exists as a Python package (confirmed; contains
   `api_types.py` shipped by Mission C).
2. The `dashboard/services/__init__.py` re-export facade can remain as-is for one release
   cycle; Phase C removes it together with the shims.
3. The `architecture/2.x/shim-registry.yaml` schema and CI enforcement
   (`spec-kitty doctor shim-registry`) are operational as of mission
   `migration-shim-ownership-rules-01KPDYDW`.
4. The `test_dashboard_boundary.py` architectural test currently asserts "no
   `specify_cli.dashboard.*` imports inside `src/dashboard/`". The extension in this
   mission adds the reciprocal: no `dashboard.*` imports inside `src/specify_cli/` or
   `src/kernel/`.
5. The `removal_release` for all four shims is the first release tag after this mission
   merges into `feature/645` and subsequently into `main`.

---

## User Scenarios and Testing

### Scenario A — Dashboard reflects a status event without a server restart

An agent appends a `done` event to `status.events.jsonl` for WP03. The next
`GET /api/missions/{id}/status` response shows `done: 1, claimed: 0` without requiring
a server restart or cache flush command. The dashboard tile updates on the next poll cycle.

**Acceptance test**: integration test — append event, call `list_missions()` on the
same `MissionRegistry` instance, assert lane counts reflect the appended event.

### Scenario B — Multiple requests share the same WorkPackageRegistry instance

A load-test issues ten sequential `GET /api/missions/{id}/workpackages` requests. All
ten share the same `WorkPackageRegistry` instance (per mission, per registry lifetime)
and the filesystem is scanned only once per cache-key change.

**Acceptance test**: create a `MissionRegistry`, call `workpackages_for()` twice for
the same mission, assert the returned `WorkPackageRegistry` is the same Python object
(identity check, not equality).

### Scenario C — CLI `--json` and dashboard API agree on lane counts

`spec-kitty dashboard --json` and `GET /api/missions` are called back-to-back against
the same project directory. Both return the same `done` count for a mission whose
event log was recently updated. (Current code diverges because they use different
readers; after this mission they share the registry.)

### Scenario D — Architectural test catches an inverted import

`tests/architectural/test_dashboard_boundary.py` passes with the extended assertion
enabled. A synthetic import of `from dashboard.services.registry import MissionRegistry`
planted inside a file under `src/specify_cli/` is detected by the test.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `specify_cli/missions/registry.py` contains `MissionRegistry`, `WorkPackageRegistry`, `LaneCounts`, `MissionRecord`, `WorkPackageRecord`, and `CacheEntry`. The module is a self-contained move of the canonical implementation; no `dashboard.*` import is present anywhere in the file. | Proposed |
| FR-002 | `MissionRegistry.list_missions()` applies per-mission cache invalidation. The implementation stores per-mission `CacheEntry` objects keyed on `_mission_dir_cache_key(feature_dir)` alongside the top-level directory key. The top-level key detects new or deleted mission directories; each per-mission key detects event-log appends and `meta.json` edits independently. A stale per-mission key triggers a targeted rescan of that mission only, not a full walk. | Proposed |
| FR-003 | `MissionRegistry._wp_registries` is changed from `WeakValueDictionary` to `dict[str, WorkPackageRegistry]`. The docstring documents the eviction policy explicitly: entries are evicted only when the enclosing `MissionRegistry` instance is garbage-collected. | Proposed |
| FR-004 | `specify_cli/missions/scan_service.py` contains `MissionScanService` and `parse_kanban_path`, moved from `dashboard/services/mission_scan.py`. No `dashboard.*` import is present. The TYPE_CHECKING-only import of `MissionRegistry` is updated to source from `specify_cli.missions.registry`. | Proposed |
| FR-005 | `specify_cli/missions/project_state.py` contains `ProjectStateService`, moved from `dashboard/services/project_state.py`. No `dashboard.*` import is present. | Proposed |
| FR-006 | `specify_cli/missions/sync_service.py` contains `SyncService`, `SyncTriggerResult`, and `_build_trigger_request`, moved from `dashboard/services/sync.py`. No `dashboard.*` import is present. | Proposed |
| FR-007 | `dashboard/services/registry.py` is replaced with a shim that re-exports every public symbol currently importable from it, sourced from `specify_cli.missions.registry`. The shim carries a module-level `# SHIM — removal_release: <next-version>` comment and no logic beyond the re-exports. | Proposed |
| FR-008 | `dashboard/services/mission_scan.py`, `project_state.py`, and `sync.py` are each replaced with shims following the same pattern as FR-007, pointing to `specify_cli.missions.scan_service`, `specify_cli.missions.project_state`, and `specify_cli.missions.sync_service` respectively. | Proposed |
| FR-009 | All four shims are registered in `architecture/2.x/shim-registry.yaml` with `grandfathered: false`, `owner_mission: dashboard-services-domain-migration-01KR151P`, and `removal_release` set to the next release tag after this mission merges. | Proposed |
| FR-010 | `specify_cli/cli/commands/dashboard.py` imports `MissionRecord` and `MissionRegistry` from `specify_cli.missions.registry`. No `dashboard.*` import remains (including under `TYPE_CHECKING`). | Proposed |
| FR-011 | `specify_cli/dashboard/handlers/features.py` imports `MissionScanService` and `parse_kanban_path` from `specify_cli.missions.scan_service`. No `dashboard.*` import remains. | Proposed |
| FR-012 | `specify_cli/dashboard/handlers/api.py` imports `ProjectStateService` from `specify_cli.missions.project_state` and `SyncService` from `specify_cli.missions.sync_service`. The existing re-export of `_build_trigger_request` as `_build_sync_trigger_request` is updated to source from `specify_cli.missions.sync_service` (C-007). No `dashboard.*` import remains. | Proposed |
| FR-013 | `dashboard/api/app.py`, `deps.py`, `routers/missions.py`, `routers/health.py`, and `routers/sync.py` import their service symbols directly from `specify_cli.missions.*`. At merge time, no caller in `dashboard/api/` imports through the compatibility shims. | Proposed |
| FR-014 | `tests/architectural/test_dashboard_boundary.py` gains a new assertion: no module under `src/specify_cli/` or `src/kernel/` contains any import of a symbol from `src/dashboard/`. The assertion uses the same `pytestarch` or AST tooling already in place; a synthetic violation in a temporary file must trigger it. | Proposed |
| FR-015 | A regression test verifies P1: given a warm `MissionRegistry` list cache, appending a new `done` event to a mission's `status.events.jsonl` and calling `list_missions()` on the same registry instance returns `MissionRecord.lane_counts` that reflect the appended event (stale cache hit does not occur). | Proposed |
| FR-016 | A regression test verifies P2: calling `workpackages_for()` twice on the same `MissionRegistry` for the same mission `mission_id` returns the identical `WorkPackageRegistry` object (Python `is` check). | Proposed |
| FR-017 | A new ADR is filed at `architecture/2.x/adr/2026-05-07-1-dashboard-services-phase-b.md` documenting: the motivation for Phase B, the chosen target layout, the shim lifecycle, the `removal_release` target for Phase C, and the relationship to #992. The ADR is cross-linked from `architecture/2.x/adr/README.md`. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | All existing dashboard tests pass without modification to their assertions. `test_seams.py`, the OpenAPI snapshot test, `test_transport_does_not_import_scanner.py`, and `test_fastapi_handler_purity.py` must remain green. | 100% pass rate | Proposed |
| NFR-002 | `mypy --strict` passes for all moved modules and updated caller files after import-path changes. Zero new type errors introduced. | Zero new errors | Proposed |
| NFR-003 | Per-mission cache key computation in the P1 fix does not increase median `list_missions()` latency by more than 5 ms relative to the pre-fix baseline, measured using the existing dashboard test fixtures. | ≤ 5 ms increase | Proposed |
| NFR-004 | No new Python packages are added to `pyproject.toml`. The P2 fix uses stdlib `dict`. | Zero new dependencies | Proposed |
| NFR-005 | `spec-kitty doctor shim-registry` exits clean with zero warnings after all four shims are registered. | Clean doctor output | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The moved modules must not import from `dashboard.*` at any import level (top-level, deferred, or under `TYPE_CHECKING`). Any existing `TYPE_CHECKING` imports that reference `dashboard.services.*` must be updated to the new canonical paths. | Proposed |
| C-002 | The compatibility shims must be pure re-exports — no business logic, no conditional imports, no side effects. A shim body longer than 15 executable lines is a signal that the move was incomplete. | Proposed |
| C-003 | `dashboard/services/__init__.py` continues to re-export from `dashboard.services.registry` (which becomes the registry shim). This facade is left intact for Phase C; it is not touched in this mission. | Proposed |
| C-004 | No HTTP wire shapes change. `MissionRecord`, `WorkPackageRecord`, and the Pydantic models in `dashboard/api/models.py` are structurally identical before and after the move; only their import paths change. The OpenAPI snapshot test must pass without updating the snapshot. | Proposed |
| C-005 | The P1 cache fix must not alter the observable behavior of `WorkPackageRegistry.list_work_packages()`. That method already uses `_mission_dir_cache_key` correctly; the fix extends `list_missions()` to apply equivalent granularity at the list level without changing the per-WP cache contract. | Proposed |
| C-006 | Shim `removal_release` values must reference a version that has not yet been tagged at the time this mission merges. | Proposed |
| C-007 | `specify_cli/dashboard/handlers/api.py` currently re-exports `_build_trigger_request` as `_build_sync_trigger_request` for seam-test compatibility. After this mission, that re-export must point to `specify_cli.missions.sync_service._build_trigger_request`; the re-export name `_build_sync_trigger_request` is preserved so existing seam tests require no modification. | Proposed |

---

## Key Entities

| Entity | Description | Location after migration |
|--------|-------------|--------------------------|
| `MissionRegistry` | Single sanctioned reader for mission-level summary data. Per-mission + top-level cache keys after P1 fix. | `specify_cli/missions/registry.py` |
| `WorkPackageRegistry` | Per-mission WP reader. Strong-reference store after P2 fix. | `specify_cli/missions/registry.py` |
| `MissionRecord` | Frozen dataclass: one mission's identity + lane counts. | `specify_cli/missions/registry.py` |
| `WorkPackageRecord` | Frozen dataclass: one WP's state snapshot. | `specify_cli/missions/registry.py` |
| `LaneCounts` | Frozen value object: 9-lane aggregate. | `specify_cli/missions/registry.py` |
| `CacheEntry` | Internal generic cache primitive. | `specify_cli/missions/registry.py` |
| `MissionScanService` | Assembles kanban / features-list response from the registry. | `specify_cli/missions/scan_service.py` |
| `parse_kanban_path` | Module-level path parser for `/api/kanban/<id>`. | `specify_cli/missions/scan_service.py` |
| `ProjectStateService` | Assembles `HealthResponse` from daemon status + project path. | `specify_cli/missions/project_state.py` |
| `SyncService` | Orchestrates sync-daemon trigger and result interpretation. | `specify_cli/missions/sync_service.py` |
| `SyncTriggerResult` | Dataclass: HTTP status + body for the sync adapter. | `specify_cli/missions/sync_service.py` |
| `_build_trigger_request` | Pure helper: builds the sync-daemon HTTP request. | `specify_cli/missions/sync_service.py` |
| `dashboard/services/registry.py` | Compatibility shim → re-exports from `specify_cli.missions.registry`. | `dashboard/services/registry.py` (shim) |
| `dashboard/services/mission_scan.py` | Compatibility shim → re-exports from `specify_cli.missions.scan_service`. | `dashboard/services/mission_scan.py` (shim) |
| `dashboard/services/project_state.py` | Compatibility shim → re-exports from `specify_cli.missions.project_state`. | `dashboard/services/project_state.py` (shim) |
| `dashboard/services/sync.py` | Compatibility shim → re-exports from `specify_cli.missions.sync_service`. | `dashboard/services/sync.py` (shim) |

---

## Work Package Outline

### WP01 — Registry migration and cache fixes

Move `MissionRegistry`, `WorkPackageRegistry`, and all supporting classes to
`specify_cli/missions/registry.py`. Apply the P1 fix (per-mission cache key for
`list_missions()`) and the P2 fix (replace `WeakValueDictionary` with `dict`).
Convert `dashboard/services/registry.py` to a compatibility shim.
Update `specify_cli/cli/commands/dashboard.py` imports.

**Owned files:**
- `src/specify_cli/missions/registry.py` (new — canonical implementation)
- `src/dashboard/services/registry.py` (replaced with shim)
- `src/specify_cli/cli/commands/dashboard.py` (import update)

**Acceptance gate:** P1 regression test passes; P2 identity test passes; all existing
registry and dashboard CLI tests pass.

---

### WP02 — MissionScanService migration

Move `MissionScanService` and `parse_kanban_path` to `specify_cli/missions/scan_service.py`.
Convert `dashboard/services/mission_scan.py` to a shim.
Update `specify_cli/dashboard/handlers/features.py` imports.

**Owned files:**
- `src/specify_cli/missions/scan_service.py` (new)
- `src/dashboard/services/mission_scan.py` (replaced with shim)
- `src/specify_cli/dashboard/handlers/features.py` (import update)

**Acceptance gate:** `test_seams.py` features tests pass; no `from dashboard.*` in
`specify_cli/dashboard/handlers/features.py`.

---

### WP03 — ProjectStateService and SyncService migration

Move `ProjectStateService` to `specify_cli/missions/project_state.py` and `SyncService`
+ `SyncTriggerResult` + `_build_trigger_request` to `specify_cli/missions/sync_service.py`.
Convert both `dashboard/services/` source files to shims.
Update `specify_cli/dashboard/handlers/api.py` imports, preserving the
`_build_sync_trigger_request` re-export for seam-test compatibility (C-007).

**Owned files:**
- `src/specify_cli/missions/project_state.py` (new)
- `src/specify_cli/missions/sync_service.py` (new)
- `src/dashboard/services/project_state.py` (replaced with shim)
- `src/dashboard/services/sync.py` (replaced with shim)
- `src/specify_cli/dashboard/handlers/api.py` (import update)

**Acceptance gate:** `/api/health` and `/api/sync/trigger` seam tests pass; no
`from dashboard.*` in `specify_cli/dashboard/handlers/api.py`.

---

### WP04 — API consumer updates, shim registry, architectural enforcement, and governance

Update all `dashboard/api/` consumers to import directly from `specify_cli.missions.*`
(FR-013), so the shims have zero dependents at merge time.
Register all four shims in `architecture/2.x/shim-registry.yaml` (FR-009).
Extend `tests/architectural/test_dashboard_boundary.py` with the reciprocal assertion
(FR-014) and verify it catches a synthetic violation.
Write the P1 and P2 regression tests (FR-015, FR-016).
File the Phase B ADR (FR-017).

**Owned files:**
- `src/dashboard/api/app.py` (import update)
- `src/dashboard/api/deps.py` (import update)
- `src/dashboard/api/routers/missions.py` (import update)
- `src/dashboard/api/routers/health.py` (import update)
- `src/dashboard/api/routers/sync.py` (import update)
- `architecture/2.x/shim-registry.yaml` (4 new shim entries)
- `tests/architectural/test_dashboard_boundary.py` (extended assertion)
- `tests/specify_cli/missions/test_registry_cache.py` (new — P1 + P2 regression)
- `architecture/2.x/adr/2026-05-07-1-dashboard-services-phase-b.md` (new ADR)

**Acceptance gate:** `spec-kitty doctor shim-registry` exits clean; extended boundary
test detects a synthetic violation; P1 and P2 regression tests pass; OpenAPI snapshot
test passes unchanged.

---

## Success Criteria

1. `src/specify_cli/missions/registry.py`, `scan_service.py`, `project_state.py`, and
   `sync_service.py` exist and contain the full canonical implementations.
2. No module under `src/specify_cli/` or `src/kernel/` has any `dashboard.*` import —
   enforced and verified by the extended `test_dashboard_boundary.py` (FR-014).
3. `list_missions()` returns fresh lane counts after a `status.events.jsonl` append on a
   warm cache — verified by the P1 regression test (FR-015).
4. `workpackages_for()` returns the same `WorkPackageRegistry` object on repeated calls
   within one registry lifetime — verified by the P2 identity test (FR-016).
5. All four shims are in `shim-registry.yaml`; `spec-kitty doctor shim-registry` exits
   clean (FR-009, NFR-005).
6. Zero callers in `dashboard/api/` import through the shims at merge time (FR-013).
7. All existing dashboard tests, architectural tests, and seam tests pass without
   modification to their assertions (NFR-001).
8. ADR `2026-05-07-1-dashboard-services-phase-b.md` exists and is cross-linked from
   `architecture/2.x/adr/README.md` (FR-017).

---

## Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| Mission C (`api-surface-completion-services-aliases-async-01KQSXDA`) | Predecessor | Must be merged first. Established `specify_cli/missions/api_types.py` and the Phase A placement pattern. |
| Mission B (`resource-oriented-mission-api-01KQQRF2`) | Predecessor | Must be merged first. Introduced `DIRECTIVE_API_DEPENDENCY_DIRECTION` and the registry pattern this mission elevates. |
| `specify_cli/missions/` package | Runtime | Exists as of Mission C; this mission extends it with domain service modules. |
| `architecture/2.x/shim-registry.yaml` | Governance | Schema and CI enforcement active as of `migration-shim-ownership-rules-01KPDYDW`. |
| `tests/architectural/test_dashboard_boundary.py` | Test | Extended in WP04; its current form is the extension baseline. |

---

## Related Issues and Documents

- Epic: [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645)
- Domain-boundary repair epic: [#992](https://github.com/Priivacy-ai/spec-kitty/issues/992)
- Phase A assessment: `architecture/2.x/initiatives/2026-05-stable-application-api-surface/api-service-placement-assessment.md`
- Initiative README: `architecture/2.x/initiatives/2026-05-stable-application-api-surface/README.md`
- PR #970 Robert's review: [link](https://github.com/Priivacy-ai/spec-kitty/pull/970)
- ADR (Mission B registry and cache): `architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md`
- ADR (Mission B resource-oriented API): `architecture/2.x/adr/2026-05-03-2-resource-oriented-mission-api.md`
- Shim registry rulebook: `architecture/2.x/06_migration_and_shim_rules.md`

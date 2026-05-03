# Tasks — Resource-Oriented Mission API and HATEOAS-LITE

**Mission**: `resource-oriented-mission-api-01KQQRF2`
**Branch**: `feature/650-dashboard-ui-ux-overhaul`
**Spec / Plan / Design**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

4 work packages, 30 subtasks, average 7.5 subtasks per WP.
WP01 is a strict prerequisite for WP02. WP04 depends on all three predecessors.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Extend `WorkPackageRecord` dataclass with `claimed_at: datetime \| None` and `blocked_reason: str \| None` fields in `registry.py` | WP01 | — |
| T002 | Update `WorkPackageRegistry` per-WP scan to populate `claimed_at` and `blocked_reason` from `status.events.jsonl` | WP01 | — |
| T003 | Add `ReviewEvidence` and `WorkPackageAssignment` Pydantic v2 models to `src/dashboard/api/models.py` | WP01 | [P] |
| T004 | Add `MissionSummary` and `Mission` resource models (subclass `ResourceModel`, declare `_links`) | WP01 | [P] |
| T005 | Add `MissionStatus` resource model | WP01 | [P] |
| T006 | Add `WorkPackageSummary` and `WorkPackage` resource models; run arch test to confirm non-vacuous | WP01 | [P] |
| T007 | Create `src/dashboard/api/routers/missions.py` skeleton: `_mission_links()`, `_wp_links()`, `get_or_404()` helpers | WP02 | — |
| T008 | Implement `GET /api/missions` → `list[MissionSummary]` | WP02 | — |
| T009 | Implement `GET /api/missions/{mission_id}` → `Mission` (404 / 409) | WP02 | — |
| T010 | Implement `GET /api/missions/{mission_id}/status` → `MissionStatus` | WP02 | [P] |
| T011 | Implement `GET /api/missions/{mission_id}/workpackages` → `list[WorkPackageSummary]` | WP02 | [P] |
| T012 | Implement `GET /api/missions/{mission_id}/workpackages/{wp_id}` → `WorkPackage` (404) | WP02 | — |
| T013 | Register missions router in `src/dashboard/api/app.py` | WP02 | — |
| T014 | Add `tests/test_dashboard/test_missions_api.py`: list, detail, status, WP list, WP detail, 404, 409 | WP02 | — |
| T015 | Verify `test_transport_does_not_import_scanner.py` passes after all routes wired | WP02 | — |
| T016 | Verify `test_url_naming_convention.py` accepts all new paths | WP02 | — |
| T017 | Add `tags=["kanban"]` to `features.py` and `kanban.py` `APIRouter` constructors | WP03 | — |
| T018 | Add domain tags to all remaining routers (research, artifacts, charter, dossier, glossary, health, diagnostics, sync, shutdown, static_mount, lint) | WP03 | [P] |
| T019 | Add `Deprecation: true` and `Link` headers to `GET /api/features` response | WP03 | — |
| T020 | Add `Deprecation: true` and `Link` headers to `GET /api/kanban/{feature_id}` response | WP03 | [P] |
| T021 | Add `tests/test_dashboard/test_deprecation_headers.py`: assert headers present on deprecated routes | WP03 | — |
| T022 | Assert deprecated route response bodies are unchanged (structural parity against pre-mission snapshot) | WP03 | — |
| T023 | Run full architectural test suite; confirm no regressions | WP03 | — |
| T024 | Run full dashboard test suite; confirm no regressions | WP03 | — |
| T025 | Run full test suite; confirm `test_resource_models_have_links.py` green and non-vacuous (≥5 subclasses) | WP04 | — |
| T026 | Regenerate `tests/test_dashboard/snapshots/openapi.json` (once; all routes and tags in place) | WP04 | — |
| T027 | Author `architecture/2.x/adr/2026-05-03-2-resource-oriented-mission-api.md` | WP04 | [P] |
| T028 | Update `architecture/2.x/05_ownership_map.md` and `05_ownership_manifest.yaml`; mark #957/#958 done | WP04 | [P] |
| T029 | Author `kitty-specs/resource-oriented-mission-api-01KQQRF2/issue-matrix.md` | WP04 | [P] |
| T030 | Update `docs/migration/dashboard-fastapi-transport.md` with resource-oriented endpoints section | WP04 | [P] |

## Dependencies

```
WP01 (registry extension + models)
  └──▶ WP02 (all new mission/WP routes + tests)
                 └──▶ WP04 (governance + snapshot)
WP03 (tag grouping + deprecation aliases)
  └──▶ WP04
```

Lane parallelization:
- **Lane A**: WP01 → WP02 → WP04
- **Lane B**: WP03 → WP04

## Work Packages

---

### WP01 — Registry extension and Pydantic resource models

**Goal**: Lay the foundation: extend `WorkPackageRecord` with two missing fields (`claimed_at`, `blocked_reason`), and define all seven new Pydantic response models in `models.py`. After this WP, `tests/architectural/test_resource_models_have_links.py` transitions from vacuous to enforcing.

**Priority**: P0 — gates WP02.
**Independent test**: `pytest tests/architectural/test_resource_models_have_links.py` passes and reports ≥5 `ResourceModel` subclasses verified; `pytest tests/test_dashboard/ -q` exits 0.

**Subtasks**:
- [ ] T001 Extend `WorkPackageRecord` dataclass in `registry.py`
- [ ] T002 Update `WorkPackageRegistry` scan to populate new fields from JSONL
- [ ] T003 Add `ReviewEvidence` and `WorkPackageAssignment` models to `models.py`
- [ ] T004 Add `MissionSummary` and `Mission` models
- [ ] T005 Add `MissionStatus` model
- [ ] T006 Add `WorkPackageSummary` and `WorkPackage` models; verify arch test

**Estimated prompt size**: ~400 lines
**Owned files**: `src/dashboard/services/registry.py`, `src/dashboard/api/models.py`
**Dependencies**: none

---

### WP02 — New mission and workpackage resource routes

**Goal**: Create `src/dashboard/api/routers/missions.py` with all five new resource-oriented endpoints, register in `app.py`, and cover with tests. After this WP, clients can navigate the full mission/WP hierarchy via HATEOAS-LITE links.

**Priority**: P0.
**Independent test**: `GET /api/missions` returns 200 with `_links` on each item; `GET /api/missions/{id}/workpackages/{wp_id}` returns 200 or 404; `pytest tests/test_dashboard/test_missions_api.py` passes; both arch tests pass.

**Subtasks**:
- [ ] T007 Create `missions.py` skeleton with helpers
- [ ] T008 GET /api/missions route
- [ ] T009 GET /api/missions/{id} route
- [ ] T010 GET /api/missions/{id}/status route
- [ ] T011 GET /api/missions/{id}/workpackages route
- [ ] T012 GET /api/missions/{id}/workpackages/{wp_id} route
- [ ] T013 Register router in app.py
- [ ] T014 Test file: all routes + error cases
- [ ] T015 Verify test_transport_does_not_import_scanner passes
- [ ] T016 Verify test_url_naming_convention passes

**Estimated prompt size**: ~550 lines
**Owned files**: `src/dashboard/api/routers/missions.py`, `src/dashboard/api/app.py`, `tests/test_dashboard/test_missions_api.py`
**Dependencies**: WP01

---

### WP03 — Tag grouping and deprecation aliases on existing routers

**Goal**: Tag every `APIRouter` constructor for Swagger/ReDoc grouping (#958), and retrofit `/api/features` + `/api/kanban/{id}` with `Deprecation` / `Link` headers. This WP runs in parallel with WP02.

**Priority**: P1.
**Independent test**: Every path in the app's `/openapi.json` has a non-empty tag; `GET /api/features` response contains `Deprecation: true` header; `pytest tests/test_dashboard/test_deprecation_headers.py` passes; full dashboard test suite exits 0.

**Subtasks**:
- [ ] T017 Tags on features.py and kanban.py
- [ ] T018 Tags on all remaining existing routers
- [ ] T019 Deprecation headers on GET /api/features
- [ ] T020 Deprecation headers on GET /api/kanban/{id}
- [ ] T021 Test file: assert headers present on deprecated routes
- [ ] T022 Assert deprecated response bodies structurally unchanged
- [ ] T023 Run architectural tests
- [ ] T024 Run full dashboard tests

**Estimated prompt size**: ~420 lines
**Owned files**: `src/dashboard/api/routers/artifacts.py`, `src/dashboard/api/routers/charter.py`, `src/dashboard/api/routers/dossier.py`, `src/dashboard/api/routers/features.py`, `src/dashboard/api/routers/glossary.py`, `src/dashboard/api/routers/health.py`, `src/dashboard/api/routers/kanban.py`, `src/dashboard/api/routers/lint.py`, `src/dashboard/api/routers/shutdown.py`, `src/dashboard/api/routers/static_mount.py`, `src/dashboard/api/routers/sync.py`, `src/dashboard/api/routers/diagnostics.py`, `tests/test_dashboard/test_deprecation_headers.py`
**Dependencies**: none

---

### WP04 — Governance wrap-up and OpenAPI snapshot

**Goal**: Final gate: regenerate the OpenAPI snapshot (all routes + tags now stable), confirm all arch tests pass in their non-vacuous state, author the ADR, update the ownership map, file the issue matrix, and update the migration runbook.

**Priority**: P1 (gated by WP02 + WP03).
**Independent test**: `pytest tests/test_dashboard/snapshots/ tests/architectural/ -q` exits 0; snapshot file matches the running app's `/openapi.json`; ADR, issue matrix, and ownership map committed.

**Subtasks**:
- [ ] T025 Full test run; confirm test_resource_models_have_links non-vacuous
- [ ] T026 Regenerate OpenAPI snapshot
- [ ] T027 Author ADR 2026-05-03-2
- [ ] T028 Update ownership map + manifest
- [ ] T029 Author issue-matrix.md
- [ ] T030 Update migration runbook

**Estimated prompt size**: ~380 lines
**Owned files**: `tests/test_dashboard/snapshots/openapi.json`, `architecture/2.x/adr/2026-05-03-2-resource-oriented-mission-api.md`, `architecture/2.x/05_ownership_map.md`, `architecture/2.x/05_ownership_manifest.yaml`, `kitty-specs/resource-oriented-mission-api-01KQQRF2/issue-matrix.md`, `docs/migration/dashboard-fastapi-transport.md`
**Dependencies**: WP02, WP03

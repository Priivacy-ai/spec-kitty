# Implementation Plan: Resource-Oriented Mission API and HATEOAS-LITE

**Branch**: `feature/650-dashboard-ui-ux-overhaul` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: `kitty-specs/resource-oriented-mission-api-01KQQRF2/spec.md`

## Summary

Add canonical resource-oriented endpoints anchored on `mission` as the noun (`/api/missions`, `/api/missions/{id}`, status, workpackages, per-WP detail), backed by the `MissionRegistry` from mission 112. Introduce `WorkPackageAssignment` and `ReviewEvidence` Pydantic models; make all five new resource models subclass `ResourceModel` to activate the HATEOAS-LITE arch test. Tag every existing `APIRouter` for OpenAPI grouping. Retrofit `/api/features` and `/api/kanban/{id}` with `Deprecation` + `Link` headers. Close out with ADR, ownership map update, and OpenAPI snapshot regen.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.115+, Pydantic v2, `src/dashboard/services/registry.py` (MissionRegistry, MissionRecord, WorkPackageRecord, LaneCounts — frozen dataclasses)
**Storage**: Filesystem only — registry reads `kitty-specs/*/`; no database
**Testing**: pytest; `tests/test_dashboard/`, `tests/architectural/`; OpenAPI snapshot gate in CI
**Target Platform**: Linux/macOS server process; HTTP only (no ASGI upgrade needed in this mission)
**Project Type**: Python library + FastAPI application; single-source layout under `src/`
**Performance Goals**: Warm-cache p99 ≤ pre-mission `/api/features` p99 + 10%; `/api/missions/{id}/status` p99 ≤ 50 ms
**Constraints**: Zero new top-level Python dependencies; zero new `# type: ignore`; OpenAPI snapshot regenerated once at end of mission; `src/dashboard/` must not import from `specify_cli.dashboard.*`
**Scale/Scope**: ~150 missions in this repo; 1 Hz browser poll per tab; 6 work packages

## Charter Check

- ✅ Python 3.11+ — matches charter language requirement
- ✅ No new external dependencies — consistent with "minimal-footprint" directive
- ✅ Tests alongside implementation — consistent with testing requirements
- ✅ Architectural tests enforced in CI — consistent with DIR-001 / DIR-002
- ✅ ADR authored for significant design decisions — consistent with DIR-003
- ✅ No `specify_cli.dashboard.*` imports inside `src/dashboard/` — consistent with FR-010 boundary invariant from mission 111

## Project Structure

### Documentation (this feature)

```
kitty-specs/resource-oriented-mission-api-01KQQRF2/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (spec-kitty.tasks)
```

### Source Code (repository root)

```
src/dashboard/
├── api/
│   ├── models.py                    # + WorkPackageAssignment, ReviewEvidence, 5 ResourceModel subclasses
│   └── routers/
│       ├── missions.py              # NEW — /api/missions, /api/missions/{id}, /status, /workpackages, /workpackages/{wp_id}
│       ├── features.py              # UPDATED — Deprecation + Link headers on /api/features
│       ├── kanban.py                # UPDATED — Deprecation + Link headers on /api/kanban/{id}
│       └── *.py                     # UPDATED — tags=[...] on every APIRouter constructor
├── services/
│   └── registry.py                  # UPDATED — WorkPackageRecord gains claimed_at, blocked_reason fields
└── api/
    └── app.py                       # UPDATED — register missions router

architecture/2.x/adr/
└── 2026-05-03-2-resource-oriented-mission-api.md    # NEW

tests/
├── test_dashboard/
│   ├── snapshots/openapi.json        # UPDATED at WP06 (single regen)
│   └── test_missions_api.py          # NEW — endpoint coverage + _links shape
└── architectural/
    └── test_resource_models_have_links.py   # ACTIVATED (already present, vacuous until WP01)
```

## Work Package Design

### WP01 — Registry extension + Pydantic resource models

**Goal**: Extend `WorkPackageRecord` with the fields `WorkPackageAssignment` needs that the current record does not expose (`claimed_at`, `blocked_reason`). Define all new Pydantic v2 models (`WorkPackageAssignment`, `ReviewEvidence`, `MissionSummary`, `Mission`, `MissionStatus`, `WorkPackageSummary`, `WorkPackage`) in `src/dashboard/api/models.py` subclassing `ResourceModel`. This WP activates `tests/architectural/test_resource_models_have_links.py` (transitions from vacuous to enforcing).

**Key decisions**:
- `WorkPackageRecord` fields to add: `claimed_at: datetime | None`, `blocked_reason: str | None`. These are populated by reading `status.events.jsonl` in the registry's existing per-mission scan — the `claimed_at` is the `at` timestamp of the most recent `→ claimed` event; `blocked_reason` is the `reason` field of the most recent `→ blocked` event.
- `_links` hrefs are built server-side in router code (not in model constructors) using the canonical `mission_id` so links in list responses are stable.
- `review_evidence` in `WorkPackageAssignment` is populated only for WPs in `in_review`, `approved`, or `done` lanes; it is `None` for all other lanes.

**Dependencies**: None (foundational WP).

---

### WP02 — OpenAPI tag grouping (issue #958)

**Goal**: Add `tags=[...]` to every `APIRouter(...)` constructor in every file under `src/dashboard/api/routers/` so Swagger UI renders grouped routes. Single-line change per router file.

| Router file | Tag |
|-------------|-----|
| `features.py` | `kanban` (deprecated alias) |
| `kanban.py` | `kanban` |
| `missions.py` (new, WP03) | `missions` |
| `research.py` (if present) | `research` |
| `artifacts.py` → contracts/checklists | `contracts` / `checklists` |
| `charter.py` | `charter` |
| `dossier.py` | `dossier` |
| `glossary.py` | `glossary` |
| `health.py` | `health` |
| `diagnostics.py` | `health` |
| `sync.py` | `sync` |
| `shutdown.py` | `lifecycle` |

**Dependencies**: None — fully independent of WP01 and WP03–WP05.

---

### WP03 — Mission list and detail routers

**Goal**: Create `src/dashboard/api/routers/missions.py` with:
- `GET /api/missions` → list of `MissionSummary`
- `GET /api/missions/{mission_id}` → `Mission`

Both routes call `get_mission_registry()` Depends. `{mission_id}` resolves via the registry's `get_mission()` method (supports `mission_id`, `mid8`, `mission_slug`; returns 404 on miss, 409 on ambiguity). Register the router in `src/dashboard/api/app.py`.

**Dependencies**: WP01 (models must exist before the router can return typed responses).

---

### WP04 — Mission status and workpackage resource routers

**Goal**: Extend `src/dashboard/api/routers/missions.py` with:
- `GET /api/missions/{mission_id}/status` → `MissionStatus`
- `GET /api/missions/{mission_id}/workpackages` → `list[WorkPackageSummary]`
- `GET /api/missions/{mission_id}/workpackages/{wp_id}` → `WorkPackage`

All three use `get_mission_registry()`. The `{wp_id}` route returns 404 if the WP is not in the mission.

**Dependencies**: WP01 (models), WP03 (shared `get_or_404` helper and router file).

---

### WP05 — Deprecation alias headers

**Goal**: Retrofit `/api/features` (`src/dashboard/api/routers/features.py`) and `/api/kanban/{feature_id}` (`src/dashboard/api/routers/kanban.py`) with:
- `Deprecation: true` response header
- `Link: </api/missions>; rel="successor-version"` response header (for `/api/features`)
- `Link: </api/missions/{id}/status>; rel="successor-version"` response header (for `/api/kanban/{id}`)

Response body unchanged. The routes continue to work for the full deprecation window.

**Dependencies**: None — logically independent of WP01–WP04.

---

### WP06 — Governance wrap-up and snapshot regen

**Goal**: Final wrap-up gate for the mission:
1. Regenerate `tests/test_dashboard/snapshots/openapi.json` once (all new routes and tags are in place).
2. Run full test suite; confirm `test_resource_models_have_links.py`, `test_transport_does_not_import_scanner.py`, and `test_url_naming_convention.py` all pass.
3. Author `architecture/2.x/adr/2026-05-03-2-resource-oriented-mission-api.md`.
4. Update `architecture/2.x/05_ownership_map.md` and `05_ownership_manifest.yaml`; mark #957 and #958 done.
5. Author `kitty-specs/resource-oriented-mission-api-01KQQRF2/issue-matrix.md`.
6. Update `docs/migration/dashboard-fastapi-transport.md` with a short "Resource-oriented endpoints" section explaining the new URL structure and the one-release deprecation window.

**Dependencies**: WP01, WP02, WP03, WP04, WP05 (snapshot must reflect all changes).

## Dependency Graph

```
WP01 (models + registry extension)
  └──▶ WP03 (mission list/detail routers)
         └──▶ WP04 (status + WP routers)
                └──▶ WP06 (governance wrap-up)

WP02 (tag grouping)     ──┐
                          ├──▶ WP06
WP05 (deprecation aliases)┘
```

Lane parallelization:
- **Lane A**: WP01 → WP03 → WP04 → WP06
- **Lane B**: WP02 → WP05 (independent; merge into WP06)

## Complexity Tracking

No charter violations identified. All work fits within the existing `src/dashboard/` package boundary.

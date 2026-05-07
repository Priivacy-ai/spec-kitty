# Feature Specification: Resource-Oriented Mission API and HATEOAS-LITE

**Feature Slug**: `resource-oriented-mission-api-01KQQRF2`
**Mission ID**: `01KQQRF2ZKPQW1CT7H6BYTN5BG`
**Mission Type**: software-dev
**Created**: 2026-05-03
**Target Branch**: `feature/650-dashboard-ui-ux-overhaul`
**Parent epic**: [#645 — Stable Application API Surface (UI / CLI / MCP / SDK)](https://github.com/Priivacy-ai/spec-kitty/issues/645)
**Primary tracker**: [#957](https://github.com/Priivacy-ai/spec-kitty/issues/957) · **Secondary**: [#958](https://github.com/Priivacy-ai/spec-kitty/issues/958)

## Overview

The dashboard FastAPI surface currently exposes verb-shaped endpoints (`/api/features`, `/api/kanban/{id}`) that are holdovers from the legacy `BaseHTTPServer` era. No endpoint is tagged in the OpenAPI document, so Swagger UI renders a flat, unnavigable list. There is no single-workpackage endpoint, no formal ownership schema, and the codebase's canonical noun — **mission** — is absent from every URL.

Mission 112 (`mission-registry-and-api-boundary-doctrine-01KQPDBB`) delivered the `MissionRegistry`, three doctrine directives, and the HATEOAS-LITE paradigm — including a `ResourceModel` Pydantic base and a vacuous arch test (`test_resource_models_have_links.py`) waiting for subclasses. This mission materializes that infrastructure by shipping:

1. **Resource-oriented URLs** anchored on `mission` as the canonical noun (`/api/missions`, `/api/missions/{id}`, status, workpackages, per-WP detail).
2. **`WorkPackageAssignment`** — the formal contract for WP ownership, lane, assignee, and review evidence.
3. **HATEOAS-LITE materialization** — every new resource model subclasses `ResourceModel` and declares `_links`, activating the arch test from mission 112.
4. **OpenAPI tag grouping** — every `APIRouter` tagged so Swagger UI and ReDoc render routes grouped by domain.
5. **Deprecation aliases** — `/api/features` and `/api/kanban/{id}` retained for one release with `Deprecation` response headers pointing at the canonical URLs.

## Domain Language

| Term | Canonical meaning | Avoid |
|------|-------------------|-------|
| **mission** | A tracked unit of work; the canonical noun for this API surface. Identified by `mission_id` (ULID), `mid8` (first 8 chars), or `mission_slug`. | "feature", "project" |
| **work package (WP)** | A discrete deliverable within a mission, identified by `WP##`. | "task", "story" |
| **lane** | The current kanban state of a WP: `planned`, `claimed`, `in_progress`, `for_review`, `in_review`, `approved`, `done`, `blocked`, `canceled`. | "status", "state" (ambiguous) |
| **HATEOAS-LITE** | The subset hypermedia convention adopted by this project: every resource response includes `_links: {<rel>: {href: ...}}`. Not full HAL or JSON:API. | "HAL", "hypermedia" |
| **MissionRegistry** | The canonical service-layer entry point for reading mission and WP data. Landed in mission 112. | "scanner", "MissionScanService" |
| **ResourceModel** | The Pydantic v2 base class that marker-enforces `_links`; landed in mission 112. | |
| **deprecation alias** | An existing endpoint retained verbatim but emitting a `Deprecation` HTTP header; removed in a separate retirement mission. | "redirect", "compatibility shim" |

## User Scenarios & Testing

### Scenario 1 — Dashboard consumer fetching the mission list (P0)

A browser tab with `dashboard.js` polls `/api/missions` every second. The response contains `MissionSummary` objects, each with a `_links.self` href the UI can follow for the full mission detail without hardcoding URL patterns. The UI no longer calls `/api/features`; the deprecated alias continues to work during the transition window.

**Test**: `GET /api/missions` returns HTTP 200 with a JSON array; each item has `mission_id`, `mission_slug`, `friendly_name`, `lane_counts`, `weighted_percentage`, and a non-empty `_links.self`. Deprecated `GET /api/features` returns the same shape plus a `Deprecation` response header.

### Scenario 2 — Single-mission detail and status drill-down (P0)

An operator calls `GET /api/missions/01KQQRF2` (using `mid8`). The response includes the full `Mission` resource with `_links.self`, `_links.status`, and `_links.workpackages`. They follow `_links.status` to `GET /api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG/status` and receive lane counts and weighted percentage without fetching all missions.

**Test**: `GET /api/missions/{mid8}`, `GET /api/missions/{mission_id}`, and `GET /api/missions/{slug}` all resolve to the same mission. Ambiguous selector returns HTTP 409 with a structured error listing candidates.

### Scenario 3 — MCP tool fetching a single WP assignment (P1)

A future MCP tool calls `GET /api/missions/{id}/workpackages/WP03` to check whether the WP is claimed and by whom before dispatching an agent. The `WorkPackageAssignment` in the response tells the tool the current `lane`, `assignee`, and `claimed_at` without needing to read `status.events.jsonl` directly.

**Test**: `GET /api/missions/{id}/workpackages/{wp_id}` returns HTTP 200 with a `WorkPackage` resource including a non-null `assignment.wp_id` and the correct `lane`. Returns HTTP 404 for an unknown `wp_id`.

### Scenario 4 — API consumer navigating by OpenAPI tags (P1)

A developer opens `/docs` and sees route groups: `missions`, `research`, `contracts`, `charter`, etc. They click `missions` and see only the five mission/WP endpoints. They do not need to scroll through a flat list of 23+ routes.

**Test**: Every path in the `/openapi.json` response has at least one non-empty tag. Swagger UI renders the tag sections visually (Playwright or manual screenshot).

### Edge cases

- **Unknown mission selector**: `GET /api/missions/no-such-mission` → HTTP 404 with `{"detail": "Mission not found: no-such-mission"}`.
- **Ambiguous `mid8` collision**: `GET /api/missions/ABCD1234` where two missions share the same 8-char prefix → HTTP 409 with `MISSION_AMBIGUOUS_SELECTOR` error listing both candidates. No silent fallback.
- **WP not in mission**: `GET /api/missions/{id}/workpackages/WP99` where WP99 does not exist → HTTP 404.
- **Registry cold start**: First request after server boot triggers a full scan; subsequent requests within the TTL are served from cache. Response time is acceptable even on cold start.
- **Deprecated alias with Accept header**: clients that send `Accept: application/json` to `/api/features` receive the same JSON body as `/api/missions`, plus the `Deprecation` header.

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | `GET /api/missions` returns a list of `MissionSummary` resource objects. Each object includes `mission_id`, `mission_slug`, `mission_number` (null pre-merge), `friendly_name`, `mission_type`, `lane_counts: LaneCounts`, `weighted_percentage: float \| None`, and `_links: {self: Link, status: Link, workpackages: Link}`. Backed by `MissionRegistry.list_missions()`. | Proposed |
| FR-002 | `GET /api/missions/{id}` returns a full `Mission` resource. `{id}` resolves against `mission_id` first, then `mid8`, then `mission_slug` (via the registry's existing resolution logic). Includes all `MissionSummary` fields plus `mission_description`, `target_branch`, `created_at`, and `_links.self`, `_links.status`, `_links.workpackages`. Returns HTTP 404 for an unknown id; HTTP 409 with `MISSION_AMBIGUOUS_SELECTOR` error for an ambiguous `mid8`. | Proposed |
| FR-003 | `GET /api/missions/{id}/status` returns a `MissionStatus` resource with `lane_counts: LaneCounts`, `weighted_percentage: float \| None`, `current_phase: int`, `done_count: int`, `total_count: int`, and `_links.self`, `_links.mission`. Backed by `MissionRegistry.get_mission()`. | Proposed |
| FR-004 | `GET /api/missions/{id}/workpackages` returns a list of `WorkPackageSummary` resource objects. Each includes `wp_id`, `title`, `assignment: WorkPackageAssignment`, and `_links.self`, `_links.mission`. Backed by `MissionRegistry.list_work_packages()`. | Proposed |
| FR-005 | `GET /api/missions/{id}/workpackages/{wp_id}` returns a full `WorkPackage` resource. Includes all `WorkPackageSummary` fields plus `subtasks: list[SubtaskSummary]`, `dependencies: list[str]`, `prompt_ref: str \| None` (relative path to the WP prompt file if it exists), and `_links.self`, `_links.mission`, `_links.workpackages`. Returns HTTP 404 if the mission or WP is unknown. Backed by `MissionRegistry.get_work_package()`. | Proposed |
| FR-006 | A `WorkPackageAssignment` Pydantic v2 model is introduced in `src/dashboard/api/models.py` with fields: `wp_id: str`, `lane: str`, `assignee: str \| None`, `agent_profile: str \| None`, `role: str \| None`, `claimed_at: datetime \| None`, `last_event_id: str \| None`, `blocked_reason: str \| None`, `review_evidence: ReviewEvidence \| None`. | Proposed |
| FR-007 | A `ReviewEvidence` Pydantic v2 model is introduced in `src/dashboard/api/models.py` with fields: `reviewed_by: str`, `reviewed_at: datetime`, `verdict: Literal["approved", "rejected"]`, `notes: str \| None`. | Proposed |
| FR-008 | All five new resource models (`MissionSummary`, `Mission`, `MissionStatus`, `WorkPackageSummary`, `WorkPackage`) subclass `ResourceModel` (landed in mission 112) and declare `_links: dict[str, Link]`. This activates `tests/architectural/test_resource_models_have_links.py`, which must pass (green, non-vacuous) after this mission. | Proposed |
| FR-009 | `GET /api/features` and `GET /api/kanban/{feature_id}` are retained as deprecation aliases under the same FastAPI app. Each alias route handler emits a `Deprecation` HTTP response header with the value `true` and a `Link` header pointing at the canonical URL (e.g., `Link: </api/missions>; rel="successor-version"`). The response body is unchanged from pre-mission behaviour. | Proposed |
| FR-010 | Every `APIRouter` constructor in every file under `src/dashboard/api/routers/` is annotated with `tags=[...]`. The tag set applied to each router matches the domain grouping table: `missions` (new mission/WP routers), `kanban` (existing kanban + deprecated `/api/features` alias), `research`, `contracts`, `checklists`, `charter`, `dossier`, `glossary`, `health`, `sync`, `lifecycle`. | Proposed |
| FR-011 | Swagger UI at `/docs` renders routes grouped by tag. Verification is a manual screenshot or Playwright test confirming that tag accordion sections are present and each tag contains only its own routes. | Proposed |
| FR-012 | The OpenAPI snapshot at `tests/test_dashboard/snapshots/openapi.json` is regenerated once at the end of the mission (not per WP). The CI snapshot gate (`test_openapi_snapshot.py` or equivalent) must pass on the final commit. | Proposed |
| FR-013 | New router files under `src/dashboard/api/routers/` for the mission/WP endpoints call `get_mission_registry()` Depends and never import from `specify_cli.dashboard.scanner`, `specify_cli.scanner`, or any `*scanner*` module path. The existing `tests/architectural/test_transport_does_not_import_scanner.py` must remain green. | Proposed |
| FR-014 | All new URL paths conform to the resource-noun convention validated by `tests/architectural/test_url_naming_convention.py`. Action-shaped URLs (`/api/sync/trigger`, `/api/shutdown`) remain in the existing allowlist; no new action-shaped URLs are added. | Proposed |
| FR-015 | An ADR `architecture/2.x/adr/2026-05-03-2-resource-oriented-mission-api.md` is authored and committed. It records: the decision to adopt resource-oriented naming, alternatives considered (keeping `/api/features` as canonical, verb-shaped action endpoints), the deprecation timeline and trigger for alias retirement, and the future MCP exposure pathway. | Proposed |
| FR-016 | The ownership map `architecture/2.x/05_ownership_map.md` Dashboard slice is updated to list the new mission/WP router files; `05_ownership_manifest.yaml` is updated correspondingly. Issues #957 and #958 are marked `done` in the Open Sub-tickets callout. | Proposed |
| FR-017 | `kitty-specs/resource-oriented-mission-api-01KQQRF2/issue-matrix.md` is authored listing issues #957 (resource-oriented endpoints), #958 (tag grouping), and their resolution status. | Proposed |

## Non-Functional Requirements

| ID | Attribute | Threshold | Status |
|----|-----------|-----------|--------|
| NFR-001 | `GET /api/missions` warm-cache p99 latency | ≤ pre-mission `GET /api/features` p99 + 10 % on the same machine (registry cache must not regress). Measured with `scripts/bench_registry_syscalls.py` from mission 112 (re-run post-mission). | Proposed |
| NFR-002 | `GET /api/missions/{id}/status` warm-cache p99 latency | ≤ 50 ms (single-mission cache lookup, no full scan). | Proposed |
| NFR-003 | Type-checking debt | Zero new `# type: ignore` directives added to `src/dashboard/api/models.py` or any new router file. | Proposed |
| NFR-004 | New top-level Python dependencies | Zero. Pydantic v2, `datetime`, and `typing` are already in-tree. | Proposed |
| NFR-005 | Test suite regression | All pre-existing dashboard, architectural, and daemon-gate tests pass after each WP merge. Zero new test failures attributable to this mission. | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | New router files must call `MissionRegistry` via `get_mission_registry()` Depends; direct scanner imports in transport-side modules are forbidden by `tests/architectural/test_transport_does_not_import_scanner.py`. | Proposed |
| C-002 | Deprecated aliases retain their existing URLs exactly; the alias route handlers emit `Deprecation` and `Link` headers but do not redirect. The response body must remain byte-equivalent to the pre-mission response for the same input. | Proposed |
| C-003 | The OpenAPI snapshot (`tests/test_dashboard/snapshots/openapi.json`) is regenerated once at the final WP, not per WP. Mid-mission snapshot drift is acceptable and expected. | Proposed |
| C-004 | `{id}` path parameters resolve via `MissionRegistry` selector logic: `mission_id` (ULID) first, then `mid8` (8-char prefix), then `mission_slug`. Ambiguous selectors return HTTP 409 with `MISSION_AMBIGUOUS_SELECTOR`; no silent fallback to the first match. | Proposed |
| C-005 | `_links` href values are server-relative paths (e.g. `/api/missions/01KQQRF2ZKPQW1CT7H6BYTN5BG`) not absolute URLs, so the dashboard works without knowledge of its external address. | Proposed |
| C-006 | The legacy `BaseHTTPServer` handler stack is not modified by this mission. Its retirement is tracked separately in the epic's sequencing. | Proposed |
| C-007 | `mission_number` is display-only metadata (`null` pre-merge); it is never used as an `{id}` path parameter or selector. | Proposed |

## Success Criteria

- An operator navigating `/docs` sees routes organized into named domain groups (missions, research, charter, etc.) rather than a flat list.
- A client that knows only a `mission_id` or `mission_slug` can reach any mission or WP detail through a single well-known entry point (`/api/missions`) without needing to know internal URL patterns.
- The HATEOAS-LITE architectural test (`test_resource_models_have_links.py`) transitions from vacuous (no subclasses) to enforcing (5 resource models verified), and passes in CI.
- `GET /api/features` and `GET /api/kanban/{id}` continue to work for clients that have not yet migrated, with machine-readable `Deprecation` headers signalling the transition.
- Warm-cache latency on `/api/missions` does not regress compared to `/api/features` (within 10 %).
- All pre-existing dashboard and architectural tests remain green.

## Key Entities

| Entity | Description | Source |
|--------|-------------|--------|
| `MissionSummary` | Lightweight list-view resource; includes lane counts and weighted progress. | New (this mission) |
| `Mission` | Full mission detail resource; includes all summary fields plus description and branch. | New (this mission) |
| `MissionStatus` | Lane counts + weighted percentage for a single mission; for polling. | New (this mission) |
| `WorkPackageSummary` | Lightweight WP list-view resource; includes assignment. | New (this mission) |
| `WorkPackage` | Full WP detail resource; includes subtasks, dependencies, prompt ref, assignment. | New (this mission) |
| `WorkPackageAssignment` | Ownership contract: lane, assignee, agent profile, review evidence. | New (this mission) |
| `ReviewEvidence` | Review outcome sub-model: reviewer, timestamp, verdict, notes. | New (this mission) |
| `ResourceModel` | Pydantic base that enforces `_links`; landed in mission 112. | Pre-existing |
| `Link` | `{href: str}` hypermedia link model; landed in mission 112. | Pre-existing |
| `MissionRegistry` | Canonical mtime-cached service-layer reader; landed in mission 112. | Pre-existing |
| `LaneCounts` | Lane-keyed WP count map; pre-existing in `src/dashboard/api/models.py`. | Pre-existing |

## Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| Mission 112 (`mission-registry-and-api-boundary-doctrine-01KQPDBB`) | Hard prerequisite | ✅ Merged |
| `MissionRegistry.list_missions()`, `get_mission()`, `list_work_packages()`, `get_work_package()` in `src/dashboard/services/registry.py` | Code prerequisite | ✅ Available |
| `ResourceModel` and `Link` in `src/dashboard/api/models.py` | Code prerequisite | ✅ Available |
| `get_mission_registry()` Depends helper in `src/dashboard/api/deps.py` | Code prerequisite | ✅ Available |
| `tests/architectural/test_resource_models_have_links.py` (vacuous, waiting for subclasses) | Arch test activated by this mission | ✅ Present |

## Assumptions

- `MissionRegistry.get_work_package()` returns enough data (lane, assignee, claimed_at, last_event_id, blocked_reason, review_evidence) to populate `WorkPackageAssignment` without a separate JSONL read per request. If the registry does not yet surface these fields, the registry interface is extended as part of this mission before the WP endpoint is wired up.
- `_links` hrefs are constructed server-side from the request's `{id}` parameter using the canonical `mission_id` (not `mid8` or slug), so links in list responses are stable regardless of how the list was fetched.
- The `Deprecation` header value `true` (per RFC 8594 draft) is sufficient signalling for the one-release transition window; a full `sunset` header is not required at this stage.
- The OpenAPI snapshot test already exists from the FastAPI migration mission; this mission updates the snapshot file, it does not create a new test.

## Out of Scope

- Removal of `/api/features` and `/api/kanban/{id}` (separate retirement mission, after at least one release with canonical URLs as default).
- Glossary and lint handler service extraction (#954, #955 — Mission C, parallel track).
- Async update transport (WebSocket / SSE — Step 5 of epic #645).
- Generated client tooling (Step 6 of epic #645).
- Changes to the legacy `BaseHTTPServer` stack.
- `WorkPackageAssignment` write/mutation endpoints; this mission is read-only.

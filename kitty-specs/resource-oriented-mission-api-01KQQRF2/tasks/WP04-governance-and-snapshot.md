---
work_package_id: WP04
title: Governance wrap-up and OpenAPI snapshot
dependencies:
- WP02
- WP03
requirement_refs:
- FR-012
- FR-015
- FR-016
- FR-017
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
agent: claude
history: []
agent_profile: curator-carla
authoritative_surface: architecture/2.x/
execution_mode: planning_artifact
model: claude-sonnet-4-6
owned_files:
- tests/test_dashboard/snapshots/openapi.json
- architecture/2.x/adr/2026-05-03-2-resource-oriented-mission-api.md
- architecture/2.x/05_ownership_map.md
- architecture/2.x/05_ownership_manifest.yaml
- kitty-specs/resource-oriented-mission-api-01KQQRF2/issue-matrix.md
- docs/migration/dashboard-fastapi-transport.md
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

Final gate for the mission. All routes and tag changes from WP01–WP03 are in place; this WP regenerates the OpenAPI snapshot, confirms all architectural tests pass in their enforcing (non-vacuous) state, and produces the governance artifacts: ADR, ownership map update, issue matrix, and migration runbook addendum.

## Branch Strategy

- **Planning base / merge target**: `feature/650-dashboard-ui-ux-overhaul`
- Depends on WP02 and WP03 — run: `spec-kitty agent action implement WP04 --agent claude`
- Execution workspace: Lane A worktree, after WP02 merges (WP03 from Lane B also merged first).

## Context

By the time this WP starts:
- `src/dashboard/api/routers/missions.py` exists with 5 routes.
- All `APIRouter(...)` constructors have `tags=[...]`.
- `/api/features` and `/api/kanban/{id}` emit `Deprecation` headers.
- All dashboard and architectural tests pass.
- The OpenAPI snapshot at `tests/test_dashboard/snapshots/openapi.json` is **stale** (it doesn't yet reflect the new routes or tags).

## Implementation Guide

### T025 — Full test run; confirm arch test non-vacuous

```bash
.venv/bin/python -m pytest tests/test_dashboard/ tests/architectural/ -q --timeout=120
```

Must exit 0. Pay special attention to:

```bash
.venv/bin/python -m pytest tests/architectural/test_resource_models_have_links.py -v
```

The output must show **at least 5 `ResourceModel` subclasses verified**. If it still reports "vacuous" or "0 subclasses", WP01 has not landed correctly — do not proceed until this is resolved.

---

### T026 — Regenerate OpenAPI snapshot

The snapshot test at `tests/test_dashboard/` (look for `test_openapi_snapshot.py` or similar) compares the running app's schema against `tests/test_dashboard/snapshots/openapi.json`. Regenerate it:

```bash
.venv/bin/python -c "
import json
from pathlib import Path
from dashboard.api.app import create_app

# create_app may require a project_dir argument — check its signature
# Pass '.' or the repo root as appropriate
app = create_app(Path('.'))
schema = app.openapi()
out = Path('tests/test_dashboard/snapshots/openapi.json')
out.write_text(json.dumps(schema, indent=2, sort_keys=True) + '\n')
print(f'Snapshot written: {out}')
print(f'Paths: {len(schema[\"paths\"])}')
"
```

After regeneration, run the snapshot test to confirm it passes:

```bash
.venv/bin/python -m pytest tests/test_dashboard/ -k "snapshot or openapi" -v
```

**Verification checklist**:
- [ ] `/api/missions` appears in the snapshot paths.
- [ ] `/api/missions/{mission_id}` appears.
- [ ] `/api/missions/{mission_id}/status` appears.
- [ ] `/api/missions/{mission_id}/workpackages` appears.
- [ ] `/api/missions/{mission_id}/workpackages/{wp_id}` appears.
- [ ] Every path has at least one tag in `"tags": [...]`.
- [ ] The `kanban` tag group contains `/api/features` and `/api/kanban/{feature_id}`.

---

### T027 — Author ADR

**File**: `architecture/2.x/adr/2026-05-03-2-resource-oriented-mission-api.md`

Follow the ADR format used in adjacent files (e.g., `2026-05-02-2-fastapi-openapi-transport.md`). Cover:

```markdown
# ADR 2026-05-03-2: Resource-Oriented Mission API and HATEOAS-LITE Materialization

**Date**: 2026-05-03
**Status**: Accepted
**Mission**: resource-oriented-mission-api-01KQQRF2
**Trackers**: #957, #958
**Epic**: #645

## Context

[Describe the current state: verb-shaped endpoints, no canonical `/api/missions` surface,
no per-WP endpoint, no OpenAPI tag grouping, vacuous HATEOAS-LITE arch test]

## Decision

Introduce resource-oriented endpoints anchored on `mission` as the canonical noun.
[Summarize the 5 new routes, WorkPackageAssignment, ResourceModel materialization,
tag grouping, and deprecation aliases]

## Alternatives Considered

1. Keep `/api/features` as the canonical URL — rejected because `mission` is the canonical
   noun across all CLI, ADRs, and spec-kitty identity model.
2. Rename existing routes without deprecation period — rejected because active consumers
   (dashboard.js polling at 1 Hz) would break immediately.
3. Separate OpenAPI tag grouping into its own mission — rejected because it is a one-line
   change per router and blocks no parallelism.

## Consequences

- Positive: stable, navigable API surface; HATEOAS-LITE arch test enforcing.
- Positive: Swagger/ReDoc now navigable by domain.
- Positive: MCP tools can discover the API via `/openapi.json` without hardcoding paths.
- Negative: `/api/features` and `/api/kanban/{id}` must be maintained for one release.

## Deprecation Timeline

`/api/features` and `/api/kanban/{feature_id}` emit `Deprecation: true` as of this mission.
A follow-up retirement mission removes them after at least one tagged release with the
canonical URLs as default.

## Future Work

- Async update transport (WebSocket/SSE) — depends on this mission's canonical URLs.
- Generated TypeScript client from OpenAPI — `openapi-typescript` path documented in
  `docs/migration/dashboard-fastapi-transport.md`.
- MCP adapter using the new endpoints as tool implementations.
```

Update `architecture/2.x/adr/README.md` index to add a row for this ADR.

---

### T028 — Update ownership map + manifest

**Files**: `architecture/2.x/05_ownership_map.md`, `architecture/2.x/05_ownership_manifest.yaml`

In `05_ownership_map.md`, find the **Dashboard** section. Update:
- Add `src/dashboard/api/routers/missions.py` to the router list.
- Note that `WorkPackageAssignment` and `ReviewEvidence` are new resource models.
- Mark issues **#957** and **#958** as `done` in the Open Sub-tickets callout.
- Reference this ADR and the HATEOAS-LITE paradigm.

Mirror the structural changes in `05_ownership_manifest.yaml`.

---

### T029 — Author issue-matrix.md

**File**: `kitty-specs/resource-oriented-mission-api-01KQQRF2/issue-matrix.md`

```markdown
# Issue Matrix: resource-oriented-mission-api-01KQQRF2

| Issue | Title | Status | WP |
|-------|-------|--------|----|
| #957 | Dashboard API: resource-oriented mission + workpackage endpoints | ✅ fixed | WP01, WP02 |
| #958 | Dashboard API: tag every operation in the OpenAPI document | ✅ fixed | WP03 |
| #645 | Epic: Stable Application API Surface | 🔄 in-progress | (parent) |
```

---

### T030 — Update migration runbook

**File**: `docs/migration/dashboard-fastapi-transport.md`

Add a new section after the existing content (or within the appropriate logical location):

```markdown
## Resource-Oriented Mission Endpoints (Mission B)

As of this mission, the canonical endpoints for mission and WP data are:

| Endpoint | Description |
|----------|-------------|
| `GET /api/missions` | List all missions |
| `GET /api/missions/{id}` | Single mission (by mission_id, mid8, or slug) |
| `GET /api/missions/{id}/status` | Lane counts + weighted progress |
| `GET /api/missions/{id}/workpackages` | WP list for a mission |
| `GET /api/missions/{id}/workpackages/{wp_id}` | Single WP detail |

### Deprecated aliases

`/api/features` and `/api/kanban/{feature_id}` continue to work but emit:
- `Deprecation: true`
- `Link: <canonical-url>; rel="successor-version"`

Clients should migrate before the retirement mission removes these aliases.

### HATEOAS-LITE navigation

Every resource response includes a `_links` block with relative hrefs:

```json
{
  "_links": {
    "self": { "href": "/api/missions/01KQQRF2..." },
    "status": { "href": "/api/missions/01KQQRF2.../status" },
    "workpackages": { "href": "/api/missions/01KQQRF2.../workpackages" }
  }
}
```

### MCP exposure pathway

The FastAPI surface at `/openapi.json` documents all routes with tags and schemas.
An MCP tool can call `GET /api/missions/{id}/workpackages/{wp_id}` to obtain a
`WorkPackageAssignment` (lane, assignee, claimed_at) without reading the filesystem directly.
See ADR `2026-05-03-2-resource-oriented-mission-api.md` for the full pathway.
```

## Definition of Done

- [ ] `pytest tests/test_dashboard/ tests/architectural/ -q` exits 0.
- [ ] `test_resource_models_have_links.py` reports ≥5 subclasses, non-vacuous.
- [ ] OpenAPI snapshot regenerated and snapshot test passes.
- [ ] Every path in snapshot has ≥1 non-empty tag.
- [ ] `/api/missions`, `/api/missions/{id}`, `/api/missions/{id}/status`, `/api/missions/{id}/workpackages`, `/api/missions/{id}/workpackages/{wp_id}` all appear in snapshot.
- [ ] ADR authored and referenced in `architecture/2.x/adr/README.md`.
- [ ] Ownership map updated; #957 and #958 marked done.
- [ ] `issue-matrix.md` present and complete.
- [ ] Migration runbook updated.

## Risks

- **Stale snapshot test**: If the snapshot test compares byte-for-byte and the snapshot was regenerated with a different JSON key order, the test may fail. Ensure `sort_keys=True` in the regen script matches whatever the snapshot test expects. Read the test first.
- **`create_app()` signature**: The factory may require `project_dir` or `project_token`. Check its signature in `src/dashboard/api/app.py` before calling it in the regen script.

# Issue Matrix: resource-oriented-mission-api-01KQQRF2

| Issue | Title | Status | WP(s) |
|-------|-------|--------|-------|
| [#957](https://github.com/Priivacy-ai/spec-kitty/issues/957) | Dashboard API: resource-oriented mission + workpackage endpoints (incl. WorkPackageAssignment schema) | ✅ fixed | WP01, WP02 |
| [#958](https://github.com/Priivacy-ai/spec-kitty/issues/958) | Dashboard API: tag every operation in the OpenAPI document for Swagger / ReDoc grouping | ✅ fixed | WP03 |
| [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645) | Epic: Stable Application API Surface (UI / CLI / MCP / SDK) | 🔄 in-progress (steps 3–4 done, steps 5–7 deferred) | (parent) |

## Resolution Notes

**#957** resolved by:
- `WorkPackageRecord` extended with `claimed_at` and `blocked_reason` (WP01, `src/dashboard/services/registry.py`)
- `WorkPackageAssignment`, `ReviewEvidence`, `MissionSummary`, `Mission`, `MissionStatus`, `WorkPackageSummary`, `WorkPackage` Pydantic models (WP01, `src/dashboard/api/models.py`)
- All 5 `ResourceModel` subclasses verified by `tests/architectural/test_resource_models_have_links.py`
- `GET /api/missions`, `GET /api/missions/{id}`, `GET /api/missions/{id}/status`, `GET /api/missions/{id}/workpackages`, `GET /api/missions/{id}/workpackages/{wp_id}` (WP02, `src/dashboard/api/routers/missions.py`)
- `/api/features` and `/api/kanban/{id}` retained as deprecated aliases with `Deprecation` + `Link` headers (WP03)

**#958** resolved by:
- `tags=[...]` added to every `APIRouter(...)` constructor in `src/dashboard/api/routers/` (WP03)

## Swagger UI Verification

Operator verification of `/docs` tag accordion groups: **required before release**.
Open the dashboard, navigate to `/docs`, confirm that route groups appear by domain
tag (`missions`, `kanban`, `research`, `contracts`, etc.). Record result here:

- [ ] Visual confirmation completed by: ___________________ on ___________________

# ADR: Resource-Oriented Mission API and HATEOAS-LITE Materialization

**Date**: 2026-05-03
**Status**: Accepted
**Mission**: `resource-oriented-mission-api-01KQQRF2`
**Trackers**: [#957](https://github.com/Priivacy-ai/spec-kitty/issues/957) · [#958](https://github.com/Priivacy-ai/spec-kitty/issues/958)
**Epic**: [#645 — Stable Application API Surface (UI / CLI / MCP / SDK)](https://github.com/Priivacy-ai/spec-kitty/issues/645)
**Follows**: ADR `2026-05-03-1-dashboard-mission-registry-and-cache.md` (MissionRegistry + doctrine, Mission 112)

## Context

After the FastAPI transport migration (Mission 111 + ADR `2026-05-02-2`) and the
MissionRegistry introduction (Mission 112 + ADR `2026-05-03-1`), the dashboard API
surface had three remaining structural gaps:

1. **Verb-shaped URLs**: The primary list endpoint was `/api/features` — a holdover
   from the legacy `BaseHTTPServer` era. The canonical noun across CLI, ADRs, status
   models, and the mission identity model (ADR `2026-04-09-1`) is **mission**, not
   "feature". Consumers calling `/api/features` are reading against a stale vocabulary.

2. **No per-resource endpoints**: Consumers had to fetch the entire mission list and
   filter client-side to find one mission's status or work-package detail. There were
   no endpoints at `/api/missions/{id}`, `/api/missions/{id}/status`, or
   `/api/missions/{id}/workpackages/{wp_id}`. A 1 Hz polling client needed to fetch
   ~150 missions to check the status of one.

3. **Vacuous HATEOAS-LITE enforcement**: Mission 112 introduced the `ResourceModel`
   Pydantic base and the arch test `test_resource_models_have_links.py`, but no
   production model subclassed `ResourceModel` yet. The arch test was vacuous (0
   subclasses verified). Consumers had no hypermedia links to navigate the API.

4. **No OpenAPI tag grouping**: All 23+ routes appeared as a flat, unordered list in
   Swagger UI and ReDoc. Consumers and codegen tools had no domain grouping to navigate
   by.

## Decision

Introduce a resource-oriented API surface anchored on **mission** as the canonical
noun, materialized on top of the `MissionRegistry` from Mission 112.

### New canonical endpoints

| Method | Path | Response model |
|--------|------|----------------|
| `GET` | `/api/missions` | `list[MissionSummary]` |
| `GET` | `/api/missions/{id}` | `Mission` |
| `GET` | `/api/missions/{id}/status` | `MissionStatus` |
| `GET` | `/api/missions/{id}/workpackages` | `list[WorkPackageSummary]` |
| `GET` | `/api/missions/{id}/workpackages/{wp_id}` | `WorkPackage` |

The `{id}` path parameter resolves via `MissionRegistry.get_mission()` using the
`mission_id` → `mid8` → `mission_slug` precedence defined in Mission 083. Ambiguous
`mid8` returns HTTP 409 with a `MISSION_AMBIGUOUS_SELECTOR` error; unknown returns
HTTP 404.

### HATEOAS-LITE materialization

All five new response models subclass `ResourceModel` and declare `_links: dict[str, Link]`.
Every resource response carries server-relative hrefs anchored to the canonical
`mission_id` (ULID), making them stable regardless of how the resource was fetched.
The arch test `test_resource_models_have_links.py` transitions from vacuous (0 subclasses)
to enforcing (5 subclasses verified).

### `WorkPackageAssignment` and `ReviewEvidence` contracts

`WorkPackageAssignment` is the formal ownership contract for a WP: lane, assignee,
`claimed_at`, `last_event_id`, `blocked_reason`, `review_evidence`. It is the natural
payload for any future MCP tool or external SDK that needs WP-level data without reading
`status.events.jsonl` directly.

### OpenAPI tag grouping (#958)

Every `APIRouter` constructor carries `tags=[...]`. Swagger UI and ReDoc render routes
grouped by domain (`missions`, `kanban`, `research`, `contracts`, `checklists`, `charter`,
`dossier`, `glossary`, `health`, `sync`, `lifecycle`, `static`).

### Deprecation aliases

`/api/features` and `/api/kanban/{feature_id}` are retained verbatim for one release
and emit `Deprecation: true` + `Link: <canonical>; rel="successor-version"` response
headers. Removal is a separate retirement mission.

## Alternatives Considered

1. **Keep `/api/features` as the canonical URL** — rejected. `mission` is the canonical
   noun throughout the codebase (CLI, ADRs, `mission_id` identity model). Keeping
   `/api/features` would perpetuate terminology drift and block the vocabulary clean-up
   that ADR `2026-04-09-1` established.

2. **Rename existing routes without a deprecation period** — rejected. `dashboard.js`
   polls `/api/features` at 1 Hz. An immediate rename would break every open browser
   tab. The one-release grace period costs one additional header per response; the
   operational risk of a hard cut-over costs much more.

3. **Ship OpenAPI tag grouping in a separate mission** — rejected. It is a one-line
   `tags=[...]` change per router file, adds no risk, and blocks no parallelism. Bundling
   it with the resource-oriented surface change produces a single coherent commit set.

4. **Embed `_links` construction in `ResourceModel` constructors** — rejected. Hrefs
   require server context (the canonical `mission_id`). Keeping href-building in the
   router layer keeps registry records transport-agnostic and reusable from CLI/MCP
   without importing FastAPI internals.

## Consequences

- **Positive**: consumers can navigate the full mission/WP hierarchy via `_links` without
  hardcoding URL patterns.
- **Positive**: Swagger UI and ReDoc are now navigable by domain tag.
- **Positive**: the HATEOAS-LITE arch test is enforcing; future `ResourceModel` subclasses
  must declare `_links` or CI fails.
- **Positive**: MCP tools can call `GET /api/missions/{id}/workpackages/{wp_id}` and get
  a `WorkPackageAssignment` without reading `status.events.jsonl` directly.
- **Negative**: `/api/features` and `/api/kanban/{id}` must be maintained for one release,
  adding two deprecated routes to the OpenAPI document.

## Deprecation Timeline

`/api/features` → `/api/missions` (list)
`/api/kanban/{id}` → `/api/missions/{id}/status` (status sub-resource)

Both deprecated aliases were introduced in the FastAPI migration mission and emit
`Deprecation: true` headers as of this mission. A follow-up retirement mission removes
them after at least one tagged release with the canonical URLs as default-on.

## Future Work

- **Async update transport** (Step 5 of #645): WebSocket or SSE push on the FastAPI
  surface. The canonical `/api/missions/{id}/status` endpoint is the natural polling
  target to replace with a subscription.
- **Generated TypeScript client**: the OpenAPI document at `/openapi.json` is the
  input for `openapi-typescript` or similar codegen. Path documented in
  `docs/migration/dashboard-fastapi-transport.md`.
- **MCP adapter**: each new endpoint is a thin FastAPI handler over a plain Python
  callable on `MissionRegistry`. Reusing it as an MCP tool definition requires ~10
  lines. See the worked example in ADR `2026-05-02-2`.
- **Alias retirement**: separate mission, sequenced after the next tagged release.

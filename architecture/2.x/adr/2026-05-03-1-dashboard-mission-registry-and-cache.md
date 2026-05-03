# ADR: Dashboard `MissionRegistry` Abstraction Between FastAPI Routers and the Filesystem

**Date**: 2026-05-03
**Status**: Proposed (mission tracked at [#956](https://github.com/Priivacy-ai/spec-kitty/issues/956))
**Mission**: TBD — to be filed under epic [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645)
**Replaces / refines**: ADR `2026-05-02-2-fastapi-openapi-transport.md` (which migrated transport but kept the per-request filesystem-walk strategy)

## Context

The FastAPI dashboard transport (mission `frontend-api-fastapi-openapi-migration-01KQN2JA`) replaced the legacy `BaseHTTPServer` + hand-rolled router stack with a typed FastAPI app, an auto-generated OpenAPI document, and a Pydantic model layer. The transport changed; the **backing strategy did not**. Every dashboard request — including the 1-Hz poll from `dashboard.js` — still triggers a full walk of `kitty-specs/*/`, opens every `meta.json`, reads every `status.events.jsonl`, and parses every `tasks/WP*.md`.

On a non-trivial spec-kitty project (the spec-kitty repo itself has ~144 missions today), a single open browser tab causes ~720 file `open()` syscalls per second. Multiple tabs multiply linearly. There is no caching layer, no observability hook, no read-through abstraction — `dashboard.js` polls, the FastAPI router invokes a scanner function, the scanner walks the disk, the response is built. Every request is independent.

The post-FastAPI engineering review surfaced this in [Finding 5 of `docs/implementation/2026-05-03-dashboard-api-review.md`](../../docs/implementation/2026-05-03-dashboard-api-review.md). The operator-stated goal is:

> Each dashboard lookup can be done using an API call, rather than using direct file access.

Read literally, this is already true: `dashboard.js` calls `/api/*` URLs only — it does not poke the filesystem. The substantive concern is the **server-side strategy**: the dashboard's API endpoints are thin wrappers around per-request filesystem scans, with no abstraction between the route handler and the file walker.

This ADR proposes the missing abstraction.

## Decision

Introduce two service-layer registries — `MissionRegistry` and `WorkPackageRegistry` — that sit between the FastAPI routers and the underlying scanner / file-reader code. The registries:

1. **Read the filesystem once per mtime change** for the relevant `kitty-specs/<slug>/` subtree, not once per request.
2. **Serve cached snapshots** for subsequent requests until the mtime changes.
3. Are the **only sanctioned call site** for `scan_all_features` / `scan_feature_kanban` / equivalent walkers — an architectural test forbids any FastAPI router from importing these directly.

FastAPI routers call `registry.list_missions()`, `registry.get_mission(id)`, `registry.list_work_packages(mission_id)`, etc. The registry handles cache lookup, mtime check, and file-walk-on-miss internally.

Cache invalidation is **mtime-based polling at a coarser cadence than the per-request 1-Hz client poll**:
- The registry keeps a per-mission cache entry keyed by the most recent mtime of `meta.json` + `status.events.jsonl` + `tasks/`.
- A cheap "is the cache stale?" check stats those three paths (3 syscalls vs ~720) on every read.
- A full re-scan happens only when at least one of the three has a newer mtime.

This is the minimum viable design. It is intentionally simpler than:
- An inotify-based watcher (added complexity; cross-platform support; operator visibility cost).
- A push-based update transport (out of scope here; covered by Step 5 of #645).

## Rationale

- **Avoids over-engineering**: mtime polling is portable, observable, and cheap. The 3-stat-call cost is bounded and predictable.
- **Single point of subscription for Step 5**: when WebSocket / SSE push lands, it subscribes to the registry's invalidation events instead of having every route re-implement push.
- **Single point for observability**: any future metrics (cache hit rate, scan latency, mission count) plug into the registry, not into each router.
- **Clean architectural boundary**: an architectural test forbids routers from importing the scanner directly. This makes the dependency direction inspectable and prevents future drift back to per-request walks.
- **Preserves existing FR-009 / NFR-007 invariants**: route handler bodies stay ≤ 15 lines; the registry call replaces the scanner call; nothing else changes at the route boundary.

## Consequences

- **`scan_all_features` / `scan_feature_kanban` move into a private call site**. Routers that previously imported them directly switch to `MissionRegistry`. The shimmed scanner module (`src/specify_cli/scanner.py`) can stay for backward compatibility but is downgraded to "internal use only" in its docstring.
- **Test fixtures need an mtime-bump helper**. Tests that create a fixture project, then mutate it, then expect a fresh scan, must call `os.utime(...)` to force a cache miss. Helper provided in the registry's test module.
- **One new architectural test** forbids `from specify_cli.dashboard.scanner import` (or equivalent) inside `src/dashboard/api/routers/*.py`. Catches future drift in CI.
- **Cache entries live in process memory**. The dashboard is a single-process Uvicorn app on localhost; sharing across processes is not a goal. If the dashboard is ever multi-worker, the cache is per-worker; mtime polling still keeps them eventually consistent.
- **The OpenAPI surface is unchanged by this ADR**. Resource-oriented endpoints (`/api/missions/{id}/...`) are a separate ADR / mission tracked at [#957](https://github.com/Priivacy-ai/spec-kitty/issues/957).

## Rejected Alternatives

- **Per-request filesystem walk (status quo)**: this is what we are replacing. It is the simplest possible design; it does not scale beyond a few dozen missions and it is hostile to the 1-Hz client poll.
- **Inotify / fsnotify-based watcher**: more efficient than polling, but adds a runtime dependency (e.g. `watchdog`) and a watcher thread that the Uvicorn process must manage. The operational cost is real; the gain over coarse mtime polling is small for our scale.
- **Database-backed cache (SQLite)**: persists across process restarts, but adds a schema, a migration path, and a write-behind story. Out of scope for a local dev tool.
- **Push update transport (WebSocket / SSE)**: this is what Step 5 of #645 will eventually do. The registry is its prerequisite. We do not skip the registry to go straight to push, because (a) the push transport needs a single point of invalidation to subscribe to, and (b) older clients that do not speak WebSocket still need a working REST surface.

## Future Work

When the registry lands, the following downstream work becomes cheap:

- **Step 5 of #645** (async update transport): subscribe a WebSocket / SSE endpoint to the registry's invalidation events. `dashboard.js` drops the 1-Hz poll and uses an event subscription instead.
- **Step 6 of #645** (generated client support): the registry's typed return shapes feed directly into `openapi-typescript` codegen.
- **Resource-oriented endpoints** ([#957](https://github.com/Priivacy-ai/spec-kitty/issues/957)): `/api/missions/{id}/status`, `/api/missions/{id}/workpackages`, `/api/missions/{id}/workpackages/{wp_id}` all read from the registry. The new endpoints are a thin re-shaping of registry data, not new walks.
- **Future MCP exposure**: an MCP adapter wraps the registry's typed methods as MCP tools. The route handler bodies remain plain Python callables; the registry is the shared substrate.

## Cross-references

- Engineering log: [`docs/implementation/2026-05-03-dashboard-api-review.md`](../../../docs/implementation/2026-05-03-dashboard-api-review.md).
- Tracker: [#956](https://github.com/Priivacy-ai/spec-kitty/issues/956).
- Companion mission tracker: [#957](https://github.com/Priivacy-ai/spec-kitty/issues/957) — resource-oriented endpoints (depends on this ADR landing first).
- Companion CI / OpenAPI cleanup: [#958](https://github.com/Priivacy-ai/spec-kitty/issues/958) — tag grouping.
- Parent epic: [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645).
- Ownership map cross-link: `architecture/2.x/05_ownership_map.md` § Dashboard.

# ADR: Dashboard Services Move to `specify_cli.missions` (Phase B Service Placement Remediation)

**Date**: 2026-05-07
**Status**: Accepted (mission `dashboard-services-domain-migration-01KR151P` shipped 2026-05-07)
**Mission**: `dashboard-services-domain-migration-01KR151P` — Phase B of epic [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645)
**Refines**: ADR `2026-05-02-1-dashboard-service-extraction.md` (Phase A — extracted services from `dashboard.api` into `dashboard.services`)
**Refines**: ADR `2026-05-03-1-dashboard-mission-registry-and-cache.md` (introduced `MissionRegistry` with mtime-keyed cache)
**Companion to**: [`docs/implementation/2026-05-03-dashboard-api-review.md`](../../../docs/implementation/2026-05-03-dashboard-api-review.md)

## Context

Phase A of epic #645 (mission `mission-registry-and-api-boundary-doctrine-01KQPDBB`, ADR
`2026-05-02-1`) extracted the four mission-domain service classes —
`MissionRegistry`, `MissionScanService`, `ProjectStateService`, and
`SyncService` — out of FastAPI route handlers and into a dedicated
`src/dashboard/services/` package. Routers were updated to depend on these
services exclusively (no more `from specify_cli.scanner import ...` inside
transport modules). That mission also added the C-009 architectural rule
forbidding `specify_cli/*` and `kernel/*` from importing `dashboard.*`.

Phase A succeeded on the *vertical* dependency arrow (transport → service)
but introduced a new *horizontal* problem: the four domain services were
**physically** placed under `src/dashboard/`, in the same package tree as the
FastAPI presentation layer. This:

1. **Inverted the conceptual ownership.** The mission registry, the kanban
   scanner, the project-state aggregator, and the sync trigger are
   *domain* concerns. They have nothing to do with HTTP, FastAPI, OpenAPI,
   browsers, or presentation. Yet they lived in `dashboard.services.*`.
2. **Made the C-009 rule structurally fragile.** Any new caller in
   `specify_cli/` who wanted to use `MissionRegistry` (a perfectly
   reasonable re-use case — e.g. CLI commands, doctor checks, future
   IDE adapters) was *forced* to import `dashboard.services.registry`,
   tripping the C-009 boundary or requiring per-file allow-listing.
3. **Tightly coupled cache regressions to the dashboard.** The P1 (two-level
   cache) and P2 (strong-reference WP store) bugs investigated under this
   epic were domain-cache bugs. Pinning their fixes to a `dashboard/`
   path made cross-surface re-use awkward and the test surface unclear.

The pre-mission analysis [`docs/implementation/2026-05-03-dashboard-api-review.md`](../../../docs/implementation/2026-05-03-dashboard-api-review.md)
called out this misplacement as the highest-leverage cleanup remaining
before the API surface stabilises for 3.2.0.

## Decision

Move the four mission-domain services from `src/dashboard/services/` to
`src/specify_cli/missions/`, and reverse the dependency arrow at the
package boundary:

| Module | Old canonical home | New canonical home |
|---|---|---|
| `MissionRegistry` (+ `MissionRecord`, `WorkPackageRecord`, `LaneCounts`, `WorkPackageRegistry`) | `dashboard.services.registry` | `specify_cli.missions.registry` |
| `MissionScanService` (+ `parse_kanban_path`) | `dashboard.services.mission_scan` | `specify_cli.missions.scan_service` |
| `ProjectStateService` | `dashboard.services.project_state` | `specify_cli.missions.project_state` |
| `SyncService` (+ `SyncTriggerResult`, `_build_trigger_request`) | `dashboard.services.sync` | `specify_cli.missions.sync_service` |

The four `dashboard.services.*` modules become **thin re-export shims**
registered in `architecture/2.x/shim-registry.yaml` with
`removal_target_release: 3.2.0`, owner mission
`dashboard-services-domain-migration-01KR151P`, and
`grandfathered: false`. The shims will be deleted in Phase C, after 3.2.0
ships and any third-party importers have had a release window to migrate.

In addition:

- **C-009 enforcement is tightened.** The previous `test_no_upstream_dashboard_imports`
  exempted the entire `specify_cli/dashboard/` subtree and
  `specify_cli/cli/commands/dashboard.py` via path-skip blocks. Both
  exemptions are removed. Three specific bridge files
  (`specify_cli/dashboard/server.py`, `specify_cli/dashboard/api_types.py`,
  `specify_cli/dashboard/handlers/features.py`) remain on an explicit
  allow-list with documented rationale; everything else must obey C-009.
  A synthetic-violation fixture
  (`test_boundary_check_catches_dashboard_import`) proves the AST scan
  fires on a planted `from dashboard.*` import.
- **P1 + P2 regression tests are pinned to the canonical location.**
  `tests/specify_cli/missions/test_registry_cache.py` exercises both:
  (a) `list_missions()` reflects an appended `status.events.jsonl` event
  on the same registry instance (the two-level mtime-keyed cache fix), and
  (b) `workpackages_for(mission_id)` returns the *same Python object* on
  repeated calls (the strong-reference store that replaced the broken
  `WeakValueDictionary`). These tests would have caught the 2026-05-03
  cache misses at review time.

## Rationale

Moving the services under `specify_cli/missions/` aligns physical layout
with conceptual ownership: missions are a `specify_cli` domain concept,
not a dashboard-presentation concept. The dashboard is one consumer; CLI
commands, doctor checks, future MCP adapters, and future IDE integrations
are equally legitimate consumers. By placing the canonical home in the
domain package, we:

- Allow any in-tree caller to import `MissionRegistry` without crossing
  C-009 or requiring per-file allow-listing.
- Decouple cache lifetime from dashboard process lifetime. The
  `MissionRegistry` is now a domain object usable by long-lived CLI
  invocations, scripted automation, and the SaaS-side reconciler.
- Make `dashboard/` a true presentation layer: it imports from the domain,
  it does not own the domain.
- Reduce the C-009 allow-list from "the whole specify_cli/dashboard
  subtree" to a hand-listed three-file bridge surface, which is
  enforceable, reviewable, and shrinkable.

The reverse-direction shims are accepted as a one-release migration cost
to avoid churning external callers (legacy adapters, documentation,
example code) on the same release that lands the move. The shim registry
gives us deterministic deletion timing and a CI gate
(`spec-kitty doctor shim-registry`) that fails when a `removal_target_release`
ships without the shim being deleted.

## Consequences

### Positive

- C-009 is structurally tighter; new violations cannot hide behind a
  package-wide skip rule.
- `MissionRegistry` and friends are re-usable across surfaces (CLI,
  dashboard, doctor, MCP, automation) without architectural workarounds.
- P1 + P2 regression tests now live next to the code they protect, so
  future refactors of the cache get clear, fast feedback.
- The shim-registry entries are visible in `spec-kitty doctor shim-registry`
  and force a follow-up before 3.2.0 GA.

### Negative / costs

- One release window (3.2.0a → 3.2.0) carries duplicate import paths.
  Documented in the shim registry; deletion is tracked by the doctor gate.
- Any out-of-tree consumer importing `dashboard.services.*` (third-party
  scripts, internal tools) must update to `specify_cli.missions.*` before
  3.2.0 GA. The shim emits no runtime warning today; if this proves
  insufficient, a `DeprecationWarning` can be added in a follow-up
  without changing the import surface.
- `specify_cli.missions` becomes the de-facto domain hub. Future
  refactors that want to split it (e.g. a separate `specify_cli.scan`
  package) need their own ADR.

### Neutral

- Frontend, OpenAPI, and FastAPI route surfaces are unchanged — the move
  is internal. The `/api/v1/missions/*` contract is unaffected.

## Phase C plan

Phase C (post-3.2.0) deletes the four `dashboard.services.*` shim files,
removes the corresponding entries from `architecture/2.x/shim-registry.yaml`,
and confirms `spec-kitty doctor shim-registry` reports zero overdue
shims. Acceptance criteria for Phase C:

1. `git ls-files src/dashboard/services/` returns nothing (the directory
   no longer exists, or contains only an empty `__init__.py` slated for
   the same removal).
2. `tests/architectural/test_dashboard_boundary.py` still passes; the
   allow-list is unchanged or further narrowed.
3. The mission-services regression-test suite still passes from its
   canonical `tests/specify_cli/missions/` home.
4. `spec-kitty doctor shim-registry` reports the four entries as `REMOVED`
   (or they are pruned from the YAML once removal is confirmed shipped).

If a third-party caller surfaces a hard dependency on
`dashboard.services.*` between 3.2.0a and 3.2.0 GA, Phase C may be split
into a 3.3.0 deletion with `extension_rationale` recorded in the registry.

## Relationship to #645

Epic #645 (API Surface Completion) frames the dashboard's transport,
service, registry-cache, and presentation work as a single arc culminating
in a stable 3.2.0 dashboard API. Within that arc:

- ADR `2026-05-02-1-dashboard-service-extraction.md` — Phase A — extracted
  services from FastAPI handlers but placed them under `dashboard/`.
- ADR `2026-05-02-2-fastapi-openapi-transport.md` — Phase A — replaced
  `BaseHTTPServer` with FastAPI + auto-generated OpenAPI.
- ADR `2026-05-03-1-dashboard-mission-registry-and-cache.md` — introduced
  the mtime-keyed two-level cache and the strong-reference WP store.
- ADR `2026-05-03-2-resource-oriented-mission-api.md` — moved the public
  contract to resource-oriented `/api/v1/missions/*` URLs.
- **This ADR (Phase B)** — fixes the service-placement misstep from
  Phase A and tightens C-009.

After Phase B + C, epic #645's architectural debt is paid down and the
3.2.0 dashboard surface is structurally stable: presentation under
`src/dashboard/`, domain under `src/specify_cli/missions/`, and a thin
allow-listed bridge surface in between.

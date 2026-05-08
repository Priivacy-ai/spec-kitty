# Architectural Assessment: API Service Placement
## Should Domain Services Live Inside Their Domain Modules?

**Author**: Architect Alphonso
**Date**: 2026-05-04
**Parent initiative**: [Stable Application API Surface (May 2026)](./README.md)
**Parent epic**: [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645)
**Status**: Advisory — input for Mission C and successor missions

---

## 1 — The Question

The user put it directly:

> "Would placing the different API entrypoints and domain services inside their
> respective modules not make more sense — cfr. the DDD / domain-based doctrine artefacts?"

The short answer is **yes, for services; no, for transport adapters**. This document
explains the distinction, surfaces the evidence in the current codebase, and
recommends a target placement that closes the tension before it compounds further.

---

## 2 — Current State

The FastAPI migration (mission `frontend-api-fastapi-openapi-migration-01KQN2JA`)
and the registry mission (`mission-registry-and-api-boundary-doctrine-01KQPDBB`)
produced the following layout:

```
src/
  dashboard/
    api/
      routers/          ← HTTP transport adapters (FastAPI route bodies)
      models.py         ← Pydantic response DTOs
      deps.py           ← FastAPI Depends helpers
    services/
      registry.py       ← MissionRegistry + MissionRecord (canonical reader)
      mission_scan.py   ← MissionScanService (kanban assembly)
      project_state.py  ← ProjectStateService
      sync.py           ← SyncService
    api_types.py        ← TypedDict wire shapes (shim re-exports specify_cli version)

  specify_cli/
    glossary/           ← Glossary domain logic (seed files, conflicts, scopes)
    status/             ← Status / lane domain (event log, reducer, transitions)
    charter_lint/       ← Lint / decay-watch domain logic
    charter/            ← Charter domain logic
    cli/commands/
      dashboard.py      ← CLI --json flag (imports from dashboard.services.registry)
```

The `dashboard.services.*` modules were deliberately placed in the `dashboard`
package during the migration because they emerged from extracting logic out of
the old `BaseHTTPRequestHandler` subclasses. They are described in their own
docstrings as "Pydantic-free so CLI / MCP / SDK consumers can depend on them
without pulling Pydantic." That self-description contains the architectural
contradiction: a module inside `dashboard` is already Pydantic-free specifically
*so that non-dashboard consumers can use it*. That's a signal that it does not
belong in `dashboard`.

---

## 3 — The Core Tension

### 3.1 Importing direction

The CLI command `src/specify_cli/cli/commands/dashboard.py` already imports:

```python
from dashboard.services.registry import MissionRegistry
from dashboard.services.registry import MissionRecord
```

This means `specify_cli` (the main CLI package) depends on `dashboard` (the web
app package). The dependency arrow points **upward from domain to presentation
layer** — the reverse of what DDD and the existing layer-rule test prescribe.
The current `tests/architectural/test_layer_rules.py` enforces:

```
kernel ← doctrine ← charter ← specify_cli
```

The `dashboard` package sits *outside* this enforced chain. There is no test
that prevents `specify_cli` from importing `dashboard.*`, so the inverted
dependency exists today and will silently grow as more CLI subcommands need
mission or WP data.

### 3.2 Glossary and lint are not dashboard concerns

The pending Mission C work (#954 glossary, #955 lint) will create
`src/dashboard/services/glossary.py` and `src/dashboard/services/lint.py`.
Both services will call into `specify_cli.glossary.*` and read
`.kittify/lint-report.json` respectively. Neither piece of logic is a
*dashboard* concern — it is a **glossary domain concern** and a **lint domain
concern** that happens to be exposed over HTTP. Placing them in `dashboard/services/`
repeats the same misclassification already made for `MissionRegistry`.

### 3.3 The "stable retrieval surface" goal is wider than the dashboard

The initiative's stated goal is a retrieval surface that *all* consumers —
dashboard UI, CLI, future MCP adapter, future SDK — can use. A service layer
locked inside `dashboard/services/` is not available to those consumers
without an awkward cross-package import or duplication. A service layer located
in `specify_cli/<domain>/` (or a dedicated `src/missions/` sibling package)
is naturally available to every Python consumer regardless of transport.

---

## 4 — Recommended Target Structure

Apply the **Ports and Adapters** pattern (Hexagonal Architecture). The boundary
is drawn between *application/domain services* and *transport adapters*.

```
src/
  specify_cli/                   ← Domain + application services
    missions/                    ← NEW: mission query services (replaces dashboard/services/mission_scan + registry)
      registry.py                ←   MissionRegistry, MissionRecord (moved here)
      scan_service.py            ←   MissionScanService (moved here)
    glossary/
      service.py                 ← NEW: GlossaryService (extracted for #954)
    charter_lint/
      service.py                 ← NEW: LintService (extracted for #955)
    status/                      ← already canonical for status events

  dashboard/
    api/
      routers/                   ← Thin HTTP adapters; import from specify_cli.*
      models.py                  ← Pydantic DTOs (HTTP-specific, stay here)
      deps.py                    ← FastAPI Depends (HTTP-specific, stay here)
    api_types.py                 ← TypedDict shim (retain until shim retirement)
```

### What moves

| Current location | Target location | Rationale |
|---|---|---|
| `dashboard/services/registry.py` | `specify_cli/missions/registry.py` | Domain identity — not HTTP |
| `dashboard/services/mission_scan.py` | `specify_cli/missions/scan_service.py` | Domain query service |
| `dashboard/services/project_state.py` | `specify_cli/missions/project_state.py` | Domain query service |
| `dashboard/services/sync.py` | `specify_cli/missions/sync_service.py` | Domain coordination, not HTTP |
| (planned) `dashboard/services/glossary.py` | `specify_cli/glossary/service.py` | Glossary domain |
| (planned) `dashboard/services/lint.py` | `specify_cli/charter_lint/service.py` | Lint domain |

### What stays

| Location | Reason |
|---|---|
| `dashboard/api/routers/` | HTTP transport — legitimately presentation-layer |
| `dashboard/api/models.py` | Pydantic DTOs are HTTP/OpenAPI artefacts |
| `dashboard/api/deps.py` | FastAPI Depends plumbing |
| `dashboard/api_types.py` | TypedDict shim pending retirement |

### What changes in routing modules

After the move, every FastAPI router imports from `specify_cli.*` instead of
`dashboard.services.*`. Because `DIRECTIVE_API_DEPENDENCY_DIRECTION` already
forbids routers from importing the scanner directly, this is a safe lateral
move — the routers already delegate to a service; we are only changing *which
package* that service lives in.

The architectural test `test_transport_does_not_import_scanner.py` should be
extended (or a companion test added) to also assert:

> No module under `src/dashboard/api/routers/` imports directly from
> `dashboard.services.*` (i.e., services are not re-imported via the old path
> once moved).

---

## 5 — Sequencing Recommendation

This is a non-trivial package rename, and the `MissionRegistry` is already in
production use across routers, the CLI, and the shim. A big-bang move carries
regression risk. The recommended sequence:

### Phase A — New domain services alongside Mission C (low risk)

Mission C (#954 + #955) will create *new* service objects. Place them in
`specify_cli/glossary/service.py` and `specify_cli/charter_lint/service.py`
from the start rather than in `dashboard/services/`. No existing code is
moved; the routers import the new services from their canonical domain homes.
This proves the pattern with zero migration risk.

### Phase B — Migrate `MissionRegistry` and companions (follow-up mission)

A dedicated mission moves `dashboard/services/registry.py`,
`mission_scan.py`, `project_state.py`, and `sync.py` into
`specify_cli/missions/`. Shims (re-exports) are left in `dashboard/services/`
with `removal_release` set in `shim-registry.yaml`. The architectural test
is updated to enforce the new canonical import path. The CLI command
`dashboard.py` is updated to import from `specify_cli.missions.registry`.

### Phase C — Shim retirement (one release after Phase B)

`dashboard/services/` shims are deleted. The architectural test removes the
shim allowance. `dashboard/services/` becomes an empty package and is
removed.

---

## 5a — Addendum: DTO Co-location and One-Way Dependency Direction (2026-05-04)

*Added following user architectural review of the draft spec.*

The original assessment focused on where **services** live. A further refinement
applies to **data transfer objects (DTOs)** — the TypedDicts and Pydantic models
that describe service return shapes and HTTP response bodies.

### The problem with centralised DTOs

`src/dashboard/api_types.py` currently centralises all TypedDicts, including
domain-specific shapes like `GlossaryHealthResponse`, `GlossaryTermRecord`, and
`DecayWatchTileResponse`. If `GlossaryService` (in `specify_cli/glossary/`) is to
return `GlossaryHealthResponse`, it must import that type from `dashboard/api_types.py`
— which means `specify_cli` imports from `dashboard`. This is the same inverted
dependency the service-placement section identifies, now manifesting at the type level.

### The rule

> **DTOs used as return types of a domain service must be defined inside that
> service's domain module.** `dashboard/api` may import from domain modules; domain
> modules must never import from `dashboard/`.

This is the Ports and Adapters boundary stated at the type level, not just the
service level.

### Practical split for Mission C

| Type | Current home | Target home | Rationale |
|---|---|---|---|
| `GlossaryHealthResponse` | `dashboard/api_types.py` | `specify_cli/glossary/types.py` | Return type of `GlossaryService.get_health()` |
| `GlossaryTermRecord` | `dashboard/api_types.py` | `specify_cli/glossary/types.py` | Return element of `GlossaryService.get_terms()` |
| `DecayWatchTileResponse` | `dashboard/api_types.py` | `specify_cli/charter_lint/types.py` | Return type of `LintService.get_decay_watch_tile()` |
| Pydantic `GlossaryHealthResponse` | `dashboard/api/models.py` | stays | HTTP-transport artefact; `dashboard/api` imports from domain module |
| Pydantic `GlossaryTermRecord` | `dashboard/api/models.py` | stays | Same |
| Pydantic `DecayWatchTileResponse` | `dashboard/api/models.py` | stays | Same |
| `ArtifactInfo`, `ErrorResponse`, `HealthResponse`, etc. | `dashboard/api_types.py` | `src/kernel/api_types.py` (this mission, FR-019) | Cross-cutting, no single domain owner |
| `KanbanTaskData`, `KanbanStats`, `KanbanResponse` | `dashboard/api_types.py` | `src/specify_cli/status/api_types.py` (this mission, FR-019) | Domain-correlated with WP status |
| `MissionRecord`, `MissionContext`, `WorktreeInfo`, `WorkflowStatus` | `dashboard/api_types.py` | `src/specify_cli/missions/api_types.py` (this mission, FR-019) | Domain-correlated with mission management |

All callers of the moved TypedDicts — FastAPI routers, Pydantic model definitions in
`dashboard/api/models.py`, and the legacy `BaseHTTPRequestHandler` handlers — update
their imports to the new locations in the same mission. The moved definitions are
deleted from `dashboard/api_types.py` with no shim left behind. Once all moves are
complete `dashboard/api_types.py` is deleted (or contains only explicitly justified
dashboard-presentation-only types).

### Updated dependency diagram

```
kernel/api_types.py         ← ErrorResponse, HealthResponse, ArtifactInfo, SyncInfo, …
    ↑
specify_cli/glossary/types.py   ← GlossaryHealthResponse, GlossaryTermRecord
specify_cli/charter_lint/types.py  ← DecayWatchTileResponse
specify_cli/status/api_types.py    ← KanbanTaskData, KanbanStats, KanbanResponse
specify_cli/missions/api_types.py  ← MissionRecord, MissionContext, WorktreeInfo, WorkflowStatus
    ↑
specify_cli/glossary/service.py    ← GlossaryService (imports from .types)
specify_cli/charter_lint/service.py ← LintService (imports from .types)
    ↑
dashboard/api/routers/glossary.py  ← thin HTTP adapter (imports from specify_cli.glossary.*)
dashboard/api/routers/lint.py      ← thin HTTP adapter (imports from specify_cli.charter_lint.*)
dashboard/api/models.py            ← Pydantic DTOs (HTTP-only; may import from specify_cli.*)
```

`dashboard/api_types.py` is deleted once all migrations are complete (or retains only
justified dashboard-presentation-only types, listed and approved in `research.md`).

### Architectural test extension

The existing `test_dashboard_boundary.py` should gain a complementary assertion:

> No module under `src/specify_cli/` or `src/kernel/` imports from `src/dashboard/`.

This closes the blind spot identified in Section 7 (Risk 2) and enforces the
one-way dependency direction at CI level for the full module tree.

---

## 6 — Impact on the Current Mission Spec

The spec created in this session
(`kitty-specs/api-surface-completion-services-aliases-async-01KQSXDA`) covers
Mission C (glossary + lint extraction), alias retirement, Step 5 (async
transport), and Step 6 (TypeScript codegen). In light of this assessment:

- **Mission C service placement**: The glossary and lint services created for
  issues #954 and #955 should target `specify_cli/glossary/service.py` and
  `specify_cli/charter_lint/service.py` respectively. The FastAPI routers
  import from those domain locations.

- **Mission C DTO placement (domain-specific)**: `GlossaryHealthResponse`, `GlossaryTermRecord`,
  and `DecayWatchTileResponse` are moved from `dashboard/api_types.py` to
  `specify_cli/glossary/types.py` and `specify_cli/charter_lint/types.py`
  respectively (see §5a). All callers update their imports; the definitions are
  deleted from `dashboard/api_types.py` (no shim). Encoded as FR-016, FR-017, C-009.

- **Mission C DTO placement (cross-cutting → kernel)**: All remaining TypedDicts in
  `dashboard/api_types.py` are migrated to either `src/kernel/api_types.py` (truly
  cross-cutting: `ErrorResponse`, `HealthResponse`, `ArtifactInfo`, `SyncInfo`, etc.)
  or their respective domain module (`specify_cli/status/`, `specify_cli/missions/`).
  `dashboard/api_types.py` is deleted when empty. Encoded as FR-019, C-010.

- **Mission C acceptance criteria**: The architectural test
  `test_dashboard_boundary.py` is extended to assert no module in
  `specify_cli/` or `kernel/` imports from `dashboard/` (§5a — architectural
  test extension). This closes the layer-rule blind spot.

- **Phase B is a separate mission**: The existing `MissionRegistry` move is
  explicitly out of scope for the current spec. A follow-up issue should be
  filed after Mission C ships.

---

## 7 — Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Import chain breakage during `MissionRegistry` move | HIGH | Shim re-exports in `dashboard/services/`; `shim-registry.yaml` entry; CI must be green before shim retirement |
| Architectural test blind spot: `specify_cli` → `dashboard` direction never enforced | MEDIUM | File a TODO in `test_layer_rules.py` now; enforce in Phase B |
| Mission C services land in wrong place if Phase A recommendation is ignored | MEDIUM | Encode canonical target paths in the spec FR and acceptance criteria; reviewer checks import paths |

---

## 8 — Open Questions for the Mission Spec

These items need explicit answers in the spec before the plan phase:

1. **Package name for mission services**: Should the mission query services live
   in `specify_cli/missions/` (a new sibling to `specify_cli/status/`,
   `specify_cli/glossary/`, etc.) or directly in `specify_cli/` as flat modules?
   Preference: `specify_cli/missions/` to group the bounded context cleanly.
   *Deferred to Phase B mission spec.*

2. **Scope boundary of Phase A**: ~~Should the current mission spec explicitly
   forbid creating any new service in `dashboard/services/`, or leave that as
   an advisory note?~~ **Resolved**: Encoded as hard constraint C-002 in the
   spec. Encoded as C-009 for the DTO dependency direction. Reviewer can gate
   on both.

3. **DTO placement for cross-cutting types**: `ArtifactInfo`, `ErrorResponse`,
   `HealthResponse` etc. — **Resolved**: Scope extended per stakeholder direction
   (2026-05-04). All remaining `dashboard/api_types.py` types migrate to `kernel/`
   or their domain module in this mission (FR-019, C-010). The research phase will
   produce the definitive per-type categorisation. `dashboard/api_types.py` is
   deleted when empty.

---

*— Architect Alphonso, 2026-05-04*
*Handoff to: Planner Priti (sequencing), Implementer Ivan (execution)*

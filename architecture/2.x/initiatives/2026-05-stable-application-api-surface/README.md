# Initiative: Stable Application API Surface (May 2026)

**Owner role**: Architect Alphonso (this assessment); subsequent missions sequenced by Planner Priti.
**Date**: 2026-05-03
**Parent epic**: [#645 — Frontend Decoupling and Application API Platform](https://github.com/Priivacy-ai/spec-kitty/issues/645)
**Status**: Architectural assessment — proposed for execution

This initiative captures the architectural posture for spec-kitty's next dashboard / API arc. It cross-references all open `dashboard`-labelled tickets, the existing ADRs, the existing layer-rule enforcement, and the gaps in our doctrine around RESTful API design. It does **not** schedule the work — that is Planner Priti's responsibility. It does identify a recommended **epic rescope** for #645 (flagged, not executed).

---

## 1 — Open ticket landscape

10 open tickets carry the `dashboard` label as of 2026-05-03. They cluster into four logical families:

| Family | Tickets | Theme |
|--------|---------|-------|
| **Backbone & API surface** (this initiative's primary focus) | [#645 (epic)](https://github.com/Priivacy-ai/spec-kitty/issues/645), [#956](https://github.com/Priivacy-ai/spec-kitty/issues/956), [#957](https://github.com/Priivacy-ai/spec-kitty/issues/957), [#958](https://github.com/Priivacy-ai/spec-kitty/issues/958) | Decouple retrieval from filesystem; stable API; resource-oriented URL surface; OpenAPI grouping |
| **Service-layer extractions** (FR-007 follow-ups) | [#954](https://github.com/Priivacy-ai/spec-kitty/issues/954), [#955](https://github.com/Priivacy-ai/spec-kitty/issues/955) | Glossary, lint extracted from handler-layer logic into `dashboard.services.*` |
| **UX surface** (parallel epic) | [#650 (epic)](https://github.com/Priivacy-ai/spec-kitty/issues/650), [#767](https://github.com/Priivacy-ai/spec-kitty/issues/767), [#667](https://github.com/Priivacy-ai/spec-kitty/issues/667) | Design system; dropdown grouping; URL routing |
| **Adjacent / future** | [#648](https://github.com/Priivacy-ai/spec-kitty/issues/648) | Static site generation (children of a different epic, #651) |

**Observation 1 — The two epics live in parallel, not in series.** #645 is "stable application API"; #650 is "shared UI/UX design system". A consumer of #650 needs the API surface that #645 produces, but #650 is fundamentally a frontend / design-token concern that does not block #645. Sequencing them in series would block #650 unnecessarily.

**Observation 2 — The Backbone & API surface family has a clean dependency chain.** #956 (registry + cache) is the foundation; #957 (resource-oriented endpoints) layers on top; #958 (tag grouping) is independent and can ship anytime. No cycles.

---

## 2 — Cross-reference with existing architecture

### What's already in place (good)

| Concern | Mechanism |
|---------|-----------|
| **Package boundary enforcement** | `tests/architectural/test_layer_rules.py` uses `pytestarch` to enforce `kernel ← doctrine ← charter ← specify_cli`. ADR `2026-03-27-1` documents the rationale. |
| **Per-subsystem boundary tests** | `test_dashboard_boundary.py` (FR-010), `test_dossier_sync_boundary.py`, `test_status_sync_boundary.py`, `test_events_tracker_public_imports.py`, `test_retrospective_events_boundary.py`, `test_shared_package_boundary.py`. Mature pattern. |
| **Handler-purity enforcement** | `test_fastapi_handler_purity.py` AST-scans router bodies for forbidden `JSONResponse(...)` writes. |
| **Shim governance** | `architecture/2.x/shim-registry.yaml` + `test_unregistered_shim_scanner.py`; new shims must be registered with `removal_release`. |
| **ADR rhythm** | Recent ADRs (2026-04 / 2026-05) follow a clean Context / Decision / Rationale / Consequences / Rejected Alternatives shape. Index lives at `architecture/2.x/adr/README.md`. |

### What's missing (the gaps this initiative addresses)

| Gap | Severity | Evidence |
|-----|----------|----------|
| **No directive on RESTful API design** | HIGH | `grep -rln "REST\|HATEOAS\|hypermedia" src/doctrine/` returns only tutorial / guideline text, no codified directive or paradigm. The FastAPI mission shipped without an authoritative checklist for what "good API" means. |
| **No directive on dependency direction at the API boundary** | HIGH | The general layer-rule test exists but does not codify "transport may not import from backbone directly; only from service layer". The dashboard's per-request scanner walks (Finding 5 of [`docs/implementation/2026-05-03-dashboard-api-review.md`](../../../docs/implementation/2026-05-03-dashboard-api-review.md)) are technically architecturally legal today. |
| **No paradigm naming "stable retrieval surface"** | MEDIUM | The CLI command `spec-kitty dashboard --json` calls `build_mission_registry(project_root)` directly from the scanner (see `src/specify_cli/cli/commands/dashboard.py:59`). The dashboard's FastAPI calls the same scanner. **Two transports, two readers, same data, no shared service contract.** |
| **No HATEOAS / link-relation pattern in responses** | MEDIUM | Current responses are flat JSON. A consumer that fetches `/api/missions/{id}` cannot discover the URL of its `workpackages` collection without out-of-band knowledge of the URL scheme. |
| **No deprecation-cycle convention for API URLs** | LOW | The OpenAPI stability contract at `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/contracts/openapi-stability.md` covers schema drift but not URL-renames (e.g. `/api/features` → `/api/missions` — Finding 2 of the engineering log). |

### Two-entrypoint problem (the substantive architectural risk)

Today there are at least **three** independent readers of the same `kitty-specs/*/` data:

1. **Dashboard FastAPI** — `src/dashboard/api/routers/features.py` → `MissionScanService` → `scanner.scan_all_features`.
2. **Dashboard CLI flag** — `src/specify_cli/cli/commands/dashboard.py:59` (`--json` mode) → `scanner.build_mission_registry` directly.
3. **Per-router internal calls** — e.g. `routers/glossary.py` opens `.kittify/doctrine/graph.yaml` directly (transport-only migration, see [#954](https://github.com/Priivacy-ai/spec-kitty/issues/954)).

These readers serve **different shapes** of the same underlying data. No test enforces that they agree. A bugfix to the scanner that changes one reader's output but not another's would land silently. This is the canonical "passing test, failing system" failure mode the mission-review skill warns about.

The user's stated goal — *"multiple entrypoints directing to the same domain/business layer services"* — is the correct architectural response. The substantive work is:

- a single canonical `MissionRegistry` that is the **only** sanctioned reader (resolves #956);
- transport-side adapters (FastAPI routers, CLI commands, future MCP tools) call the registry, never the scanner;
- an architectural test enforces this at CI level.

---

## 3 — Recommended doctrine additions

The architectural assessment surfaces three doctrine gaps. Each warrants a small artefact filed alongside the next execution mission.

### 3.1 New directive: `DIRECTIVE_API_DEPENDENCY_DIRECTION`

**Rule**: Any module under `src/dashboard/api/routers/` or `src/specify_cli/cli/commands/` that exposes a retrieval entry point (HTTP route, CLI subcommand, MCP tool) MUST consume mission / WP / artifact data exclusively via the canonical service-layer interface (`dashboard.services.registry.MissionRegistry` once #956 lands; today: the existing `MissionScanService` and equivalents).

**Forbidden imports inside transport modules** (enforced by an AST-walking architectural test, mirroring `test_fastapi_handler_purity.py`):
- `from specify_cli.dashboard.scanner import ...`
- `from specify_cli.scanner import ...` (current shim)
- direct `Path(...).rglob(...)` or `open(...)` inside route bodies / CLI command bodies

**Allowed**:
- Imports of typed service classes from `dashboard.services.*`
- Imports of Pydantic models from `dashboard.api.models`
- File I/O confined to the service layer, where it can be cached / observed

### 3.2 New directive: `DIRECTIVE_REST_RESOURCE_ORIENTATION`

**Rule**: Public HTTP endpoints follow resource-oriented naming. A path is named for the **noun** (the resource) and the HTTP method names the **verb**. Operations on a single resource live under `/<collection>/{id}`; nested collections live under `/<collection>/{id}/<sub-collection>`.

**Examples**:
- ✅ `GET /api/missions` (collection) / `GET /api/missions/{id}` (item) / `GET /api/missions/{id}/workpackages` (sub-collection).
- ❌ `GET /api/features` (verb-shaped historical name; Finding 2 of the engineering log).
- ❌ `GET /api/sync/trigger` (verb in URL) — acceptable as a documented **action** endpoint, but should be tagged `actions` so it's clearly a non-resource URL.

Deprecation cycle: a renamed URL retains the old path for one release with a `Deprecation` HTTP header per RFC 8594. The OpenAPI snapshot test gates the rename.

### 3.3 New paradigm: `HATEOAS-LITE`

**Rule**: Resource responses include a `_links` block with the canonical URL of every related resource the consumer might navigate to. Consumers do not need out-of-band knowledge of the URL scheme; they follow links.

**Example**:
```json
{
  "mission_id": "01KQN2JA...",
  "mission_slug": "frontend-api-fastapi-openapi-migration-01KQN2JA",
  "lane_counts": {"done": 6},
  "_links": {
    "self": {"href": "/api/missions/01KQN2JA..."},
    "status": {"href": "/api/missions/01KQN2JA.../status"},
    "workpackages": {"href": "/api/missions/01KQN2JA.../workpackages"},
    "kanban-deprecated": {"href": "/api/kanban/01KQN2JA..."}
  }
}
```

#### Why "lite" — rationale (decided 2026-05-03)

We add only the `_links` convention. We do **not** adopt full HAL (`_embedded`, curies, link templates) and we do **not** adopt JSON:API (resource objects keyed by `type` / `id`, sparse fieldsets, included compound documents).

Reasoning:

1. **Scope is local-first.** The dashboard is a localhost-bound developer tool. The audience is the developer's own browser, the spec-kitty CLI, and (eventually) an MCP adapter — none of which are public clients with high-stakes evolution constraints.
2. **Minimum viable discoverability.** The substantive value of hypermedia for our consumers is "follow links instead of hard-coding URL templates". `_links` delivers that. The rest of HAL / JSON:API is plumbing for problems we don't have (third-party client SDKs, sparse-fieldset bandwidth optimisation, paginated compound documents).
3. **Forward compatibility.** `_links` is a strict subset of what HAL accepts. Any consumer that learns to read `_links` today will read it from a future HAL document tomorrow without code change. The migration path is additive, not breaking.
4. **Architectural-test cost is bounded.** A test that asserts "`_links` exists and is shaped correctly" is ~30 LOC of AST work. A test that validates a full HAL document against the spec is a separate dependency we don't need yet.

#### Future migration path (when triggered)

We graduate from HATEOAS-LITE to full **HAL** (or, if the consumer set demands it, **JSON:API**) when **any** of these triggers fires:

| Trigger | Why it forces the upgrade |
|---------|---------------------------|
| First public / external SDK consumer | External clients benefit from `_embedded` to avoid round-trips and from curies to namespace links |
| First paginated collection where the client needs included sub-resources in one round-trip | `_embedded` (HAL) or `included` (JSON:API) becomes load-bearing |
| First multi-tenant / public deployment where bandwidth cost matters | JSON:API's sparse fieldsets pay off |
| First case where a consumer needs to discover *operations* (state transitions), not just *links* | We adopt the `actions` / `operations` extension (HAL-FORMS or JSON:API operations) |

When any trigger fires, file a follow-up ADR that records the trigger, the chosen target (HAL vs JSON:API), and the migration plan. The expected migration shape:

1. Add the new fields (`_embedded` for HAL; `data` / `included` for JSON:API) **alongside** existing `_links`. Both are valid for the deprecation period.
2. Update the marker `ResourceModel` and the architectural test to require the new fields.
3. Update the OpenAPI snapshot.
4. Retain `_links` as an alias for one release (HAL accepts it natively; JSON:API requires translation).

The rule today is enforced by a small architectural test that asserts every Pydantic response model that represents a resource (subclass of a marker `ResourceModel`) declares a `_links` field of the correct shape. The test signature is forward-compatible: extending it to also require `_embedded` later is additive.

---

## 4 — Recommended enforcement (architectural tests)

Three new tests, each ~30 LOC, file alongside the next mission:

| Test | What it asserts | File |
|------|-----------------|------|
| `test_transport_does_not_import_scanner.py` | No file under `src/dashboard/api/routers/` or `src/specify_cli/cli/commands/dashboard.py` imports from `specify_cli.scanner` or `specify_cli.dashboard.scanner` directly. Catches the "two-entrypoint" regression at CI. | `tests/architectural/` |
| `test_resource_models_have_links.py` | Every Pydantic class subclassing `dashboard.api.models.ResourceModel` declares a `_links: dict[str, Link]` field. Enforces HATEOAS-LITE. | `tests/architectural/` |
| `test_url_naming_convention.py` | Every path in the published OpenAPI `paths` either matches the resource-noun convention OR is registered in a small allow-list (`actions:`) for action-shaped URLs (`/api/sync/trigger`, `/api/shutdown`). Catches verb-shaped URL drift. | `tests/architectural/` |

These tests do not require any new dependencies; they reuse the existing AST + JSON tooling.

---

## 5 — Cross-reference matrix: tickets ↔ architecture

| Ticket | What it ships | Architecture impact | Doctrine touched |
|--------|---------------|---------------------|------------------|
| [#956](https://github.com/Priivacy-ai/spec-kitty/issues/956) | `MissionRegistry` + cache | Closes the per-request-FS-walk gap; foundation for the dependency-direction directive | DIRECTIVE_API_DEPENDENCY_DIRECTION (test enforcing single reader) |
| [#957](https://github.com/Priivacy-ai/spec-kitty/issues/957) | Resource-oriented endpoints + `WorkPackageAssignment` | Realises DIRECTIVE_REST_RESOURCE_ORIENTATION; introduces `_links` blocks (HATEOAS-LITE) | DIRECTIVE_REST_RESOURCE_ORIENTATION + HATEOAS-LITE paradigm |
| [#958](https://github.com/Priivacy-ai/spec-kitty/issues/958) | OpenAPI tag grouping | Improves the spec's discoverability; orthogonal to the dependency-direction work | None new |
| [#954](https://github.com/Priivacy-ai/spec-kitty/issues/954) | Glossary service extraction | Makes glossary fit DIRECTIVE_API_DEPENDENCY_DIRECTION | Same directive (extends compliance) |
| [#955](https://github.com/Priivacy-ai/spec-kitty/issues/955) | Lint service extraction | Same as #954 | Same |
| [#767](https://github.com/Priivacy-ai/spec-kitty/issues/767) | Dropdown grouping | UX-only (epic #650) | None |
| [#667](https://github.com/Priivacy-ai/spec-kitty/issues/667) | URL routes + slash command | Frontend routing concern (epic #650) | None |
| [#648](https://github.com/Priivacy-ai/spec-kitty/issues/648) | Static site generation | Different epic (#651) | None |

---

## 6 — Epic-level recommendation (FLAGGED — requires user approval)

#645's title is **"Epic: Frontend Decoupling and Application API Platform"**. The body talks about "frontend platform" and "frontend consumers." But the substantive work as it now sequences is **broader** than frontend decoupling:

- The CLI also reads from the same data through a different entry point (`build_mission_registry`).
- A future MCP adapter (per the FastAPI mission's Future Work § and ADR `2026-05-02-2-fastapi-openapi-transport.md`) would also need a stable retrieval surface.
- An external SDK (Step 6 of the existing #645 sequencing) consumes the same surface.

The architecturally accurate framing is **"Stable Application API Surface for Mission and Work-Package Retrieval"** — the consumer set is plural (UI, CLI, MCP, SDK), not just frontend.

### Recommended rescope (for user approval — NOT executed)

- **Rename** #645 from `Epic: Frontend Decoupling and Application API Platform` → `Epic: Stable Application API Surface (UI / CLI / MCP / SDK)`.
- **Update** the epic body's "Goals" section to add: "expose a single stable retrieval surface that all spec-kitty consumers (dashboard UI, CLI commands, future MCP adapter, future external SDKs) consume; enforce the single-entry-point invariant via architectural test".
- **Keep** the current Sequencing list (Steps 1–7); it remains accurate. Add a new Step 0: "codify the directives and architectural tests that guard the single-entry-point invariant".

This is a **terminology + scope clarification**, not a strategic redirect. The work in #956/#957/#958 already moves in this direction. The rename makes the destination obvious to anyone reading the epic cold.

If approved, the rename is a 5-minute edit (title + body); no code change.

---

## 7 — Boundary check (architect's lane)

Architect Alphonso's `avoidance_boundary` is "Direct code implementation, routine bug fixes, project management". This initiative document:

- ✅ Defines architectural posture and recommended directives / paradigms — in lane.
- ✅ Identifies tests that would enforce the architecture — in lane (recommendation, not implementation).
- ✅ Cross-references existing tickets to the architecture — in lane.
- ✅ Flags an epic rescope for user approval — in lane (handoff to project owner).
- ❌ Does NOT schedule any mission, decompose any work into WPs, or estimate effort — that is **Planner Priti's** lane.
- ❌ Does NOT write the directives, tests, or registry code — that is **Implementer Ivan's** lane (or whoever the planner assigns).

**Handoff to**: Planner Priti (next agent in the user's sequence).

**Handoff content**:
1. This initiative document — the architectural assessment.
2. The engineering log at `docs/implementation/2026-05-03-dashboard-api-review.md` — the per-finding evidence.
3. The three child tickets (#956, #957, #958) — the executable scope.
4. The flagged rescope of #645 — pending user approval.

---

## 8 — Open questions (for the planner / user)

1. **Should the rescope of #645 happen before or after the next mission lands?** Either is valid. Doing it first makes the mission name align cleanly; doing it after avoids a context-switch.
2. **Is HATEOAS-LITE acceptable, or do we want full HAL / JSON:API?** Lite is recommended for the local-dashboard scope; full HAL is overkill but not wrong.
3. **Should the new directives ship in the next mission or as a standalone "doctrine update" mission?** Bundling them with #956 keeps the directives close to their first enforcement; a separate doctrine mission lets them ship faster but risks the "directive without a test" anti-pattern.

These are the planner's calls; this document records them as the open decisions, not as architectural prescriptions.

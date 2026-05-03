# Functional Ownership Map

| Field     | Value                                                                                                                              |
|-----------|------------------------------------------------------------------------------------------------------------------------------------|
| Status    | Active                                                                                                                             |
| Date      | 2026-04-18                                                                                                                         |
| Mission   | [functional-ownership-map-01KPDY72](../../kitty-specs/functional-ownership-map-01KPDY72/spec.md)                                   |
| Manifest  | [05_ownership_manifest.yaml](./05_ownership_manifest.yaml)                                                                         |
| Exemplar  | Mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880`                                                        |
| Direction | [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461)                     |

> **Terminology**: This document uses **Mission** (not "feature") and **Work Package** (not "task") per the repository's terminology canon in `AGENTS.md`. All downstream extraction PRs must follow the same convention.

---

## How to use this map

### Audience A — Extraction-PR Author

**Goal**: Prepare a PR that extracts a slice (e.g. glossary, runtime, lifecycle) to its canonical package without missing any obligation.

**Procedure**:

1. **Locate the slice entry** — open this map and find the H2 for the slice you are extracting.
2. **Read the required fields in order**:
   - `current_state` — list the exact files you will move.
   - `canonical_package` — the target package; use this as the destination path.
   - `adapter_responsibilities` — keep these in `src/specify_cli/` (the CLI shell). Do not move them.
   - `shims` — for each entry, create the shim file at `path` that re-exports from `canonical_import`. Record the `removal_release`.
   - `seams` — for each seam sentence, verify the seam still works after the move (typically a single test at the seam boundary).
   - `extraction_sequencing_notes` — confirm the prerequisites for this slice are landed.
3. **For the runtime slice only**: also honour `dependency_rules`. Add an import-graph test that asserts `may_call` / `may_be_called_by` hold.
4. **Confirm the slice entry in the PR description** — copy the slice's H2 from the map into the PR description and tick every field off. If a field is deferred, name the follow-up tracker.

**Worked example — Glossary extraction (mission #613)**:

- `current_state`: `src/specify_cli/glossary/` (14 modules).
- `canonical_package`: `src/glossary/`.
- `adapter_responsibilities`: CLI argument parsing and Rich rendering for `spec-kitty glossary *` commands stays in `src/specify_cli/cli/commands/glossary.py`.
- `shims`: one shim at `src/specify_cli/glossary/` with `canonical_import: glossary`, `removal_release: 3.4.0`.
- `seams`: doctrine registers a glossary runner via `kernel.glossary_runner.register()`; mission execution reads via `get_runner()` (resolved by ADR `2026-03-25-1`).
- `extraction_sequencing_notes`: depends on the architectural-tests and deprecation-scaffolding ACs in #613 and #615 landing first.
- PR moves all 14 modules to `src/glossary/`, adds the shim, ticks every field off in the PR description.

---

### Audience B — Reviewer

**Goal**: Reject extraction PRs that silently skip obligations or place code in the wrong package.

**Procedure**:

1. Open the PR and read its description.
2. Open this map and find the slice entry the PR claims to target.
3. For each required field in the slice entry: confirm the PR delivers it, or confirm the PR names a follow-up tracker, or request changes.
4. Verify **Mission / Work Package** canon — no "feature/task" language in the PR description or commit messages.
5. Verify the CHANGELOG entry exists if the slice had a shim removal.
6. For the runtime slice only: confirm `dependency_rules` have a corresponding test.

**Worked example — Runtime extraction PR review (mission #612)**:

- PR claims: "extracts runtime to `src/runtime/`".
- Reviewer checks `dependency_rules.may_call: [charter_governance, doctrine, lifecycle_status, glossary]` — PR adds an import-graph test covering these four.
- Reviewer checks `may_be_called_by: [cli_shell]` — PR adds the reverse assertion.
- Reviewer checks `adapter_responsibilities` — CLI commands under `src/specify_cli/cli/commands/` that delegate to runtime stay in place.
- Reviewer checks `extraction_sequencing_notes` — PR confirms architectural-tests AC in #612, import-graph-enforcement AC in #612, and #615 (deprecation scaffolding) are all in place.
- If every field is accounted for, approve. Otherwise, request changes naming the specific missing field.

---

### Manifest-driven tooling

Third-party tools (CI checks, the shim registry in mission #615, future scripts) parse `05_ownership_manifest.yaml` directly. A typical consumer pattern:

```python
import yaml
from pathlib import Path

manifest = yaml.safe_load(Path("architecture/2.x/05_ownership_manifest.yaml").read_text())
runtime = manifest["runtime_mission_execution"]
may_call = runtime["dependency_rules"]["may_call"]
# assert import-graph compliance
```

---

## CLI Shell

| Field                        | Value                                                                                       |
|------------------------------|---------------------------------------------------------------------------------------------|
| `canonical_package`          | `src/specify_cli/cli/`                                                                      |
| `extraction_sequencing_notes`| Not extracted. The CLI shell is the permanent `src/specify_cli/` surface for CLI-only code. |

**`current_state`**:
- `src/specify_cli/cli/`

**`adapter_responsibilities`**:
- All user-facing CLI commands, argument parsing, and Rich console output
- Entry points for every `spec-kitty *` sub-command
- Permanent home; extraction of other slices moves code *out of* `src/specify_cli/`, not out of the CLI shell

**`shims`**: *(none)*

**`seams`**:
- CLI shell delegates mission execution to `runtime_mission_execution` via `spec-kitty implement / next / review / accept`
- CLI shell reads charter context via `charter.build_charter_context` for `spec-kitty charter *` commands
- CLI shell reads lifecycle status via `status.*` for `spec-kitty agent tasks status`

---

## Charter Governance

| Field                        | Value                       |
|------------------------------|-----------------------------|
| `canonical_package`          | `charter` (= `src/charter/`) |
| `extraction_sequencing_notes`| Already extracted by mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880`. No further extraction queued. |

**`current_state`**:
- `src/charter/`

**`adapter_responsibilities`**:
- `src/specify_cli/cli/commands/charter.py` — `spec-kitty charter *` CLI commands
- `src/specify_cli/cli/commands/charter_bundle.py` — bundle management CLI surface

**`shims`**: *(none — `src/specify_cli/charter/` compatibility shim deleted by WP02 of mission `functional-ownership-map-01KPDY72`)*

**`seams`**:
- Runtime reads charter context via `charter.build_charter_context` to load project principles at mission start
- Doctrine loads charter bundle for principle synthesis via `charter.ensure_charter_bundle_fresh`

> **Reference exemplar**: Mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` (`01KPD880`) is the canonical exemplar for all future slice extractions in this repository. It established the full extraction pattern: move canonical code to `src/<slice>/`, wire adapter CLI commands in `src/specify_cli/cli/commands/`, create a re-export shim at `src/specify_cli/<slice>/` with a `DeprecationWarning` and `__removal_release__`, add the C-005 test-fixture exception, and document the seams. Every downstream extraction Mission (#612, #613, #614) follows this pattern. See [06_unified_charter_bundle.md](./06_unified_charter_bundle.md) for the charter bundle contract.

---

## Doctrine

| Field                        | Value                          |
|------------------------------|--------------------------------|
| `canonical_package`          | `doctrine` (= `src/doctrine/`) |
| `extraction_sequencing_notes`| Already extracted. The `model_task_routing` artefact specialises the **tactic** parent-kind: it adds a schema-validated task/model catalog, routing policy (weights, tier constraints), and freshness policy (R-006). No further extraction queued. |

**`current_state`**:
- `src/doctrine/`

**`adapter_responsibilities`**:
- CLI rendering for doctrine entries stays in `src/specify_cli/cli/`

**`shims`**: *(none)*

**`seams`**:
- Runtime loads `doctrine.model_task_routing` to select the appropriate model for each Work Package task type
- Charter reads doctrine principles during charter synthesis for principle–doctrine alignment checks

---

## Runtime Mission Execution

| Field                        | Value             |
|------------------------------|-------------------|
| `canonical_package`          | `src/runtime/`    |
| `extraction_sequencing_notes`| Target for mission #612. Extraction requires the architectural-tests and import-graph-enforcement ACs in #612 to be met, and deprecation scaffolding in #615 to land first. Import-graph enforcement is load-bearing because `dependency_rules` must be verified automatically after the slice boundary moves. |

**`current_state`**:
- `src/specify_cli/runtime/` — runtime bootstrap, resolver, home-path, doctor, migration support
- `src/specify_cli/missions/` — mission type registry and mission-level orchestration
- `src/specify_cli/next/` — canonical `spec-kitty next` control-loop integration
- `src/specify_cli/mission.py`, `src/specify_cli/mission_metadata.py` — mission model and metadata helpers

**`adapter_responsibilities`**:
- `src/specify_cli/cli/commands/implement.py` — `spec-kitty implement` CLI entry point
- `src/specify_cli/cli/commands/accept.py` — `spec-kitty accept` CLI entry point
- `src/specify_cli/cli/commands/init.py` — `spec-kitty init` CLI entry point
- All other `spec-kitty agent action *` CLI entry points

**`shims`**: *(none — runtime has not yet been extracted; code lives directly in `src/specify_cli/runtime/`)*

**`seams`**:
- CLI shell calls runtime to execute the next-step control loop (`spec-kitty next`)
- Runtime reads charter context at mission start via `charter.build_charter_context`
- Runtime reads `doctrine.model_task_routing` for model selection at Work Package dispatch time
- Runtime reads lifecycle lane state via `lifecycle_status` to decide which Work Package to claim next
- Runtime reads glossary state via `glossary` for terminology validation during mission execution

**`dependency_rules`**:
- `may_call`: `charter_governance`, `doctrine`, `lifecycle_status`, `glossary`
- `may_be_called_by`: `cli_shell`

---

## Glossary

| Field                        | Value                                                                                                                               |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `canonical_package`          | `src/glossary/`                                                                                                                     |
| `extraction_sequencing_notes`| Target for mission #613. Depends on the architectural-tests AC in #613 and deprecation scaffolding in #615 landing first. Import-graph tooling (AC in #612) is nice-to-have, not blocking. |

**`current_state`**:
- `src/specify_cli/glossary/`

**`adapter_responsibilities`**:
- `src/specify_cli/cli/commands/glossary.py` — CLI argument parsing and Rich rendering for `spec-kitty glossary *` commands

**`shims`**: *(none — glossary has not yet been extracted)*

**`seams`**:
- Doctrine registers a glossary runner via `kernel.glossary_runner.register()`; runtime reads via `get_runner()` (resolved by ADR `2026-03-25-1`)
- Runtime reads canonical terminology via `glossary.store` to validate Work Package and Mission naming during mission execution

---

## Dashboard

| Field                        | Value                                                                                                                        |
|------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `canonical_package`          | `dashboard` (= `src/dashboard/`)                                                                                             |
| `extraction_sequencing_notes`| Service extraction shipped in mission `dashboard-service-extraction-01KQMCA6`. Transport migration (FastAPI/OpenAPI) is mission `frontend-api-fastapi-openapi-migration-01KQN2JA` and adds `src/dashboard/api/` as a sibling subpackage. Scanner, status, and sync subsystems remain in `src/specify_cli/` until their own extraction missions; `src/dashboard/` retains intentional cross-layer imports from those subsystems until they are extracted (staged approach). Full boundary isolation — "no imports from `src/specify_cli/`" — requires scanner (#613) and status (#614) extraction missions as prerequisites. |

**`current_state`** (post-registry mission `mission-registry-and-api-boundary-doctrine-01KQPDBB`):
- `src/dashboard/services/registry.py` — **canonical reader**: `MissionRegistry` + `WorkPackageRegistry`; mtime-caches filesystem reads; all transport layers consume this
- `src/dashboard/services/{mission_scan,project_state,sync}.py` — extracted business logic; `MissionScanService` and `WorkPackageRegistry` delegate through the registry
- `src/dashboard/file_reader.py` — path-traversal-safe artifact reads
- `src/dashboard/api_types.py` — TypedDict response shapes (canonical home post-extraction)
- `src/dashboard/api/` — FastAPI app subpackage; contains `app.py`, `deps.py` (`get_mission_registry` dependency), `errors.py`, `models.py` (`Link`, `ResourceModel`), and `routers/<family>.py`
- `src/specify_cli/dashboard/handlers/{features,api,charter,diagnostics,glossary,lint,static}.py` — thin single-call adapters; legacy stack retained until a separate retirement mission removes it
- `src/specify_cli/dashboard/server.py` — strangler boundary that selects between legacy and FastAPI transport via `dashboard.transport` config

**`adapter_responsibilities`** (post-registry):
- **Legacy stack (retained for rollback)**: HTTP dispatch via `handlers/router.py`, `BaseHTTPRequestHandler` I/O, inline token guards
- **FastAPI stack (`src/dashboard/api/`)**: route registration via `APIRouter` per family; `Depends(get_mission_registry)` injects registry into routers; `Depends(verify_project_token)` for token validation; `StaticFiles` mount for assets; auto-generated OpenAPI at `/openapi.json` + Swagger UI at `/docs` + ReDoc at `/redoc`
- **Transport-independent**: HTTP server bootstrap selects the active stack at process start; the strangler boundary in `server.py` reads the config and dispatches

**`shims`**:
- path: `src/specify_cli/dashboard/api_types.py`
  canonical_import: `dashboard.api_types`
  removal_release: FastAPI transport migration milestone
- path: `src/specify_cli/scanner.py`
  canonical_import: `specify_cli.dashboard.scanner` (will move with scanner extraction mission #613)
  removal_release: scanner extraction mission completion (#613) — the canonical scanner location moves out of `specify_cli.dashboard.scanner` at that point and this shim updates to point at the new home, then retires when `dashboard.*` imports the canonical path directly. See [scanner-shim-ownership-addendum.md](../../kitty-specs/dashboard-service-extraction-01KQMCA6/scanner-shim-ownership-addendum.md).

**`seams`**:
- `FastAPI features router` → `MissionScanService.get_features_list` → `MissionRegistry.list_missions` → `scanner.scan_all_features` (cached)
- `FastAPI kanban router` → `MissionScanService.get_kanban` → `WorkPackageRegistry.list_work_packages` → `scanner.scan_feature_kanban` (cached)
- `APIHandler.handle_health` delegates to `ProjectStateService.get_health`
- `APIHandler.handle_sync_trigger` delegates to `SyncService.trigger_sync`
- File-serving handlers (`handle_research`, `handle_contracts`, `handle_checklists`, `handle_artifact`) delegate to `DashboardFileReader`

> **ADR references**:
> - [2026-05-02-1-dashboard-service-extraction](./adr/2026-05-02-1-dashboard-service-extraction.md) — handler-to-service extraction
> - [2026-05-02-2-fastapi-openapi-transport](./adr/2026-05-02-2-fastapi-openapi-transport.md) — FastAPI / OpenAPI transport migration
> - [2026-05-03-1-dashboard-mission-registry-and-cache](./adr/2026-05-03-1-dashboard-mission-registry-and-cache.md) — registry abstraction between FastAPI routers and the filesystem (**Accepted**; shipped in `mission-registry-and-api-boundary-doctrine-01KQPDBB`)
>
> **Doctrine references**:
> - `DIRECTIVE_API_DEPENDENCY_DIRECTION` (`src/doctrine/directives/shipped/api-dependency-direction.directive.yaml`) — enforces single-reader invariant; no scanner imports in transport layer
> - `DIRECTIVE_REST_RESOURCE_ORIENTATION` (`src/doctrine/directives/shipped/rest-resource-orientation.directive.yaml`) — URL naming convention
> - `HATEOAS-LITE` paradigm (`src/doctrine/paradigms/shipped/hateoas-lite.paradigm.yaml`) — `_links` convention; activated when mission B ships
>
> **Completed dashboard sub-tickets**:
> - [#956](https://github.com/Priivacy-ai/spec-kitty/issues/956) — `MissionRegistry` + cache layer ✅ shipped (`mission-registry-and-api-boundary-doctrine-01KQPDBB`)
>
> **Open dashboard sub-tickets** (children of [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645)):
> - [#957](https://github.com/Priivacy-ai/spec-kitty/issues/957) — resource-oriented mission + workpackage endpoints + `WorkPackageAssignment` schema
> - [#958](https://github.com/Priivacy-ai/spec-kitty/issues/958) — OpenAPI tag grouping (Swagger / ReDoc navigation)
> - [#954](https://github.com/Priivacy-ai/spec-kitty/issues/954) — glossary service extraction (transport-only migration follow-up)
> - [#955](https://github.com/Priivacy-ai/spec-kitty/issues/955) — lint service extraction (transport-only migration follow-up)
>
> Engineering log: [`docs/implementation/2026-05-03-dashboard-api-review.md`](../../docs/implementation/2026-05-03-dashboard-api-review.md).

---

## Lifecycle Status

| Field                        | Value                                                                                                                               |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `canonical_package`          | `src/lifecycle/`                                                                                                                    |
| `extraction_sequencing_notes`| Target for mission #614. Has the most cross-slice callers in the codebase (next loop, orchestrator, dashboard, sync, tracker). Requires the architectural-tests and import-graph-enforcement ACs in #614 and deprecation scaffolding in #615 before extraction — the import-graph tooling is material here due to the high fan-in. |

**`current_state`**:
- `src/specify_cli/status/`

**`adapter_responsibilities`**:
- `src/specify_cli/cli/commands/lifecycle.py` — `spec-kitty agent tasks status` and related commands

**`shims`**: *(none — lifecycle has not yet been extracted)*

**`seams`**:
- Runtime reads Work Package lane state via `status.lane_reader.get_wp_lane()` to decide what to claim next
- Orchestrator reads WP status via `status.reducer.materialize()` for cross-repo drift detection
- CLI shell renders lane state via `status.models.StatusSnapshot` for the kanban display
- Sync writes lane events via `status.emit.emit_status_transition()` after SaaS-side state changes

---

## Orchestrator / Sync / Tracker / SaaS

| Field                        | Value                                                                                                                                    |
|------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| `canonical_package`          | `src/orchestrator/` *(forward-looking commitment; no extraction mission queued)*                                                         |
| `extraction_sequencing_notes`| Fragmented across 7 subdirectories today (see `current_state`). No near-term extraction mission. The canonical target is recorded here so future consolidation work has a named destination. Not in scope for missions #612–#615. |

**`current_state`**:
- `src/specify_cli/orchestrator_api/` — external-consumer contract surface (SaaS API)
- `src/specify_cli/lanes/` — lane computation and worktree ownership
- `src/specify_cli/merge/` — merge executor, preflight validation, conflict forecast
- `src/specify_cli/sync/` — sync coordinator, background sync, body queue and transport
- `src/specify_cli/tracker/` — tracker connector gateway (Linear, Jira, local)
- `src/specify_cli/saas/` — SaaS readiness flags and rollout control
- `src/specify_cli/shims/` — orchestrator-internal shim registry

**`adapter_responsibilities`**:
- CLI commands for orchestrator operations (`spec-kitty merge`, `spec-kitty agent config *`, etc.) stay in `src/specify_cli/cli/`

**`shims`**: *(none — no extraction yet; shim registry is documented by mission #615)*

**`seams`**:
- Lifecycle emits status events; sync reads them for SaaS propagation via `status.emit`
- Runtime dispatches Work Packages via `lanes.compute` for worktree allocation
- CLI shell reports merge state via `merge.state.load_state()` for `spec-kitty merge --resume`
- Tracker connector is called by sync after body-queue flush

---

## Migration / Versioning

| Field                        | Value                                                                                                                          |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `canonical_package`          | `src/specify_cli/migration/` and `src/specify_cli/upgrade/` *(stays)*                                                         |
| `extraction_sequencing_notes`| No near-term extraction. The slice's role as upgrade scaffolding for project-level migrations is distinct from runtime mission execution. Stays under `src/specify_cli/` for the foreseeable future. Not a target of any mission in the #612–#615 wave. |

**`current_state`**:
- `src/specify_cli/migration/` — migration runner, schema version tracking, state rebuild
- `src/specify_cli/upgrade/` — upgrade registry, migration file discovery, compatibility detector

**`adapter_responsibilities`**:
- `spec-kitty upgrade` CLI surface stays in `src/specify_cli/cli/`

**`shims`**: *(none)*

**`seams`**:
- Upgrade command reads the migration registry to apply incremental migrations on `spec-kitty upgrade`
- Runtime bootstrap calls migration path discovery to confirm the project is on the current schema version

---

## Safeguards and Direction

The following issues gate slice extractions and must land before the indicated missions proceed:

| Safeguard | Owned by | Slices that depend on it |
|-----------|----------|--------------------------|
| Architectural tests | AC in [#612](https://github.com/Priivacy-ai/spec-kitty/issues/612), [#613](https://github.com/Priivacy-ai/spec-kitty/issues/613), [#614](https://github.com/Priivacy-ai/spec-kitty/issues/614) respectively | Runtime (#612), Glossary (#613), Lifecycle (#614) |
| Deprecation scaffolding / shim registry | [#615](https://github.com/Priivacy-ai/spec-kitty/issues/615) | Runtime (#612), Glossary (#613), Lifecycle (#614) |
| Import-graph enforcement | AC in [#612](https://github.com/Priivacy-ai/spec-kitty/issues/612); also benefits [#614](https://github.com/Priivacy-ai/spec-kitty/issues/614) | Runtime (#612, load-bearing for `dependency_rules`), Lifecycle (#614, load-bearing due to high fan-in) |

**Direction**: [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461) provides the architectural rationale for extracting charter-adjacent governance into standalone packages. The ownership map is a downstream artefact of that direction: it records the extraction targets once #461's analysis is settled.

---

## Downstream Missions

| Mission | Slice | What it consumes from this map |
|---------|-------|-------------------------------|
| [#612 — Runtime Mission Execution Extraction](https://github.com/Priivacy-ai/spec-kitty/issues/612) | `runtime_mission_execution` | `canonical_package`, `current_state`, `adapter_responsibilities`, `dependency_rules`, `extraction_sequencing_notes` |
| [#613 — Glossary Extraction](https://github.com/Priivacy-ai/spec-kitty/issues/613) | `glossary` | `canonical_package`, `current_state`, `adapter_responsibilities`, `seams`, `extraction_sequencing_notes` |
| [#614 — Lifecycle Status Extraction](https://github.com/Priivacy-ai/spec-kitty/issues/614) | `lifecycle_status` | `canonical_package`, `current_state`, `adapter_responsibilities`, `seams`, `extraction_sequencing_notes` |
| [#615 — Migration Shim Rulebook](https://github.com/Priivacy-ai/spec-kitty/issues/615) | All slices with shims | `shims[].path`, `shims[].canonical_import`, `shims[].removal_release` |

---

## Change Control

This map is a **living document**. Edits land in-place on the target branch; there is no versioned copy. The following rules govern changes:

- **Slice entry edits** (correcting `current_state`, `seams`, etc.): land via a PR that cites the relevant mission or issue. The PR description must reproduce the affected slice entry and state what changed and why.
- **New slice key**: requires a new mission spec; the eight-key set in §2.1 of the data-model is fixed by FR-002. A proposal to add a key is treated as a scope change.
- **Each extraction PR** must confirm in its description that its slice entry is honoured: every field is delivered, deferred with a named tracker, or noted as N/A with a reason.
- **Machine-readable manifest** (`05_ownership_manifest.yaml`) must be updated in the same commit as any map change that alters a field value. The schema test in `tests/architecture/test_ownership_manifest_schema.py` is the enforcing gate.

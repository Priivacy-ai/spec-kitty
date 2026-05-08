---
work_package_id: WP07
title: Final wrap-up — ADR promotion + ownership map + runbook + full QA + snapshot regen
dependencies:
- WP05
- WP06
requirement_refs:
- C-003
- FR-012
- FR-016
- FR-017
- NFR-005
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
agent: "opencode"
shell_pid: "1547112"
history:
- date: '2026-05-03'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: architect-alphonso
authoritative_surface: architecture/2.x/
execution_mode: planning_artifact
owned_files:
- architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md
- architecture/2.x/adr/README.md
- architecture/2.x/05_ownership_map.md
- architecture/2.x/05_ownership_manifest.yaml
- docs/migration/dashboard-fastapi-transport.md
- tests/test_dashboard/snapshots/openapi.json
- kitty-specs/mission-registry-and-api-boundary-doctrine-01KQPDBB/spec.md
role: architect
tags:
- governance
- qa
- wrap-up
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load architect-alphonso
```

You are Architect Alphonso. End-of-mission governance is in your lane: ADR promotion, ownership map updates, manifest mirroring, migration runbook section. The full-QA + snapshot regen subtasks (T024 + T025) are mostly mechanical (one command each) — record their outputs in this WP's review record.

## Objective

Close out the mission. Five subtasks:

1. Promote the ADR from `Proposed` to `Accepted`.
2. Update the ownership map + manifest to reflect the registry as canonical reader.
3. Add a "MissionRegistry as canonical reader" section to the migration runbook.
4. Run the full test suite once and confirm green.
5. Regenerate the OpenAPI snapshot ONCE per spec C-003 (single regen, not per WP) + check off the FR rows in the spec that are now done.

## Context

Mission completion is when these governance + verification artefacts are in place. The ADR has been in `Proposed` state since 2026-05-03 (it was authored upstream of this mission as part of the architectural assessment). Now that the mission ships, it moves to `Accepted` to reflect that the decision has been executed.

The ownership map's Dashboard slice currently lists `MissionScanService`, `ProjectStateService`, `SyncService`, `DashboardFileReader`. After this mission, the canonical reader is `MissionRegistry` — the services delegate to it. Update the slice's `current_state` and `seams` accordingly.

The migration runbook (introduced by mission `frontend-api-fastapi-openapi-migration-01KQN2JA`) needs a section explaining why the registry exists and what `DIRECTIVE_API_DEPENDENCY_DIRECTION` means in practice — so future contributors do not re-introduce per-request scanner walks "by accident."

OpenAPI snapshot regen: per spec C-003, this is a SINGLE regen at end of mission, not per WP. WP04's router migration changes the OpenAPI doc (the `app.openapi()` walks the active router set; the new dependency injection adds `Depends` schema annotations). WP05's `Link` and `ResourceModel` types may also touch the components schema. We let those changes accumulate, regenerate the snapshot ONCE at the end, and review the diff cohesively.

## Subtasks

### T021 — ADR promotion (Proposed → Accepted)

**File**: `architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md`.

**Action**: edit the status line:

```diff
- **Status**: Proposed (mission tracked at [#956](https://github.com/Priivacy-ai/spec-kitty/issues/956))
+ **Status**: Accepted (mission `mission-registry-and-api-boundary-doctrine-01KQPDBB` shipped 2026-05-XX)
```

(replace `XX` with the merge date, or use the spec's `Created` date if merged the same day as planning).

**File**: `architecture/2.x/adr/README.md`.

**Action**: update the index row:

```diff
- | 2026-05-03-1 | [Dashboard Mission Registry and Cache](./2026-05-03-1-dashboard-mission-registry-and-cache.md) | Proposed | TBD — tracked at [#956](https://github.com/Priivacy-ai/spec-kitty/issues/956) |
+ | 2026-05-03-1 | [Dashboard Mission Registry and Cache](./2026-05-03-1-dashboard-mission-registry-and-cache.md) | Accepted | `mission-registry-and-api-boundary-doctrine-01KQPDBB` |
```

### T022 — Ownership map + manifest updates

**Files**: `architecture/2.x/05_ownership_map.md`, `architecture/2.x/05_ownership_manifest.yaml`.

**Action**: update the Dashboard slice in the ownership map:

- `current_state` adds `src/dashboard/services/registry.py` (the canonical reader).
- `current_state` notes the `MissionScanService` / `ProjectStateService` / `SyncService` triad now delegate through the registry.
- `seams` updates:

```diff
- - `FeatureHandler.handle_features_list` delegates to `MissionScanService.get_features_list`
+ - `FastAPI features router` → `MissionScanService.get_features_list` → `MissionRegistry.list_missions` → `scanner.scan_all_features` (cached)
- - `FeatureHandler.handle_kanban` delegates to `MissionScanService.get_kanban`
+ - `FastAPI kanban router` → `MissionScanService.get_kanban` → `WorkPackageRegistry.list_work_packages` → `scanner.scan_feature_kanban` (cached)
```

- Cross-link the three new doctrine artefacts:

```markdown
> **Doctrine references**:
> - `DIRECTIVE_API_DEPENDENCY_DIRECTION` (`src/doctrine/directives/shipped/api-dependency-direction.directive.yaml`) — enforces single-reader invariant
> - `DIRECTIVE_REST_RESOURCE_ORIENTATION` (`src/doctrine/directives/shipped/rest-resource-orientation.directive.yaml`) — URL naming
> - `HATEOAS-LITE` paradigm (`src/doctrine/paradigms/shipped/hateoas-lite.paradigm.yaml`) — `_links` convention; mission B activates
```

- Mark `#956` as `done` in the "Open dashboard sub-tickets" callout (added by an earlier mission). Promote the bullet to a separate "Completed dashboard sub-tickets" callout if the section is getting long.

**Mirror in the YAML manifest** (`05_ownership_manifest.yaml`): add the registry path to `dashboard.current_state` and update `seams` strings.

**Validation**: `pytest tests/architecture/test_ownership_manifest_schema.py` must pass.

### T023 — Migration runbook section

**File**: `docs/migration/dashboard-fastapi-transport.md`.

**Action**: add a new section after the existing "Mission convention notes" section:

```markdown
## MissionRegistry as canonical reader

Mission `mission-registry-and-api-boundary-doctrine-01KQPDBB` (2026-05-03)
introduced the `MissionRegistry` (`src/dashboard/services/registry.py`) as
the single sanctioned reader for mission and work-package data. Every
transport — FastAPI dashboard routers, the CLI `spec-kitty dashboard --json`,
and (when introduced) MCP tools — consumes the registry. Direct imports of
`specify_cli.dashboard.scanner` or `specify_cli.scanner` from any transport
module are forbidden by `DIRECTIVE_API_DEPENDENCY_DIRECTION`
(`src/doctrine/directives/shipped/api-dependency-direction.directive.yaml`),
enforced in CI by `tests/architectural/test_transport_does_not_import_scanner.py`.

If you are adding a new transport (a new FastAPI route, a new CLI subcommand,
a new MCP tool):

1. Construct a `MissionRegistry` with the project root, OR pull one from
   `Depends(get_mission_registry)` if you are inside FastAPI.
2. Call `registry.list_missions()`, `registry.get_mission(handle)`,
   `registry.workpackages_for(handle).list_work_packages()`, etc.
3. Do not import the scanner. The architectural test will fail your PR
   if you do.

### Why this exists

Before this mission, every dashboard request walked `kitty-specs/*/` from
disk. With ~144 missions and a 1-Hz client poll, a single open browser tab
generated ~720 file `open()` syscalls per second. The registry mtime-caches
its filesystem reads; warm-cache requests cost ≤ 5 syscalls per request.

See ADR
[`architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md`](../../architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md)
for the architectural decision and rejected alternatives.
```

### T024 — Full test suite confirmation

**Action**: run

```bash
.venv/bin/python -m pytest tests/test_dashboard/ tests/architectural/ tests/sync/test_daemon_intent_gate.py -q --timeout=120
```

Capture the pass count and any failures. Expected: ≥ 361 passed (the previous baseline) plus the new tests this mission ships:

- `tests/test_dashboard/test_scanner_entrypoint_parity.py` (WP01, ~2-4 tests)
- `tests/test_dashboard/test_mission_registry.py` (WP03, ~10 tests)
- `tests/architectural/test_transport_does_not_import_scanner.py` (WP05, 3 tests)
- `tests/architectural/test_url_naming_convention.py` (WP05, 4 tests)
- `tests/architectural/test_resource_models_have_links.py` (WP05, 3 tests)

Document the final pass count in the WP07 review record.

If any test fails, the failure must be triaged before the mission can merge:
- Test from this mission failing → fix in the responsible WP.
- Pre-existing test failing → may be a regression caused by the migration; route to WP04 for triage.

### T025 — OpenAPI snapshot regen + spec FR book-keeping

**Action**:

```bash
.venv/bin/python -c "
from pathlib import Path
import json
from dashboard.api import create_app
app = create_app(Path('.'), None)
spec = app.openapi()
out = Path('tests/test_dashboard/snapshots/openapi.json')
out.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n', encoding='utf-8')
print('snapshot regenerated:', out.stat().st_size, 'bytes')
"

.venv/bin/python -m pytest tests/test_dashboard/test_openapi_snapshot.py -v
```

Expected: snapshot regenerated; the snapshot test then passes against the new file.

The snapshot diff is reviewed inline as part of the WP07 commit. Per `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/contracts/openapi-stability.md`, snapshot drift requires reviewer signoff. The reviewer (mission-level) confirms:

- New schemas added: `Link`, `ResourceModel` from WP05.
- Existing routes' schemas unchanged (FR-019 / spec C-005).

**Spec FR book-keeping**: edit `kitty-specs/mission-registry-and-api-boundary-doctrine-01KQPDBB/spec.md` and mark each FR row's status as `[x] Approved` (or whatever the convention is for closing FRs). This is purely documentation hygiene; FR statuses on the merged spec reflect the as-shipped state.

## Branch Strategy

Lane-less on `feature/650-dashboard-ui-ux-overhaul`. Five files; commit as one or two `chore(WP07-...)` commits — typically one for governance docs + one for the snapshot regen.

## Definition of Done

- [ ] ADR `2026-05-03-1` reads `Status: Accepted`.
- [ ] ADR README index row updated.
- [ ] Ownership map Dashboard slice + manifest reflect the registry; ownership manifest schema test passes.
- [ ] Migration runbook contains the "MissionRegistry as canonical reader" section.
- [ ] Full test suite passes (≥ 361 + the new tests; no regressions).
- [ ] OpenAPI snapshot regenerated ONCE; snapshot test green.
- [ ] Spec FR rows updated to reflect as-shipped state.

## Reviewer guidance

- **ADR status integrity**: confirm BOTH the ADR file's status line AND the README index row are `Accepted`. Drift between them is a finding.
- **Ownership map ↔ manifest text consistency**: the YAML manifest is the machine-readable mirror. If the map says X and the manifest says Y, the schema test catches structural drift but not text drift; manual review catches the latter.
- **Snapshot regen happens ONCE**: confirm WP07's commits include a single OpenAPI snapshot change, not per-WP regenerations from earlier WPs. If earlier WPs accidentally regenerated, the snapshot churn must be reconciled to one final state in this WP.
- **Test pass count is recorded**: the WP07 review record (this WP's status events or the merge commit message) cites the final pass count.

## Risks

- **Snapshot drift larger than expected**: WP05's `Link` + `ResourceModel` types add to the components/schemas section. WP04's `Depends` annotations may add path parameters. The diff might be 50-200 lines. Each addition is reviewed inline; if a delta is unexpected, route back to the responsible WP.
- **Test suite regression discovered late**: if T024 finds a failing test introduced by an earlier WP, the fix lives in that WP, not this one. WP07 is housekeeping, not bug fixing. Route the failure back; the merge for this mission blocks until the responsible WP pushes a fix.
- **Migration runbook drift across missions**: each mission that touches the dashboard transport adds a section to this runbook. Keep sections in chronological order with dated headers; resist the temptation to refactor the runbook holistically as part of this WP — that's a separate mission.

## Activity Log

- 2026-05-03T17:54:27Z – opencode – shell_pid=1539810 – Started implementation via action command
- 2026-05-03T17:57:52Z – opencode – shell_pid=1539810 – ADR promoted; ownership map+manifest updated; runbook section added; 361 tests pass; snapshot regenerated
- 2026-05-03T17:57:59Z – opencode – shell_pid=1547112 – Started review via action command
- 2026-05-03T17:58:19Z – opencode – shell_pid=1547112 – All 5 subtasks complete: ADR Accepted, ownership map+manifest updated (schema tests pass), runbook section added, 361 tests green, snapshot regenerated and test passes. APPROVED.

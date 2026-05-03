# Tasks — Mission Registry and API Boundary Doctrine

**Mission**: `mission-registry-and-api-boundary-doctrine-01KQPDBB`
**Branch**: `feature/650-dashboard-ui-ux-overhaul`
**Spec / Plan / Design**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

7 work packages, 25 subtasks, average 3.6 subtasks per WP. WP01 (boyscout) is a strict prerequisite — every other WP carries `dependencies: [WP01]` (transitively through WP02/WP03 where applicable). Mission-wide test sanity rules (spec C-003) bind every WP's DoD.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|------|----------|
| T001 | Audit scanner entry points; document each I/O shape in `src/specify_cli/dashboard/scanner.py` module docstring; add `# TODO(remove with mission-registry-and-api-boundary-doctrine-01KQPDBB)` markers on functions the registry will subsume | WP01 | — | [D] |
| T002 | Replace the `git update-index --assume-unchanged` workaround for daemon-driven `kitty-specs/*/status.json` drift; chosen direction (stop daemon vs gitignore snapshot) recorded in WP01 review record | WP01 | [D] |
| T003 | Author `tests/test_dashboard/test_scanner_entrypoint_parity.py` baseline test asserting `scan_all_features` and `build_mission_registry` produce structurally compatible mission identity for the same fixture | WP01 | [D] |
| T004 | Author `src/doctrine/directives/shipped/api-dependency-direction.directive.yaml` per `contracts/doctrine-artefact-shapes.md` § 1; cross-link to `tests/architectural/test_transport_does_not_import_scanner.py` | WP02 | — | [D] |
| T005 | Author `src/doctrine/directives/shipped/rest-resource-orientation.directive.yaml` per `contracts/doctrine-artefact-shapes.md` § 2; cross-link to `tests/architectural/test_url_naming_convention.py` | WP02 | [D] |
| T006 | Author `src/doctrine/paradigms/shipped/hateoas-lite.paradigm.yaml` per `contracts/doctrine-artefact-shapes.md` § 3; verify all three artefacts pass `tests/doctrine/` schema validation; if any field is rejected, land an additive schema extension in the same WP | WP02 | — | [D] |
| T007 | Define `MissionRecord`, `WorkPackageRecord`, `LaneCounts`, `CacheEntry` Python dataclasses in `src/dashboard/services/registry.py` per `data-model.md` (frozen=True; no Pydantic; full type annotations) | WP03 | — | [D] |
| T008 | Implement `MissionRegistry` class in `src/dashboard/services/registry.py` with `list_missions()`, `get_mission()`, `workpackages_for()`, `invalidate_all()` per `contracts/registry-interface.md`; mtime-cache with `(mtime_ns, file_size, sorted_dirent_names_hash)` triple key | WP03 | — | [D] |
| T009 | Implement `WorkPackageRegistry` class in `src/dashboard/services/registry.py` with `list_work_packages()`, `get_work_package()`, `lane_counts()`; per-mission cache scope; shared cache instances via `WeakValueDictionary` | WP03 | — | [D] |
| T010 | Author `tests/test_dashboard/test_mission_registry.py` with explicit mtime-edge-case coverage: file deleted then recreated with identical mtime; truncated file with same length; concurrent writes during a scan; missing meta.json (legacy mission); cache-stale check syscall count assertion | WP03 | [D] |
| T011 | Wire `MissionRegistry` into FastAPI `app.state.mission_registry` at startup via `src/dashboard/api/app.py:create_app`; add `get_mission_registry()` Depends helper to `src/dashboard/api/deps.py` | WP04 | — | [D] |
| T012 | Migrate `src/dashboard/api/routers/features.py` and `src/dashboard/api/routers/kanban.py` from `MissionScanService` scanner calls to registry calls; update `src/dashboard/services/mission_scan.py` to delegate to the registry rather than calling the scanner directly | WP04 | — | [D] |
| T013 | Migrate CLI `src/specify_cli/cli/commands/dashboard.py` `--json` mode (line ~59) from `build_mission_registry(project_root)` direct call to `MissionRegistry(project_root).list_missions()` | WP04 | [D] |
| T014 | Add `Link` and `ResourceModel` Pydantic marker classes to `src/dashboard/api/models.py`; document the marker contract in the class docstring referencing `HATEOAS-LITE` paradigm | WP05 | — | [D] |
| T015 | Author `tests/architectural/test_transport_does_not_import_scanner.py` per `contracts/architectural-test-contracts.md` § 1; AST-walk `src/dashboard/api/routers/` and `src/specify_cli/cli/commands/dashboard.py`; positive + negative meta-tests | WP05 | [D] |
| T016 | Author `tests/architectural/test_url_naming_convention.py` per `contracts/architectural-test-contracts.md` § 2; walk the FastAPI app's OpenAPI paths; resource-noun regex + action allowlist; positive + negative meta-tests | WP05 | [D] |
| T017 | Author `tests/architectural/test_resource_models_have_links.py` per `contracts/architectural-test-contracts.md` § 3; walk Pydantic class hierarchy; assert `ResourceModel` subclasses declare `_links: dict[str, Link]`; positive + negative meta-tests; mission-A pass is vacuous (no subclasses yet) | WP05 | [D] |
| T018 | Author `scripts/bench_registry_syscalls.py` per `research.md` § R-10; spawns dashboard under both transports (legacy scanner-only via `--transport legacy` AND FastAPI with registry); `strace -c -e trace=openat,stat,statx` for 30s; outputs JSON report | WP06 | — |
| T019 | Run baseline (legacy) and post-registry (FastAPI) benchmarks on local machine; capture `/tmp/bench-registry-syscalls.json` JSON report | WP06 | — |
| T020 | Author `kitty-specs/mission-registry-and-api-boundary-doctrine-01KQPDBB/release-checklist.md` with the bench numbers pasted in; verify NFR-001 (≤5 syscalls/req warm cache), NFR-002 (≤25% cold-start regression), NFR-003 (≤3 stat calls per stale check); fill operator slots TBD | WP06 | [P] |
| T021 | Promote ADR `architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md` from `Status: Proposed` to `Status: Accepted`; update `architecture/2.x/adr/README.md` index row to `Accepted` | WP07 | — |
| T022 | Update `architecture/2.x/05_ownership_map.md` Dashboard slice: `current_state` adds the registry; `seams` updates to "FastAPI router → registry.method() → backbone (cached)"; cross-link the three new doctrine artefacts. Mirror in `05_ownership_manifest.yaml`. Mark `#956` as `done` in the Open Sub-tickets callout | WP07 | [P] |
| T023 | Update `docs/migration/dashboard-fastapi-transport.md` with a "MissionRegistry as canonical reader" section explaining `DIRECTIVE_API_DEPENDENCY_DIRECTION` so future contributors do not re-introduce per-request scanner walks | WP07 | [P] |
| T024 | Run full test suite — `.venv/bin/python -m pytest tests/test_dashboard/ tests/architectural/ tests/sync/test_daemon_intent_gate.py -q --timeout=120`; confirm zero regressions | WP07 | — |
| T025 | Regenerate OpenAPI snapshot ONCE at end of mission per spec C-003 (single regen, not per WP); `.venv/bin/python -c "from dashboard.api import create_app; ..."`; update spec FR checkbox status (book-keeping only — mark FR-001..FR-017 as `[x]` once their owning WP is done) | WP07 | — |

## Dependencies

```
WP01 (boyscout)
  ├──▶ WP02 (doctrine artefacts)
  └──▶ WP03 (registry core)

WP02 (doctrine) ──┐
                  ├──▶ WP04 (router migration)
WP03 (registry) ──┤
                  └──▶ WP05 (architectural tests + ResourceModel marker)
                        depends on WP02 (directives must exist first)
                        AND on WP04 (routers must use registry so test sees compliant code)

WP04 ──▶ WP05 (test scans real router code)
WP04 ──▶ WP06 (perf verification needs routers wired)

WP05 ──┐
       ├──▶ WP07 (final wrap-up)
WP06 ──┘
```

Lane parallelization opportunities (per planner's lane assignment, materialised by `finalize-tasks` in `lanes.json`):

- After WP01 merges: WP02 and WP03 run in parallel.
- After WP02 + WP03 + WP04 merge: WP05 and WP06 run in parallel.
- WP07 sequential at the end.

## Work Packages

### WP01 — Boyscout cleanup (prerequisite for all)

**Goal**: leave the substrate in a state where the registry can be built on top without inheriting pre-existing debt.

**Priority**: P0 — gates everything else.
**Independent test**: scanner entry-point table exists in the docstring; `git ls-files -v | grep ^h | grep kitty-specs` is empty; the parity baseline test exists and either passes or fails with documented expected delta.

**Subtasks**:
- [x] T001 Audit scanner entry points; document in module docstring; add TODO markers
- [x] T002 Replace `assume-unchanged` workaround for daemon-driven status.json drift
- [x] T003 Author scanner parity baseline test

**Estimated prompt size**: ~280 lines.

### WP02 — Doctrine artefacts

**Goal**: codify the three new doctrine artefacts so subsequent WPs can cross-reference them.

**Priority**: P0
**Independent test**: three new YAML files exist; `pytest tests/doctrine/` passes; each artefact references its enforcement test.

**Subtasks**:
- [x] T004 `DIRECTIVE_API_DEPENDENCY_DIRECTION` YAML
- [x] T005 `DIRECTIVE_REST_RESOURCE_ORIENTATION` YAML
- [x] T006 `HATEOAS-LITE` paradigm YAML + schema-extension if needed

**Dependencies**: WP01.
**Estimated prompt size**: ~260 lines.

### WP03 — Registry core

**Goal**: implement `MissionRegistry` and `WorkPackageRegistry` with mtime-cache invalidation per the data-model and registry-interface contracts.

**Priority**: P0
**Independent test**: `pytest tests/test_dashboard/test_mission_registry.py` passes; mtime-edge-case tests cover deleted+recreated, truncated, concurrent writes, missing meta.json.

**Subtasks**:
- [x] T007 Dataclasses (`MissionRecord`, `WorkPackageRecord`, `LaneCounts`, `CacheEntry`)
- [x] T008 `MissionRegistry` implementation with cache
- [x] T009 `WorkPackageRegistry` implementation with per-mission cache
- [x] T010 Edge-case unit tests

**Dependencies**: WP01.
**Estimated prompt size**: ~440 lines (4 subtasks, registry is the centrepiece).

### WP04 — Router migration

**Goal**: switch every transport-side consumer from scanner imports to registry calls. Existing JSON wire shapes preserved (no contract change in this mission).

**Priority**: P0
**Independent test**: existing dashboard parity tests pass against the registry-backed routers; CLI `--json` output count matches FastAPI `/api/features` count.

**Subtasks**:
- [x] T011 Wire `MissionRegistry` into FastAPI app state
- [x] T012 Migrate FastAPI `features` + `kanban` routers + `MissionScanService`
- [x] T013 Migrate CLI `dashboard --json` consumer

**Dependencies**: WP02, WP03.
**Estimated prompt size**: ~320 lines.

### WP05 — Architectural tests + `ResourceModel` marker

**Goal**: codify three new architectural tests that enforce the directives in CI; introduce the `ResourceModel` marker so mission B can subclass.

**Priority**: P0
**Independent test**: each new test passes (positive + negative meta-tests + the main scan); `tests/architectural/test_transport_does_not_import_scanner.py` proves WP04's migration succeeded.

**Subtasks**:
- [x] T014 `Link` + `ResourceModel` Pydantic marker classes in `models.py`
- [x] T015 `test_transport_does_not_import_scanner.py`
- [x] T016 `test_url_naming_convention.py`
- [x] T017 `test_resource_models_have_links.py`

**Dependencies**: WP02, WP04.
**Estimated prompt size**: ~480 lines (4 architectural tests, all need positive+negative meta-tests).

### WP06 — Performance verification

**Goal**: prove NFR-001..NFR-003 with measured syscall numbers; record in release-checklist for the operator who cuts the next release.

**Priority**: P1
**Independent test**: `scripts/bench_registry_syscalls.py` runs and produces a JSON report; release-checklist contains real numbers (not TBD).

**Subtasks**:
- [ ] T018 Author bench script
- [ ] T019 Run baseline + registry benchmarks; capture JSON report
- [ ] T020 Update release-checklist with numbers + NFR verification

**Dependencies**: WP04.
**Estimated prompt size**: ~280 lines.

### WP07 — Final wrap-up: governance + QA

**Goal**: promote the ADR; update ownership map / manifest / runbook; run full test suite; regenerate OpenAPI snapshot ONCE per spec C-003.

**Priority**: P1
**Independent test**: ADR status reads `Accepted`; ownership map reflects the registry; full test suite green; OpenAPI snapshot test green.

**Subtasks**:
- [ ] T021 ADR promotion (Proposed → Accepted)
- [ ] T022 Ownership map + manifest updates
- [ ] T023 Migration runbook section
- [ ] T024 Full test suite confirmation
- [ ] T025 OpenAPI snapshot regen (single, end-of-mission) + spec FR checkbox book-keeping

**Dependencies**: WP05, WP06.
**Estimated prompt size**: ~360 lines.

## Definition of Done (mission-wide)

The mission is done when:

- [ ] Every WP's subtasks are checked off and committed.
- [ ] `.venv/bin/python -m pytest tests/test_dashboard/ tests/architectural/ tests/sync/test_daemon_intent_gate.py -q --timeout=120` is green (≥361 passed plus the new tests this mission ships).
- [ ] `tests/architectural/test_transport_does_not_import_scanner.py` passes (FR-009 invariant holds).
- [ ] `tests/architectural/test_url_naming_convention.py` passes (FR-010 invariant holds; current paths are in the action allowlist).
- [ ] `tests/architectural/test_resource_models_have_links.py` passes vacuously (no `ResourceModel` subclasses in this mission per spec C-006).
- [ ] `scripts/bench_registry_syscalls.py` produces NFR-001/002/003-compliant numbers in the release-checklist.
- [ ] ADR `2026-05-03-1` reads `Status: Accepted`; ADR README index updated.
- [ ] Ownership map + manifest reflect the registry; #956 marked `done` in the Open Sub-tickets callout.
- [ ] Migration runbook has a "MissionRegistry as canonical reader" section.
- [ ] OpenAPI snapshot regenerated ONCE (per spec C-003 — single regen, not per WP).
- [ ] No new `# type: ignore` directives in `src/dashboard/services/registry.py` or migrated routers (NFR-006).

## MVP scope recommendation

Mission A's MVP is everything through WP05. WP06 (performance) and WP07 (governance + QA) are end-of-mission housekeeping that polishes the deliverable but does not change observable behaviour. If a stop-ship event forces a partial merge, WP01–WP05 is the smallest cut that delivers a working registry-backed dashboard with enforcement tests.

That said, all 7 WPs are in scope for this mission and should ship together. The MVP fallback is a contingency, not a plan.

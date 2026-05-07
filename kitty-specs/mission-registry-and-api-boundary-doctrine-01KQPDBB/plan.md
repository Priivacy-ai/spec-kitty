# Implementation Plan: Mission Registry and API Boundary Doctrine

**Branch**: `feature/650-dashboard-ui-ux-overhaul` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/mission-registry-and-api-boundary-doctrine-01KQPDBB/spec.md`

## Summary

Mission A of epic [#645](https://github.com/Priivacy-ai/spec-kitty/issues/645). Introduces a `MissionRegistry` and `WorkPackageRegistry` as the **single sanctioned reader** for mission/WP data across every transport (FastAPI dashboard routers, CLI subcommands, future MCP tools). The registry mtime-caches its filesystem reads — the existing 1-Hz `dashboard.js` poll drops from ~720 file `open()` syscalls per second to ≤ 3 stat calls per request in steady state.

Three new doctrine artefacts (`DIRECTIVE_API_DEPENDENCY_DIRECTION`, `DIRECTIVE_REST_RESOURCE_ORIENTATION`, `HATEOAS-LITE` paradigm) codify the architectural rules. Three new architectural tests enforce them in CI. The boyscout WP01 lands first and gates every other WP: scanner entry-point audit + `assume-unchanged` workaround removal + scanner parity baseline test.

The pre-existing ADR `architecture/2.x/adr/2026-05-03-1-dashboard-mission-registry-and-cache.md` is promoted from `Proposed` to `Accepted` as part of this mission.

## Technical Context

**Language/Version**: Python 3.11+ (existing repo requirement; `.python-version` reads `3.13 / 3.12 / 3.11` priority list — tests run on 3.13.12).
**Primary Dependencies**: stdlib only — `os.stat` for mtime cache invalidation, `ast` for the architectural tests, `pathlib` / `dataclasses` / `typing` for the registry. **Zero new top-level Python deps** (NFR-004).
**Storage**: filesystem only — `kitty-specs/<slug>/meta.json`, `kitty-specs/<slug>/status.events.jsonl`, `kitty-specs/<slug>/tasks/`. Cache lives in process memory; no persistence layer.
**Testing**: pytest. New unit tests for the registry (with `os.utime`-bumped fixture projects); new architectural tests (AST + JSON walk); new parity baseline test in `tests/test_dashboard/`. Doctrine schema validation reuses existing infra.
**Target Platform**: local development on Linux / macOS / Windows; loopback-only HTTP for the dashboard surface.
**Project Type**: single project (Python library + CLI; no separate frontend deploy).
**Performance Goals**: NFR-001 (≤5 syscalls per warm-cache request, syscall-traced); NFR-002 (≤25% latency overhead vs scanner cold-start); NFR-003 (≤3 stat calls per cache-stale check).
**Constraints**: localhost-only network binding; no auth changes; no contract redesign; no public API surface change (existing `/api/features` and `/api/kanban/{id}` shapes preserved); legacy scanner shim retained for the strangler period.
**Scale/Scope**: ~144 missions on this repo (representative sample); registry must scale to 500+ missions without warm-cache latency regression.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter directive | Conformance |
|-------------------|-------------|
| **DIRECTIVE_024** (Locality of Change) | Pass — allowed scope explicitly enumerated in spec § Governance: `src/dashboard/services/`, `src/dashboard/api/`, `src/specify_cli/cli/commands/dashboard.py`, `src/specify_cli/dashboard/scanner.py` (docstring only), `src/doctrine/directives/shipped/`, `src/doctrine/paradigms/shipped/`, `tests/architectural/`, `tests/test_dashboard/`, `architecture/2.x/`, `docs/migration/`, mission directory. |
| **DIRECTIVE_010** (Test Coverage Discipline) | Pass — every new module ships with tests against real fixture projects (no synthetic-fixture-only tests, per mission-wide rule C-003). Each architectural test ships with positive AND negative meta-tests. |
| **DIRECTIVE_036** (Adapter Test Pattern) | Pass — registry tests use real fixture projects (mkdir + meta.json + status.events.jsonl) rather than mocked scanner returns. |
| **NEW: DIRECTIVE_API_DEPENDENCY_DIRECTION** | Self-conforming — this mission introduces the directive AND the test that enforces it; the directive applies from this mission forward. |

No charter violations. No `Complexity Tracking` entries needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/mission-registry-and-api-boundary-doctrine-01KQPDBB/
├── spec.md                          # ✅ committed
├── plan.md                          # 🆕 this file
├── checklists/requirements.md       # ✅ committed
├── research.md                      # 🆕 Phase 0 — created next
├── data-model.md                    # 🆕 Phase 1 — created next
├── quickstart.md                    # 🆕 Phase 1 — created next
├── contracts/
│   ├── registry-interface.md        # 🆕 the registry's public Python contract
│   ├── doctrine-artefact-shapes.md  # 🆕 the YAML schema each new artefact must satisfy
│   └── architectural-test-contracts.md  # 🆕 what each architectural test must prove
└── tasks.md                         # Phase 2 (created by /spec-kitty.tasks)
```

### Source code (repository root)

```
src/dashboard/services/
├── __init__.py                      # ✅ existing
├── mission_scan.py                  # ✏️ existing — DELEGATES to MissionRegistry
├── project_state.py                 # ✅ existing
├── sync.py                          # ✅ existing
└── registry.py                      # 🆕 MissionRegistry + WorkPackageRegistry + caches

src/dashboard/api/
├── app.py                           # ✅ existing
├── deps.py                          # ✏️ existing — adds get_mission_registry() Depends
├── errors.py                        # ✅ existing
├── models.py                        # ✏️ existing — adds ResourceModel marker base class
└── routers/                         # ✏️ all existing routers — switch from scanner to registry

src/specify_cli/dashboard/
└── scanner.py                       # ✏️ docstring ONLY — entry-point audit table; TODO markers

src/specify_cli/cli/commands/
└── dashboard.py                     # ✏️ existing — `--json` mode switches to registry

src/doctrine/directives/shipped/
├── api-dependency-direction.directive.yaml  # 🆕 (FR-006)
└── rest-resource-orientation.directive.yaml # 🆕 (FR-007)

src/doctrine/paradigms/shipped/
└── hateoas-lite.paradigm.yaml       # 🆕 (FR-008)

tests/architectural/
├── test_transport_does_not_import_scanner.py  # 🆕 (FR-009)
├── test_url_naming_convention.py              # 🆕 (FR-010)
└── test_resource_models_have_links.py         # 🆕 (FR-011)

tests/test_dashboard/
├── test_scanner_entrypoint_parity.py  # 🆕 boyscout baseline (FR-015)
└── test_mission_registry.py            # 🆕 registry unit tests (mtime cache, edge cases)

architecture/2.x/
├── adr/2026-05-03-1-dashboard-mission-registry-and-cache.md   # ✏️ Proposed → Accepted
├── adr/README.md                                              # ✏️ status update
├── 05_ownership_map.md                                        # ✏️ Dashboard slice update
└── 05_ownership_manifest.yaml                                 # ✏️ mirrored

docs/migration/
└── dashboard-fastapi-transport.md   # ✏️ adds "registry as canonical reader" section
```

**Structure Decision**: Single-project layout. The registry lives in the existing `src/dashboard/services/` package — the parent extraction mission already established that as the canonical service layer. The doctrine artefacts go into the existing shipped doctrine packages. No new top-level packages.

## Phase 0 — Research (`research.md`)

Topics resolved before Phase 1 design (each becomes a Decision / Rationale / Alternatives row in `research.md`):

1. **Cache key composition** — `(mtime_ns, file_size, sorted_dirent_names_hash)` triple per cache entry vs simpler mtime-only. Decision: triple (handles identical-mtime drift cited as edge case in spec).
2. **Cache invalidation strategy** — mtime polling on every read vs background watcher. Decision: poll-on-read (matches the ADR's process-level switch rationale; no new dep; bounded 3-stat-call cost).
3. **Cache scope** — global registry vs per-mission registry. Decision: one `MissionRegistry` for collection-level reads; nested `WorkPackageRegistry` per mission for tasks/. Each cache key is independent so a single WP change does not invalidate the whole project.
4. **Doctrine YAML schema** — confirm the existing shipped-doctrine schema accepts new artefacts in `directives/shipped/` and `paradigms/shipped/` without new schema fields. Decision: yes (NFR-007); if schema rejection surfaces, escalate to schema extension.
5. **Architectural test discovery** — pytest collection mode for new tests (`tests/architectural/`) is via the `architectural` marker. Decision: keep the existing marker; add `pytestmark = pytest.mark.architectural` to each new file.
6. **Test fixture mtime-bumping** — `os.utime(path, (atime, future_mtime))` works cross-platform on Python 3.11+. Decision: confirmed; fixture helper provided alongside the registry tests.
7. **Boyscout T02 scope** — replace the `assume-unchanged` workaround. Two reasonable directions: (a) trace and stop the daemon mutation, (b) gitignore `kitty-specs/*/status.json` (keeping `status.events.jsonl` tracked). Decision: defer to WP01's reviewer with rationale. Both are reversible.
8. **Doctrine cross-link mechanism** — how a directive references an architectural test. Decision: use a `referenced_tests:` field in the directive YAML pointing at the test file path; if the schema does not support this, add a free-form `metadata:` block.
9. **`ResourceModel` marker placement** — `src/dashboard/api/models.py` (alongside existing models) vs new `src/dashboard/api/resource_model.py`. Decision: keep in `models.py` (cohesion; the test that enforces FR-011 walks the same module).
10. **Performance verification methodology** — `strace -c -e trace=openat` against the running dashboard for 30s wall time, baseline vs registry. Decision: confirmed; bench script lives at `scripts/bench_registry_syscalls.py` and outputs JSON the WP06 reviewer pastes into the release record.

## Phase 1 — Design & Contracts

### `data-model.md`

Three primary types, each a Pydantic-free Python `dataclass`:

| Type | Fields | Owner |
|------|--------|-------|
| `MissionRecord` | `mission_id`, `mission_slug`, `display_number`, `mid8`, `feature_dir`, `friendly_name`, `mission_type`, `target_branch`, `created_at`, `lane_counts`, `weighted_percentage`, `is_legacy` | `MissionRegistry` |
| `WorkPackageRecord` | `wp_id`, `title`, `lane`, `subtasks_done`, `subtasks_total`, `agent`, `agent_profile`, `role`, `assignee`, `phase`, `prompt_path`, `dependencies`, `requirement_refs`, `last_event_id`, `last_event_at` | `WorkPackageRegistry` |
| `CacheEntry[T]` | `value: T`, `cache_key: tuple[int, int, str]`, `cached_at: datetime` | both registries (private) |

`MissionRegistry` and `WorkPackageRegistry` are also documented in `data-model.md` with their public method signatures (FR-001).

### `contracts/registry-interface.md`

The Python contract for the registry: every public method, its return type, its cache-invalidation behaviour, and its error contract (e.g. `get_mission(unknown_id)` returns `None`, never raises).

### `contracts/doctrine-artefact-shapes.md`

The YAML schema each new shipped artefact must satisfy. Cross-references the existing shipped-doctrine repository test (`tests/doctrine/`).

### `contracts/architectural-test-contracts.md`

Three test contracts — one per architectural test in FR-009..FR-011. Each documents:
- What the test asserts (exact AST or JSON walk).
- The positive meta-test (synthetic violator must fail).
- The negative meta-test (synthetic clean fixture must pass).
- The allowlist (if any) and the rationale.

### `quickstart.md`

A copy-pasteable verification walk-through: sync, run the dashboard under FastAPI transport with the registry wired in, hit `/api/features`, observe the syscall count via `strace -c`, run the new architectural tests, run the registry unit tests.

## Phase 2 — Tasks (created by `/spec-kitty.tasks`)

Phase 2 will produce `tasks.md` with **8 work packages** anticipated (per planner+architect alignment):

- **WP01 — Boyscout** (3 subtasks): scanner entry-point audit + `assume-unchanged` removal + scanner parity baseline test. Strict prerequisite for every other WP.
- **WP02 — Doctrine artefacts** (3 subtasks): `DIRECTIVE_API_DEPENDENCY_DIRECTION`, `DIRECTIVE_REST_RESOURCE_ORIENTATION`, `HATEOAS-LITE` paradigm. Lands the directives so subsequent WPs can reference them.
- **WP03 — Registry core** (4 subtasks): `MissionRegistry` + `WorkPackageRegistry` + cache key + invalidation. Includes mtime-edge-case unit tests.
- **WP04 — Router migration** (3 subtasks): existing FastAPI routers switch from scanner imports to registry calls; CLI `dashboard --json` switches too.
- **WP05 — Architectural tests** (4 subtasks): `test_transport_does_not_import_scanner.py`, `test_url_naming_convention.py`, `test_resource_models_have_links.py`, plus `ResourceModel` marker class.
- **WP06 — Performance verification** (3 subtasks): `scripts/bench_registry_syscalls.py`; baseline vs registry numbers; release-checklist update.
- **WP07 — Architectural artefact updates** (3 subtasks): ADR promotion (`Proposed` → `Accepted`); ownership map / manifest updates; migration runbook section.
- **WP08 — Final QA** (2 subtasks): full test suite green; OpenAPI snapshot regenerated ONCE (per C-003); spec FR checkboxes updated.

Total subtasks: ~25; all WPs declare `dependencies: [WP01]` (or transitively through WP02/WP03).

## Phase 3 — Implementation

`/spec-kitty.implement WP## --agent claude` per WP. Lane allocation handled by `/spec-kitty.tasks-finalize` based on `owned_files` overlap. Per planner's revision, mission-wide test sanity rules (constraint C-003) bind every WP's DoD.

## Phase 4 — Review & Merge

Per-WP review via `/spec-kitty.review`. After all WPs done, mission merge via `spec-kitty merge`. Post-merge `/spec-kitty.mission-review` audits for drift.

## Complexity Tracking

*No charter violations identified. Section intentionally empty.*

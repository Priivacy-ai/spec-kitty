# Implementation Plan: Dashboard Services Domain Migration (Phase B)
*Path: kitty-specs/dashboard-services-domain-migration-01KR151P/plan.md*

**Branch**: `feature/645-api-surface-completion-mission-c` | **Date**: 2026-05-07 | **Spec**: `kitty-specs/dashboard-services-domain-migration-01KR151P/spec.md`
**Input**: Feature specification from `/kitty-specs/dashboard-services-domain-migration-01KR151P/spec.md`

---

## Summary

Move the four existing dashboard domain services (`MissionRegistry`, `MissionScanService`,
`ProjectStateService`, `SyncService`) from `src/dashboard/services/` into
`src/specify_cli/missions/` — the domain layer — closing the inverted import direction
that currently has `specify_cli` importing upward from `dashboard`. Simultaneously fix
two cache correctness bugs identified in PR #970 review: P1 (list_missions() blind to
per-mission event-log appends) via a two-level cache design, and P2 (WeakValueDictionary
allows GC between requests) via a strong-reference dict. Leave thin compatibility shims
in `dashboard/services/` registered in `shim-registry.yaml` with `removal_release: 3.2.0`.
Update all callers in both `specify_cli/` and `dashboard/api/` to import from the new
canonical paths so the shims have zero dependents at merge time.

## Technical Context

**Language/Version**: Python 3.11+ (existing project requirement)
**Primary Dependencies**: FastAPI (dashboard transport), typer (CLI), pytestarch (architectural tests), threading + stdlib dict (cache implementation — no new dependencies)
**Storage**: Filesystem only — `kitty-specs/*/status.events.jsonl` (event log), `kitty-specs/*/meta.json` (mission identity), `kitty-specs/*/tasks/WP*.md` (WP frontmatter)
**Testing**: pytest; mypy --strict; pytestarch for boundary assertions; new regression tests for P1 (cache invalidation) and P2 (identity check); existing seam tests and OpenAPI snapshot must stay green
**Target Platform**: Linux / macOS / Windows 10+ (cross-platform; no platform-specific I/O)
**Project Type**: Single Python package (`src/` layout) with embedded FastAPI sub-application
**Performance Goals**: `list_missions()` per-mission key check overhead ≤ 5 ms over pre-fix baseline on 150-mission fixture (NFR-003)
**Constraints**: Zero new PyPI packages (C-008); shim bodies ≤ 15 executable lines (C-002); no `dashboard.*` import in moved modules (C-001); wire shapes unchanged (C-004)
**Scale/Scope**: 4 service modules moved; ~15 caller import sites updated; 4 shims registered; 1 architectural test extended; 2 regression tests added; 1 ADR filed

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Python 3.11+** ✅ — all new code targets existing runtime; no version bump
- **mypy --strict** ✅ — moved modules and updated callers must type-check clean (NFR-002)
- **pytest + seam tests** ✅ — NFR-001 encodes zero regression tolerance; P1/P2 tests are additive
- **Cross-platform** ✅ — only stdlib `os.stat` / `Path` I/O; no platform-specific calls
- **Shared package boundary** ✅ — `specify_cli` must not import from `dashboard`; this mission enforces it
- **No new dependencies** ✅ — cache fix uses stdlib `dict`; shims use plain re-export syntax
- **Branch strategy** ✅ — planning and WP execution on `feature/645-api-surface-completion-mission-c`
- **Terminology canon** ✅ — no new `Feature*` identifiers; all new symbols use Mission/WP terminology
- **Shim governance** ✅ — all four shims registered in `shim-registry.yaml` with `removal_release: 3.2.0`

No charter violations.

## Project Structure

### Documentation (this mission)

```
kitty-specs/dashboard-services-domain-migration-01KR151P/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks/               # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── specify_cli/
│   ├── missions/
│   │   ├── __init__.py                      # existing — no changes
│   │   ├── api_types.py                     # existing — no changes
│   │   ├── registry.py                      # NEW — canonical MissionRegistry + WorkPackageRegistry
│   │   ├── scan_service.py                  # NEW — canonical MissionScanService
│   │   ├── project_state.py                 # NEW — canonical ProjectStateService
│   │   └── sync_service.py                  # NEW — canonical SyncService + SyncTriggerResult
│   ├── cli/
│   │   └── commands/
│   │       └── dashboard.py                 # UPDATED — import from specify_cli.missions.registry
│   └── dashboard/
│       └── handlers/
│           ├── api.py                       # UPDATED — import from specify_cli.missions.*
│           └── features.py                  # UPDATED — import from specify_cli.missions.scan_service
│
└── dashboard/
    ├── services/
    │   ├── __init__.py                      # UNCHANGED (facade left for Phase C)
    │   ├── registry.py                      # REPLACED WITH SHIM → specify_cli.missions.registry
    │   ├── mission_scan.py                  # REPLACED WITH SHIM → specify_cli.missions.scan_service
    │   ├── project_state.py                 # REPLACED WITH SHIM → specify_cli.missions.project_state
    │   └── sync.py                          # REPLACED WITH SHIM → specify_cli.missions.sync_service
    └── api/
        ├── app.py                           # UPDATED — import from specify_cli.missions.registry
        ├── deps.py                          # UPDATED — import from specify_cli.missions.registry
        └── routers/
            ├── missions.py                  # UPDATED — import from specify_cli.missions.registry
            ├── health.py                    # UPDATED — import from specify_cli.missions.project_state
            └── sync.py                      # UPDATED — import from specify_cli.missions.sync_service

architecture/
└── 2.x/
    ├── shim-registry.yaml                   # UPDATED — 4 new shim entries
    └── adr/
        ├── README.md                        # UPDATED — cross-link new ADR
        └── 2026-05-07-1-dashboard-services-phase-b.md   # NEW ADR

tests/
├── architectural/
│   └── test_dashboard_boundary.py           # UPDATED — extended reciprocal assertion
└── specify_cli/
    └── missions/
        └── test_registry_cache.py           # NEW — P1 + P2 regression tests
```

**Structure Decision**: Single-project layout. New domain service modules are flat `.py`
files alongside the existing `api_types.py` inside `src/specify_cli/missions/`. This
is consistent with the pattern established by Mission C.

## Complexity Tracking

*No charter violations requiring justification.*

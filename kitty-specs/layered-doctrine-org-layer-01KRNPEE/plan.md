# Implementation Plan: Layered Doctrine Resolution — Org Layer

**Branch**: `feat/org-doctrine-layer` | **Date**: 2026-05-15 | **Spec**: [spec.md](spec.md)  
**Mission**: `layered-doctrine-org-layer-01KRNPEE` | **Merge target**: `feat/org-doctrine-layer`

---

## Summary

Extend spec-kitty's doctrine resolution stack from two layers (shipped + project) to three
(shipped + org + project). The org layer is a versioned doctrine pack — a validated local
snapshot of an organisation's governance artifacts — installed once per developer machine and
inherited by all projects automatically.

The technical work divides into three groups: (1) infrastructure changes to the doctrine loader
and `DoctrineService` that make three-layer resolution possible; (2) fetch tooling and pack
authoring commands for operators and doctrine maintainers; and (3) observability, provenance
surfacing, and user-facing documentation.

Precedence is `shipped < org < project`. ID collisions are resolved by full-replace (higher
layer wins entirely). Resolution reads only from local files — no runtime remote calls.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: ruamel.yaml (YAML parsing), Pydantic v2 (schema validation), typer
(CLI), rich (console output), requests (HTTPS bundle source), subprocess (git source — no
additional library)  
**Storage**: Filesystem only — `~/.kittify/org/<pack>/` for global snapshot; per-project
config in `.kittify/config.yaml` under a `doctrine.org` block  
**Testing**: pytest; unit tests for each changed module; integration tests for full three-layer
resolution chain and each fetch source type; property tests (hypothesis) for merge-semantics
invariants  
**Target Platform**: Linux, macOS, Windows (cross-platform; path handling via `pathlib`)  
**Performance Goals**: < 50 ms added latency for `charter context` over two-layer baseline
(packs ≤ 200 artifacts); `doctrine fetch` completes in < 30 s on standard broadband  
**Constraints**: No runtime remote calls; offline-capable after one-time fetch; backward
compatible — existing shipped + project tests must pass unchanged

---

## Charter Check

**Charter present**: yes (`.kittify/charter/charter.md`)  
**Template set**: `software-dev-default` (Python)  
**Active directives**: DIR-001, DIR-002, DIR-003, DIR-004  

| Gate | Status | Notes |
|---|---|---|
| Single project structure | ✅ Pass | `src/doctrine/`, `src/charter/`, `src/specify_cli/` — no new top-level projects |
| No repository pattern over direct access | ✅ Pass | Repositories pre-exist; org layer follows the same pattern |
| Test coverage requirement | ✅ Pass | Unit + integration + property tests planned |
| No new external runtime dependencies | ✅ Pass | `requests` is already in the dependency set; git via subprocess |
| Backward compatibility | ✅ Pass | C-006 — project-layer override behaviour unchanged; NFR-005 — all existing tests must pass |

No charter violations.

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/layered-doctrine-org-layer-01KRNPEE/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── checklists/
│   └── requirements.md
├── contracts/
│   ├── org-doctrine-source-api-contract.md   ← HTTP API source protocol
│   ├── pack-layout.md                         ← canonical pack directory spec
│   └── config-schema.yaml                     ← .kittify/config.yaml doctrine.org block
└── tasks/               ← Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── doctrine/
│   ├── base.py                    ← MODIFY: add _apply_org_overrides() + org_dir param
│   ├── service.py                 ← MODIFY: add org_roots: list[Path]
│   ├── drg/
│   │   ├── loader.py              ← MODIFY: add load_graph_or_dir(); extend merge_layers()
│   │   └── __init__.py            ← MODIFY: export load_graph_or_dir
│   ├── directives/repository.py   ← MODIFY: pass org_dir through
│   ├── tactics/repository.py      ← MODIFY: pass org_dir through
│   ├── styleguides/repository.py  ← MODIFY: pass org_dir through
│   ├── toolguides/repository.py   ← MODIFY: pass org_dir through
│   ├── paradigms/repository.py    ← MODIFY: pass org_dir through
│   ├── procedures/repository.py   ← MODIFY: pass org_dir through
│   ├── agent_profiles/repository.py   ← MODIFY: pass org_dir through
│   └── mission_step_contracts/repository.py ← MODIFY: pass org_dir through
│
├── charter/
│   ├── _drg_helpers.py            ← MODIFY: three-layer load_validated_graph()
│   ├── context.py                 ← MODIFY: route DRG load through helper; provenance
│   ├── compiler.py                ← MODIFY: route DRG load through helper
│   ├── reference_resolver.py      ← MODIFY: use load_graph_or_dir
│   └── synthesizer/
│       ├── validation_gate.py     ← MODIFY: use load_graph_or_dir
│       ├── project_drg.py         ← MODIFY: use load_graph_or_dir
│       ├── resynthesize_pipeline.py ← MODIFY: use load_graph_or_dir (2 sites)
│       └── write_pipeline.py      ← MODIFY: use load_graph_or_dir
│
└── specify_cli/
    ├── doctrine/                  ← NEW package
    │   ├── __init__.py
    │   ├── config.py              ← NEW: DoctrineOrgConfig model; load/save from .kittify/config.yaml
    │   ├── sources/               ← NEW: OrgDoctrineSource protocol + implementations
    │   │   ├── __init__.py
    │   │   ├── protocol.py        ← NEW: OrgDoctrineSource ABC
    │   │   ├── git_source.py      ← NEW: GitSource
    │   │   ├── https_source.py    ← NEW: HttpsBundleSource
    │   │   └── api_source.py      ← NEW: ApiSource
    │   ├── snapshot.py            ← NEW: write/read/validate local snapshot
    │   ├── pack_validator.py      ← NEW: pack validate logic
    │   └── pack_assembler.py      ← NEW: pack assemble logic
    │
    └── cli/commands/
        ├── doctrine.py            ← NEW: `spec-kitty doctrine` command group
        │                              (fetch, pack validate, pack assemble)
        ├── doctor.py              ← MODIFY: add org-layer listing subcommand/section
        └── charter.py             ← MODIFY: wire lint advisory for org-overrides-shipped

tests/
├── specify_cli/
│   └── doctrine/                  ← NEW
│       ├── test_config.py
│       ├── test_sources.py
│       ├── test_snapshot.py
│       ├── test_pack_validator.py
│       └── test_pack_assembler.py
└── doctrine/
    ├── test_base_org_layer.py     ← NEW: three-layer merge unit tests
    ├── test_service_org_layer.py  ← NEW: DoctrineService org_roots tests
    └── drg/
        └── test_loader_multifile.py  ← NEW: load_graph_or_dir tests

docs/
├── how-to/
│   └── create-an-org-doctrine-pack.md   ← NEW: pack authoring guide
└── migration/
    └── doctrine-local-overlay-to-org-layer.md ← NEW: migration from .kittify/doctrine/ local override
```

---

## Work Package Breakdown

| WP | Title | Primary files | Dependencies |
|---|---|---|---|
| WP01 | Multi-file DRG loading | `doctrine/drg/loader.py`; all `graph.yaml` call sites | — |
| WP02 | BaseDoctrineRepository org layer | `doctrine/base.py`; all 8 repository subclasses | WP01 |
| WP03 | DoctrineService org roots | `doctrine/service.py`; `charter/_drg_helpers.py` | WP02 |
| WP04 | OrgDoctrineSource protocol + implementations | `specify_cli/doctrine/sources/` | WP03 |
| WP05 | Config model + `doctrine fetch` command | `specify_cli/doctrine/config.py`, `doctrine/snapshot.py`, `specify_cli/cli/commands/doctrine.py` | WP04 |
| WP06 | `doctrine pack validate` + `doctrine pack assemble` | `specify_cli/doctrine/pack_validator.py`, `pack_assembler.py` | WP05 |
| WP07 | Provenance, `doctor`, `charter lint` | `charter/context.py`, `cli/commands/doctor.py`, `cli/commands/charter.py` | WP03 |
| WP08 | User guidance documentation | `docs/how-to/create-an-org-doctrine-pack.md`, `docs/migration/doctrine-local-overlay-to-org-layer.md` | WP06, WP07 |

WP01–WP03 form the infrastructure chain (must be sequential). WP04–WP06 are the operator surface chain. WP07 can start after WP03. WP08 requires WP06 and WP07 to be complete.

---

## Phase 0: Research

See [research.md](research.md) for full findings.

Key questions investigated:
1. Multi-file DRG loading strategy — single `load_graph_or_dir()` entry point
2. Three-layer merge semantics at the `_drg_helpers.py` level
3. `OrgDoctrineSource` protocol shape and authentication model
4. Config schema for `doctrine.org` block
5. `pack assemble` conflict detection and reporting model
6. Provenance tag shape in `charter context --json`
7. Doctor org-layer listing surface
8. Charter lint advisory warning placement

---

## Phase 1: Design

See [data-model.md](data-model.md) and [contracts/](contracts/) for full artifacts.

Key design outputs:
- `OrgDoctrineSource` protocol (ABC + three concrete implementations)
- `DoctrineOrgConfig` Pydantic model (config schema)
- Pack directory layout contract
- HTTP API source contract (for API source implementors)
- Three-layer merge invariants

# Implementation Plan: Org Doctrine Profile Integrity Activation Closure

**Branch**: `mission/org-doctrine-profile-integrity-activation-closure` | **Date**: 2026-06-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/org-doctrine-profile-integrity-activation-closure-01KT1TV1/spec.md`

**Branch contract**: Planning/base branch = `mission/org-doctrine-profile-integrity-activation-closure`; final merge target = `mission/org-doctrine-profile-integrity-activation-closure`. Current branch matches target.

## Summary

Close the release-critical charter/doctrine slice by making the **DRG the single canonical source of truth for doctrine relationships** (C-009) and the catalog trustworthy end-to-end. The mission: relocates the three-layer DRG merge from `charter` into `doctrine`; adds a `specializes_from` relation; performs a **hard cutover** retiring the `enhances`/`overrides`/`specializes_from` *fields* in favour of DRG-fragment authoring across all nine kinds (a classified bulk edit); surfaces invalid-profile load diagnostics through a shared health report so `doctor doctrine` cannot report false-healthy; makes charter activation validate-before-write with real cascade scope and shared-reference-safe deactivation; wires `OperationalContext` at runtime entry points and prunes the now-live dead-symbol allowlist entries; consolidates the fragmented kind/ID vocabulary into one canonical resolver; and makes templates a discoverable, DRG-addressable kind (#1333). Delivered as one mission with many granular WPs sequenced by dependency.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, pydantic, ruamel.yaml (existing spec-kitty deps); stdlib only for new graph traversal
**Storage**: Filesystem only — doctrine YAML artifacts, DRG fragments (`drg/fragment.yaml` / `graph.yaml`), `.kittify/config.yaml`; no database
**Testing**: pytest, ATDD-first (charter C-011 binding); ruff + mypy + dead-symbol + layer-rule architectural suites as gates
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows 10+), Python package distributed via PyPI
**Project Type**: single (CLI library — `src/specify_cli/`, `src/charter/`, `src/doctrine/`, `src/kernel/`)
**Performance Goals**: `doctor doctrine` ≤ 2s on built-in + one-pack fixture (NFR-001); profile diagnostics deterministic (NFR-002)
**Constraints**: Layer order `kernel ← doctrine ← charter ← specify_cli` strictly enforced (C-006, C-008); activation failure paths non-mutating (NFR-003); no new worktrees/status events on precondition failure (NFR-004); built-in artifacts load with zero diagnostics (NFR-005); architectural suites green for in-scope symbols (NFR-006); zero relationship-loss on the field→fragment migration (NFR-007)
**Scale/Scope**: 9 doctrine artifact kinds; 36 functional requirements; 12 scenarios; ~5 dependency waves of granular WPs; `change_mode: bulk_edit` (see `occurrence_map.yaml`)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Charter present at `.kittify/charter/charter.md`. Relevant binding items and disposition:

| Charter item | Disposition |
|--------------|-------------|
| Architecture: Shared Package Boundaries; layer order `kernel ← doctrine ← charter ← specify_cli` | **Honored.** Merge relocation moves logic *down* into `doctrine` (allowed); `charter` aggregates over it. No doctrine→charter/specify_cli import (C-006). Org/project root resolution stays in `specify_cli`, passed as data (C-008). |
| `__all__` Declaration Convention (binding, C-007) + dead-symbol gate | **Honored & advanced.** FR-035/FR-036 wire `CharterPackConfigError`, remove the 2 charter sub-app exports, and drop 7 stale allowlist entries. The 2 git/lanes offenders are documented pre-existing `main` regressions (Out of Scope); allowlist-with-tracker fallback per NFR-006. |
| ATDD-First Discipline (binding, C-011) | **Honored.** Each scenario gets acceptance tests first (`DIRECTIVE_034`, `acceptance-test-first`). |
| Test and Typecheck Quality Gate (`DIRECTIVE_030`) | **Honored.** ruff/mypy/pytest per WP. |
| Doctrine Versioning Requirement (`DIRECTIVE_018`) | **Honored.** Schema/relation-vocabulary changes (relation removal, `specializes_from`, `template` kind) carry doctrine version bumps. |
| Bulk Edit Occurrence Classification (`DIRECTIVE_035`) | **Honored.** Mission is `change_mode: bulk_edit`; `occurrence_map.yaml` classifies the field-retirement surface. |
| Decision Documentation Requirement (`DIRECTIVE_003`) | **Honored.** Five plan decisions recorded in the decision-moment thread; an ADR captures the DRG-source-of-truth + merge relocation. |
| Regression Vigilance / Pre-existing Failure Reporting | **Honored.** The dead-symbol red baseline is documented (R-011) and triaged per-offender. |

No unresolved Charter violations. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```
kitty-specs/org-doctrine-profile-integrity-activation-closure-01KT1TV1/
├── plan.md              # This file
├── spec.md              # Feature specification (committed, substantive)
├── research.md          # R-001..R-013 (decisions + R-011 pre-impl review)
├── data-model.md        # Phase 1 output (this command)
├── quickstart.md        # Phase 1 output (this command)
├── contracts/           # Phase 1 output (this command)
├── occurrence_map.yaml  # Bulk-edit classification (this command)
├── decisions/           # Decision-moment artifacts (DM-*.md)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── kernel/                         # errors, base types (unchanged)
├── doctrine/                       # OWNS relationship models + canonical DRG merge (C-009)
│   ├── artifact_kinds.py           # ArtifactKind — extended into the canonical kind/ID resolver
│   ├── drg/
│   │   ├── models.py               # + Relation.SPECIALIZES_FROM; DRGGraph.edges_to (reverse index)
│   │   ├── loader.py               # built-in graph loading
│   │   ├── org_pack_loader.py      # fragment loading; augmentation auto-emit (single source)
│   │   ├── merge.py                # NEW: merge_three_layers relocated here (from charter/drg.py)
│   │   └── query.py                # walk_edges / resolve_transitive_refs / reverse reachability
│   ├── agent_profiles/
│   │   ├── repository.py           # SkippedProfile diagnostics; lineage resolves via DRG traversal
│   │   └── schema_models.py        # relationship fields removed (hard cutover)
│   ├── directives|toolguides|missions/models.py   # relationship fields removed
│   ├── templates/ + missions/<m>/templates/       # discoverable; mission-qualified template IDs
│   ├── resolver.py                 # template resolution → DRG-addressable
│   └── service.py                  # agent_profiles diagnostics preserved across construction
├── charter/                        # AGGREGATES activation-aware views over doctrine-merged DRG
│   ├── drg.py                      # thin caller of doctrine merge + activation filtering
│   ├── pack_manager.py             # canonical kind/ID resolver use; plan/commit activation seam
│   ├── context.py                  # --include via canonical kinds incl. agent-profile + template
│   ├── pack_context.py             # CharterPackConfigError (now caught externally)
│   ├── consistency_check.py        # cross-kind refs via resolved IDs (no kind-only workaround)
│   └── cascade.py                  # NEW: scoped cascade + shared-reference analysis
├── charter/invocation_context.py   # build_operational_context() pure assembler
└── specify_cli/
    ├── cli/commands/charter/{activate,deactivate,list_cmd,context}.py
    ├── cli/commands/doctor.py      # DoctrineHealthReport (shared human/JSON)
    ├── doctrine/{config.py,pack_validator.py}      # org/project roots as data; augmentation set
    ├── cli/commands/{implement.py,agent/workflow.py}  # OperationalContext at claim
    └── next/runtime_bridge.py      # OperationalContext at next decision

tests/
├── architectural/                  # layer rules + dead-symbol (relocation + FR-036)
├── doctrine/ + charter/            # unit + contract
└── specify_cli/                    # CLI black-box (DIRECTIVE_036)
```

**Structure Decision**: Single-project layout. The defining structural move is relocating relationship-merge ownership into `src/doctrine/drg/` (new `merge.py`) and reducing `src/charter/drg.py` to an activation-aware aggregator — the concrete realization of C-009 + OQ-2(ii) under the existing layer rule.

## Complexity Tracking

*No Charter Check violations; section intentionally empty.*

## Phase 0 — Research

Complete. Consolidated in [research.md](research.md): R-001..R-008 (relation naming, invalid-profile model, doctor semantics, validation-before-mutation, cascade, OperationalContext, selector reachability, catalog completeness), R-009 (kind/ID consolidation), R-010 (augmentation coverage + mission-type asymmetry), R-011 (pre-implementation code review with file:line anchors and long-method splits), R-012 (DRG source of truth — OQ-2 resolved: DRG-fragment-only authoring + doctrine-owned merge), R-013 baked into R-011 (#1333 templates). Five plan decisions resolved and verified clean.

## Phase 1 — Design & Contracts

Outputs generated by this command:
- [data-model.md](data-model.md) — entities/value objects, invariants, the canonical kind/ID model, DRG relation + reverse index, `SkippedProfile`, `DoctrineHealthReport`, cascade scope, `OperationalContext`, template identity.
- [contracts/](contracts/) — behavioral contracts for the relocated doctrine merge + layer rule, the kind/ID resolver, fragment-authoring validation (fields rejected), augmentation auto-emit parity, cascade scope + shared-reference deactivation, activation non-mutation, profile diagnostics determinism, doctor health report, `charter context --include` / `list --all`, template discovery/addressing, and the dead-symbol/`CharterPackConfigError` wiring.
- [quickstart.md](quickstart.md) — operator/dev walkthroughs proving the acceptance signals of Scenarios 1–12.
- [occurrence_map.yaml](occurrence_map.yaml) — bulk-edit classification of the relationship-field retirement across all 8 categories.

### WP sequencing (dependency-ordered; granular)

- **Wave 0 — foundation**: canonical kind/ID resolver (R-009/FR-027); `Relation.SPECIALIZES_FROM` + org-fragment silent-drop fix (FR-001/FR-002); **relocate `merge_three_layers` into `doctrine.drg`** with layer-rule + behavior contracts (C-009/OQ-2-ii).
- **Wave 1 — diagnostics integrity (low-risk, high-value)**: `SkippedProfile` loader diagnostics + dedup of the 3 layer loops (FR-005..007, NFR-002/005); `DoctrineHealthReport` + doctor human/JSON + false-healthy fix (FR-008..010, NFR-001); `CharterPackConfigError` wiring + 7 stale-allowlist removals + sub-app export cleanup (FR-035/FR-036/FR-020).
- **Wave 2 — DRG authority + bulk-edit migration**: DRG-fragment authoring + **hard-cutover field retirement across 9 kinds** (FR-001/003/004, FR-028..032, C-009, NFR-007) — governed by `occurrence_map.yaml`; profile hierarchy resolver onto DRG traversal; augmentation auto-emit/validator parity from a single source (FR-030/031).
- **Wave 3 — activation**: catalog-backed dual-ID resolver; `plan_activation`/`commit_plan` seam (FR-011/012, NFR-003); cascade scope threading + `--cascade all` (FR-013/014); `edges_to` reverse index + shared-reference-safe deactivation (FR-015/016, C-005).
- **Wave 4 — runtime + catalog UX**: `OperationalContext` pure assembler + wiring at claim/next, then FR-019 allowlist prune + FR-020 cleanup (FR-017..020, C-006, NFR-004); `charter list --all` + `--include` agent-profile/template (FR-022..026); **#1333** template discovery + mission-qualified DRG template nodes (FR-033/034).

Each wave is decomposed into many small WPs in `/spec-kitty.tasks`; dependencies gate cross-wave WPs (Wave 0 unblocks all; Wave 2 depends on Wave 0 merge relocation + resolver).

### Re-evaluated Charter Check (post-design)

No new violations introduced by the design. The merge relocation strengthens the layer boundary rather than weakening it; the bulk-edit classification satisfies `DIRECTIVE_035`; the dead-symbol changes move the gate toward green for in-scope symbols.

## Branch Strategy (restated)

- Current branch at plan start: `mission/org-doctrine-profile-integrity-activation-closure`
- Planning/base branch: `mission/org-doctrine-profile-integrity-activation-closure`
- Final merge target: `mission/org-doctrine-profile-integrity-activation-closure`
- `branch_matches_target`: true

**Next suggested command**: `/spec-kitty.tasks` (user must invoke explicitly).

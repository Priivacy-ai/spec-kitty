# Implementation Plan: Runtime Mission Execution Extraction

**Branch contract**: planning/base `main` → merge target `main` (single branch; no divergence)
**Date**: 2026-04-17
**Spec**: [./spec.md](./spec.md)
**Mission ID**: `01KPDYGWKZ3ZMBPRX9RYMWPR1A` · **mid8**: `01KPDYGW`
**Change mode**: `bulk_edit` (DIRECTIVE_035 applies; see `./occurrence_map.yaml`)
**Trackers**: [#612 — Extract runtime/mission execution](https://github.com/Priivacy-ai/spec-kitty/issues/612)
**Umbrella epic**: [#461 — Charter as Synthesis & Doctrine Reference Graph](https://github.com/Priivacy-ai/spec-kitty/issues/461)
**Exemplar**: `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` (FR-016)

---

## Summary

Spec Kitty's runtime execution core — mission discovery, state sequencing, state-transition decisioning, execution-layer interaction, profile/action invocation, active-mode handling, and charter-artefact retrieval — currently lives scattered across two sibling subtrees under `specify_cli`:

- `src/specify_cli/next/` — 4 modules, ~1,918 lines. Owns decisioning (`decision.py`, 472 lines), runtime bridging (`runtime_bridge.py`, 1,087 lines), prompt composition (`prompt_builder.py`, 342 lines), public API (`__init__.py`, 17 lines).
- `src/specify_cli/runtime/` — 10 modules, ~1,842 lines. Owns agent command dispatch (`agent_commands.py`), agent skill resolution (`agent_skills.py`), status bootstrap (`bootstrap.py`), doctor diagnostics (`doctor.py`), home resolution (`home.py`), merge orchestration (`merge.py`), migration orchestration (`migrate.py`), mission resolution (`resolver.py`), origin display (`show_origin.py`).

Combined, ~3,760 lines constitute the runtime extraction surface. This mission consolidates both subtrees into a **single canonical top-level package** at `src/runtime/` (per FR-001 and the upstream #610 ownership map). The CLI modules under `src/specify_cli/cli/commands/` become thin adapters: argument parsing, runtime service calls, Rich/JSON rendering, exit-code mapping — no inline state-machine decisioning (FR-004).

The extraction follows the charter pattern exactly: canonical implementation at a top-level package, thin re-export shim at the legacy `specify_cli.*` path with `DeprecationWarning` emission per the #615 rulebook (FR-005/FR-006), one-release deprecation window, registry entry in `architecture/2.x/shim-registry.yaml`.

Runtime is the heart of every CLI command. Extraction must preserve existing semantics bit-for-bit (C-001): `spec-kitty next`, `spec-kitty implement`, `spec-kitty agent action review`, and `spec-kitty merge` produce identical `--json` output, exit codes, and normalized stderr messages before and after. This is proved by four JSON regression fixtures captured in the first work package (FR-011/FR-012).

Two scaffolding seams ship with the extraction, but no implementations (C-002):

- `ProfileInvocationExecutor` Protocol (FR-009) — #461 Phase 4 implements against it.
- `StepContractExecutor` Protocol (FR-010) — #461 Phase 6 implements against it.

A third Protocol, `PresentationSink` (FR-013), lets runtime surface output without importing `rich.*` or `typer.*`. CLI adapters inject a Rich-backed implementation; runtime itself stays presentation-agnostic (C-009).

Dependency rules for the runtime slice are recorded in the #610 ownership map's runtime slice entry (FR-007). Enforcement uses the **existing pytestarch infrastructure** at `tests/architectural/test_layer_rules.py` — we extend the `_DEFINED_LAYERS` fixture to add a `runtime` layer and assert runtime cannot import from `specify_cli.cli.*`, `rich.*`, or `typer.*`. No new test dependency and no new test file is required (FR-008).

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement).
**Primary Dependencies**: Existing — `typer`, `rich` (CLI-layer only; forbidden in runtime), `ruamel.yaml`, `pytest`, `pytestarch` (already used by `tests/architectural/test_layer_rules.py`), `mypy --strict`.
**Storage**: Filesystem only. No schema or on-disk data changes. Runtime does not own storage; it orchestrates the modules that do.
**Testing**: pytest. New regression harness at `tests/regression/runtime/` owns four JSON fixture snapshots plus a dict-equal comparator. Architectural enforcement extends `tests/architectural/test_layer_rules.py` (spec calls this location `tests/architecture/` — the on-disk spelling is `architectural/`; we keep the existing spelling and note the drift in research.md for future cleanup). Coverage goal ≥ 90% on any new runtime code (NFR-002 per charter policy).
**Target Platform**: Developer machines and CI (Linux, macOS). No runtime platform surface change.
**Project Type**: Single project, internal Python package move + shim installation + regression harness.
**Performance Goals**: Regression suite ≤ 30s on CI (NFR-001). Runtime CLI latency within ±10% of baseline (NFR-003). Dependency-rules pytest ≤ 5s (NFR-005).
**Constraints**: No CLI UX changes (C-004); no `pyproject.toml` version bump (C-006); no `ProfileInvocationExecutor` or `StepContractExecutor` implementations (C-002); no glossary runtime middleware (C-003); no model-discipline doctrine port (C-005); external Python importers of `specify_cli.next.*` and `specify_cli.runtime.*` get one-minor-cycle deprecation window via shims; runtime must not import from `specify_cli.cli.*`, `rich.*`, or `typer.*` (C-009).
**Scale/Scope**: ~3,760 lines of Python move from `specify_cli/next/` + `specify_cli/runtime/` to top-level `src/runtime/`. ~109 internal call-site rewrites across 1 src file (`src/specify_cli/cli/commands/next_cmd.py`) and 8 test files. 2 shim packages installed (`src/specify_cli/next/*` and `src/specify_cli/runtime/*`). 2 registry entries in `architecture/2.x/shim-registry.yaml`. 4 JSON regression fixtures under `tests/regression/runtime/fixtures/`. 1 migration doc at `docs/migration/runtime-extraction.md`. 1 new Protocol set (`PresentationSink`, `ProfileInvocationExecutor`, `StepContractExecutor`). 1 architectural layer added to the pytestarch landscape fixture.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-evaluated after Phase 1 design.*

| Directive / Policy | Applies to this mission? | Compliance plan |
|---|---|---|
| **DIRECTIVE_003** — Decision Documentation | Yes | Canonical-path decision, shim sunset window, seam-Protocol shapes, and regression-harness design are captured in `plan.md`, `research.md`, `data-model.md`, `docs/migration/runtime-extraction.md`, and `CHANGELOG.md`. ADR not required (decisions are structural port of the charter pattern, not a novel architectural trade-off). |
| **DIRECTIVE_010** — Specification Fidelity | Yes | All 16 FRs, 5 NFRs, and 9 constraints in `spec.md` map to tasks in Phase 2 (see `tasks.md` after `/spec-kitty.tasks`). FR-to-WP coverage is verified by `/spec-kitty.analyze`. |
| **DIRECTIVE_035** — Bulk-edit classification | Yes | `meta.json` has `change_mode: bulk_edit`. `occurrence_map.yaml` is authored in this plan phase (see `./occurrence_map.yaml`) and enumerates every `specify_cli.next` and `specify_cli.runtime` import migrated to the canonical `runtime` package. |
| **Test coverage ≥ 90%** on new code | Yes | Applies to new Protocol module (`src/runtime/seams/`) and the regression harness. Shim modules are purely additive (re-export + `DeprecationWarning`) and are covered by dedicated shim tests. |
| **`mypy --strict` must pass** | Yes | New Protocol module and moved code keep type annotations; CI enforces. |
| **Integration tests for CLI commands** | Yes | No new CLI commands (C-004). Behavioral invariance is proved by the four JSON regression fixtures (FR-011/FR-012) running against a representative mission checked into `tests/regression/runtime/fixtures/reference_mission/`. |
| **Terminology canon (C-008)** | Yes | All new artefacts use **Mission**, **Work Package**, **Runtime**, **Shim**, **Seam**, **PresentationSink**. The glossary mission (#613) will normalize these across the repo; this mission aligns with that canon now. |

**Gate status**: PASS. No charter conflicts. No complexity-tracking entries needed.

## Project Structure

### Documentation (this mission)

```
kitty-specs/runtime-mission-execution-extraction-01KPDYGW/
├── spec.md                  # /spec-kitty.specify output
├── meta.json                # mission identity + change_mode: bulk_edit
├── plan.md                  # THIS FILE (/spec-kitty.plan output)
├── research.md              # Phase 0 output — unknowns resolved
├── data-model.md            # Phase 1 output — Protocol shapes, seam contracts
├── quickstart.md            # Phase 1 output — how a contributor reads the new layout
├── contracts/               # Phase 1 output — PresentationSink / Executor Protocol IDL
│   ├── presentation_sink.md
│   ├── profile_invocation_executor.md
│   └── step_contract_executor.md
├── occurrence_map.yaml      # DIRECTIVE_035 bulk-edit classification
├── checklists/
│   └── requirements.md      # Spec-phase quality checklist (already complete)
└── tasks/                   # Populated by /spec-kitty.tasks
```

### Source Code (repository root)

Only touched paths are listed. Single-project Python layout; the move reshapes import ownership, not product topology.

```
src/runtime/                                      # NEW canonical runtime package (FR-001)
├── __init__.py                                   # NEW — public API re-exports
├── decisioning/                                  # NEW — state-transition decisioning (was specify_cli/next/decision.py)
│   ├── __init__.py
│   └── decision.py                               # moved from specify_cli/next/decision.py
├── bridge/                                       # NEW — runtime bridge orchestration (was specify_cli/next/runtime_bridge.py)
│   ├── __init__.py
│   └── runtime_bridge.py                         # moved from specify_cli/next/runtime_bridge.py
├── prompts/                                      # NEW — prompt composition (was specify_cli/next/prompt_builder.py)
│   ├── __init__.py
│   └── builder.py                                # moved from specify_cli/next/prompt_builder.py
├── discovery/                                    # NEW — mission discovery (was specify_cli/runtime/resolver.py, home.py)
│   ├── __init__.py
│   ├── resolver.py                               # moved from specify_cli/runtime/resolver.py
│   └── home.py                                   # moved from specify_cli/runtime/home.py
├── agents/                                       # NEW — agent dispatch and skill resolution
│   ├── __init__.py
│   ├── commands.py                               # moved from specify_cli/runtime/agent_commands.py
│   └── skills.py                                 # moved from specify_cli/runtime/agent_skills.py
├── orchestration/                                # NEW — merge/migrate/bootstrap/doctor/origin
│   ├── __init__.py
│   ├── bootstrap.py                              # moved from specify_cli/runtime/bootstrap.py
│   ├── merge.py                                  # moved from specify_cli/runtime/merge.py
│   ├── migrate.py                                # moved from specify_cli/runtime/migrate.py
│   ├── doctor.py                                 # moved from specify_cli/runtime/doctor.py
│   └── show_origin.py                            # moved from specify_cli/runtime/show_origin.py
└── seams/                                        # NEW — Protocol surface (FR-009, FR-010, FR-013)
    ├── __init__.py
    ├── presentation_sink.py                      # NEW — PresentationSink Protocol
    ├── profile_invocation_executor.py            # NEW — ProfileInvocationExecutor Protocol (no impl per C-002)
    └── step_contract_executor.py                 # NEW — StepContractExecutor Protocol (no impl per C-002)

src/specify_cli/next/                             # Legacy shim surface — deprecated-in-place (FR-005)
├── __init__.py                                   # EDIT — add warnings.warn + 4 deprecation constants, re-export from runtime
├── decision.py                                   # EDIT — convert to pure re-export shim (no logic)
├── prompt_builder.py                             # EDIT — convert to pure re-export shim
└── runtime_bridge.py                             # EDIT — convert to pure re-export shim

src/specify_cli/runtime/                          # Legacy shim surface — deprecated-in-place (FR-005)
├── __init__.py                                   # EDIT — add warnings.warn + 4 deprecation constants, re-export from runtime
├── agent_commands.py                             # EDIT — convert to pure re-export shim
├── agent_skills.py                               # EDIT — convert to pure re-export shim
├── bootstrap.py                                  # EDIT — convert to pure re-export shim
├── doctor.py                                     # EDIT — convert to pure re-export shim
├── home.py                                       # EDIT — convert to pure re-export shim
├── merge.py                                      # EDIT — convert to pure re-export shim
├── migrate.py                                    # EDIT — convert to pure re-export shim
├── resolver.py                                   # EDIT — convert to pure re-export shim
└── show_origin.py                                # EDIT — convert to pure re-export shim

src/specify_cli/cli/commands/                     # Thin adapters (FR-004) — in-place edit, no shim
├── next_cmd.py                                   # EDIT — rewrite imports: specify_cli.next → runtime; adapter only
├── implement.py                                  # EDIT — ensure only adapter logic; imports from runtime
├── merge.py                                      # EDIT — ensure only adapter logic; imports from runtime
└── agent/workflow.py                             # EDIT — review/action dispatch adapter; imports from runtime

architecture/2.x/
└── shim-registry.yaml                            # EDIT — add runtime-slice entries per #615 (2 shims)

tests/architectural/
├── conftest.py                                   # EDIT — extend `landscape` fixture: add `runtime` layer
└── test_layer_rules.py                           # EDIT — extend _DEFINED_LAYERS; add runtime forbidden-import rules

tests/regression/runtime/                         # NEW — behaviour-preservation harness (FR-011, FR-012)
├── __init__.py
├── fixtures/
│   ├── reference_mission/                        # NEW — checked-in representative mission
│   │   ├── meta.json
│   │   ├── spec.md
│   │   ├── plan.md
│   │   ├── tasks.md
│   │   ├── tasks/WP01-*.md                       # minimal WP sufficient to exercise next/implement/review/merge
│   │   └── status.events.jsonl                   # pre-baked lane events
│   └── snapshots/
│       ├── next.json                             # baseline spec-kitty next --json
│       ├── implement.json                        # baseline agent action implement --json
│       ├── review.json                           # baseline agent action review --json
│       └── merge.json                            # baseline merge --json
└── test_runtime_regression.py                    # NEW — dict-equal assertions + exit code + normalized stderr

tests/
└── (128+ existing tests — updated per occurrence_map.yaml tests_fixtures:rename)

docs/migration/
└── runtime-extraction.md                         # NEW — migration guide with import-path translation table (FR-014)

CHANGELOG.md                                      # EDIT — add entry citing mission and exemplar
```

**Structure Decision**: Single top-level `src/runtime/` package mirrors the charter consolidation exemplar. Internal subdivision (`decisioning/`, `bridge/`, `prompts/`, `discovery/`, `agents/`, `orchestration/`, `seams/`) preserves module boundaries from the pre-extraction layout, so reviewers can trace every moved file to its origin. The `seams/` subpackage isolates the three Protocol surfaces so #461 Phase 4/6 implementers can import them without depending on any runtime internals.

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified.*

**None.** No violations; no entries required.

---

## Phase 0: Outline & Research — unknowns resolved

All five plan-phase open questions from `spec.md` Open Questions are resolved. See [`./research.md`](./research.md) for full evidence and alternatives. Summary:

- **Q1 Final canonical runtime path**: `src/runtime/` (top-level package). The existing `src/specify_cli/runtime/` subpackage is folded into it and becomes a deprecation shim. Sibling mission #610 will ratify the path in its ownership map; if the map picks a different path, this plan updates its references accordingly (A1 from spec).
- **Q2 Full shim enumeration**: Two shim packages — `src/specify_cli/next/` (4 files) and `src/specify_cli/runtime/` (10 files). CLI command modules at `src/specify_cli/cli/commands/` do **not** become shims; they remain in place as thin adapters (FR-004) and rewrite their imports to target the new `runtime.*` package.
- **Q3 PresentationSink protocol + seam shapes**: See `contracts/presentation_sink.md`, `contracts/profile_invocation_executor.md`, `contracts/step_contract_executor.md`. All three live in `src/runtime/seams/`. Runtime never imports Rich or Typer; CLI adapters inject a `RichPresentationSink` implementation.
- **Q4 #395 infrastructure presence**: **Present**. `tests/architectural/test_layer_rules.py` uses `pytestarch.LayerRule` with a `landscape` fixture covering kernel/doctrine/charter/specify_cli. Plan extends the fixture to add a `runtime` layer and asserts forbidden edges (no `specify_cli.cli.*`, no `rich.*`, no `typer.*` imports into runtime). No new dependency, no new test file.
- **Q5 Regression-snapshot command enumeration**: Four commands confirmed: `spec-kitty next`, `spec-kitty implement <WP>`, `spec-kitty agent action review <WP>`, `spec-kitty merge`. Additional CLI commands audited (`agent mission`, `agent tasks status`, `agent context`, `dashboard`, `doctor`, `sync`) — none directly invoke the state-transition decisioning function `decide_next`, so they do not need regression snapshots. Coverage for those commands stays under their existing test modules.

## Phase 1: Design & Contracts

- **Data model** ([`./data-model.md`](./data-model.md)): Protocol shapes for `PresentationSink`, `ProfileInvocationExecutor`, `StepContractExecutor`; type references for `ProfileRef`, `InvocationContext`, `InvocationResult`, `StepContract`, `ExecutionContext`, `StepResult`.
- **Contracts** ([`./contracts/`](./contracts/)): formal IDL for each Protocol, including minimal stub implementations that compile and type-check (validation per Success Criterion 5).
- **Quickstart** ([`./quickstart.md`](./quickstart.md)): how a contributor navigates the new `src/runtime/` layout, where each moved module landed, and how to add new runtime features.

**Post-Phase 1 Charter Re-Check**: PASS. The Protocol surfaces are minimal (3 files under `src/runtime/seams/`), add no new runtime dependencies beyond stdlib `typing.Protocol`, and do not violate C-002 (interfaces only, no implementations).

---

## Dependencies & Sequencing

**Upstream (must land before implementation starts):**

1. `functional-ownership-map-01KPDY72` (#610) — pins the canonical runtime path and publishes the runtime-slice dependency-rules entry this mission's pytestarch test references.
2. `migration-shim-ownership-rules-01KPDYDW` (#615) — provides the shim rulebook (`__deprecated__`, `__canonical_import__`, `__removal_release__`, `__deprecation_message__`, `DeprecationWarning` stacklevel=2) and the `architecture/2.x/shim-registry.yaml` registry + `spec-kitty doctor shim-registry` CI check that this mission's shims register against.

This mission's plan phase can be authored in parallel with the two upstream plans. The **implementation** phase of this mission waits for both upstream missions to merge, because:

- Without #610 merged, the canonical runtime path is not authoritative; picking a path prematurely risks a re-rename.
- Without #615 merged, the shim attribute contract is not ratified and the registry file does not exist.

**Downstream (blocked on this mission merging):**

- **#461 Phase 4** (ProfileInvocationExecutor) — implements against the `ProfileInvocationExecutor` Protocol in `src/runtime/seams/`.
- **#461 Phase 6** (StepContractExecutor) — implements against the `StepContractExecutor` Protocol in `src/runtime/seams/`.
- **#613 glossary extraction** — benefits from the stable runtime interface but is not strictly blocked; it can proceed in parallel with this mission's implementation phase if its scope is limited to the `glossary` package.

**Critical path within this mission** (enforced by task ordering in `/spec-kitty.tasks`):

1. **Regression baseline capture** — run the four CLI commands on the reference mission and commit the JSON snapshots BEFORE any code moves. This is the behaviour-preservation anchor.
2. **Package move** — relocate modules from `specify_cli/next/` and `specify_cli/runtime/` to `src/runtime/`. Keep the old paths temporarily as re-export lines so the test suite continues to pass during the move.
3. **Adapter conversion** — rewrite `src/specify_cli/cli/commands/next_cmd.py`, `implement.py`, `merge.py`, `agent/workflow.py` to import from `runtime` and delegate.
4. **Shim installation** — collapse `src/specify_cli/next/*` and `src/specify_cli/runtime/*` to pure re-export shims per #615 contract; add registry entries.
5. **Dependency-rules test** — extend `tests/architectural/test_layer_rules.py` landscape fixture to add the `runtime` layer and assert forbidden edges.
6. **Migration doc** — write `docs/migration/runtime-extraction.md`.
7. **Bulk-edit occurrence migration** — apply the `occurrence_map.yaml` category actions across the 109 call sites.
8. **Regression assertion** — re-run the four CLI commands against the post-extraction tree; confirm dict-equal match with the committed fixtures.

Steps 1 and 2 gate everything else. Steps 3 and 4 can execute in parallel after step 2 completes. Step 5 depends on step 4 (shim registry entries must exist before the layer test references them). Steps 6 and 7 can execute in parallel after step 3.

---

## Success Criteria Mapping

| Spec Success Criterion | Mapped plan artefacts |
|---|---|
| **SC-1 Behaviour invariance** | Phase 0 WP captures baseline; Phase 8 WP asserts dict-equal post-extraction. Covers FR-011/FR-012, NFR-001, NFR-003. |
| **SC-2 Package boundary cleanness** | Phase 5 WP extends pytestarch landscape fixture. Covers FR-007/FR-008, NFR-005, C-009. |
| **SC-3 Adapter conversion complete** | Phase 3 WP rewrites CLI modules. Covers FR-004. Code-review walkthrough as acceptance gate. |
| **SC-4 Deprecation contract honoured** | Phase 4 WP installs shims + registry entries. Covers FR-005/FR-006. `spec-kitty doctor shim-registry` from #615 validates. |
| **SC-5 Downstream seams usable** | Phase 1 contracts include minimal stub implementations for `ProfileInvocationExecutor` and `StepContractExecutor` that compile and type-check. Validated in research.md. Covers FR-009/FR-010, C-002. |
| **SC-6 Zero regression** | Phase 8 WP runs full `tests/` suite. Covers NFR-002. |
| **SC-7 Migration doc and PR citations** | Phase 6 WP writes `docs/migration/runtime-extraction.md`. PR description template cites the charter exemplar and the ownership-map slice. Covers FR-014/FR-016. |

---

## Branch Strategy (restated per protocol)

- **Planning base**: `main`
- **Merge target**: `main`
- **Current branch**: `main` (this mission is being planned directly on main, with implementation landing on a lane-based execution workspace created by `spec-kitty implement WP##` per the 2.x/3.x lane strategy).
- **Branch divergence**: none.

---

## Out-of-Scope Reminders (from spec)

- No `ProfileInvocationExecutor` or `StepContractExecutor` **implementations** in this mission (C-002). Seams only.
- No glossary runtime middleware (C-003; belongs to #613 / #461 Phase 5).
- No CLI UX changes (C-004). Command names, argument shapes, output formats stay identical.
- No model-discipline doctrine port (C-005).
- No `pyproject.toml` version bump (C-006). Release is cut by an upstream maintainer on a separate mission.
- No refactor of the mission state machine semantics or lane arbitration (C-001). This is a pure move + adapter conversion.
- No new CLI commands.

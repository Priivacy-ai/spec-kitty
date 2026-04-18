# Implementation Plan: Glossary Functional Module Extraction

**Branch contract**: planning/base `main` → merge target `main` (single branch; no divergence; `branch_matches_target=true` at setup)
**Date**: 2026-04-17
**Spec**: [./spec.md](./spec.md)
**Mission ID**: `01KPDYM9H8WGXC6HH6YKEQR9Q6` · **mid8**: `01KPDYM9`
**Change mode**: `bulk_edit` (DIRECTIVE_035 applies; see [./occurrence_map.yaml](./occurrence_map.yaml))
**Exemplar**: `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` (per FR-014)

---

## Summary

The canonical Glossary package is carved out of `src/specify_cli/glossary/` into `src/glossary/`, mirroring the charter-extraction pattern and the #615 shim rulebook exactly. Pre-move baseline inventory shows:

- **17 modules** under `src/specify_cli/glossary/` (5 756 LOC total incl. CLI), of which 15 are runtime/integrity modules targeted for the canonical package.
- **One CLI module**: a single 700-line `src/specify_cli/cli/commands/glossary.py` file (NOT a subdirectory). It imports private helpers (`_parse_sense_status`, `load_seed_file`) from `specify_cli.glossary.scope`, so the adapter conversion must either promote these helpers to the public canonical surface or migrate the CLI to a public equivalent (FR-005, spec edge case).
- **Two rendering/CLI-coupled modules** inside `src/specify_cli/glossary/`:
  - `rendering.py` (179 LOC) imports `rich.*` directly → must move to the CLI adapter layer (FR-003, FR-004, C-007).
  - `prompts.py` (210 LOC) imports `typer` directly → must move to the CLI adapter layer (FR-004, C-007).
- **41 files, ~243 `specify_cli.glossary` import occurrences** to migrate under `occurrence_map.yaml` (FR-009).
- **One runtime caller already exists** at `src/kernel/glossary_runner.py` — migrates to the canonical import path as part of the bulk rename; future #612 runtime code consumes the same canonical surface (acceptance scenario 7).
- The current `src/specify_cli/glossary/__init__.py` (202 LOC) already exposes a well-defined public `__all__`; the extraction preserves it identically at `src/glossary/__init__.py`. This keeps the deprecation window's re-export table mechanical.

The Mission adds **one dedicated pre-move Work Package — the Entanglement Inventory** — per FR-008, before any code moves. The Work Package produces `docs/migration/glossary-extraction.md#entanglement-inventory`, enumerating every call site with a `migrate` / `adapter` / `grandfathered` tag.

No new Glossary features, no graph-backed addressing seam, no CLI UX changes, no version bump, no touch to the repo-root `glossary/` term-content directory (C-001..C-004, C-008, C-009).

**Shim removal target release**: **`3.3.0`** — the current pyproject version is `3.1.6` (an alpha/pre-release cycle: `3.1.2a3` is reported by `setup-plan`). Per #615 rulebook "one minor release after the shim lands", the shim lands in the next minor `3.2.0` and is removed in `3.3.0`. If either upstream #615 fixes a different ceiling or the release cadence slips, the target is extended via the #615 extension mechanism (A4). The exact version string is written into the shim's `__removal_release__` attribute and into the registry entry.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement).
**Primary Dependencies**: `typer` (CLI), `rich` (console output), `ruamel.yaml` (YAML), `pytest` (tests), `mypy --strict` (type checking) — unchanged. Glossary package itself pulls only stdlib + internal runtime helpers after extraction.
**Storage**: Filesystem only. No database changes. Glossary store persistence format unchanged (C-001).
**Testing**: pytest. Existing glossary test suite at `tests/agent/glossary/` is relocated-but-preserved under the bulk-edit occurrence map. New additions: `tests/regression/glossary/` (snapshot fixtures + regression test per FR-010/FR-011), `tests/glossary/test_architectural_imports.py` (FR-004 enforcement, NFR-004), `tests/specify_cli/glossary/test_shim_deprecation.py` (FR-006 enforcement).
**Target Platform**: Developer machines and CI (Linux, macOS, Windows). No runtime platform surface change.
**Project Type**: Single-project Python refactor — top-level package addition + CLI adapter lift + deprecation shim. No new external surface.
**Performance Goals**: Glossary CLI latency unchanged to within ±10% on a representative reference project (NFR-001). Architectural pytest ≤3s (NFR-004). Regression snapshot test ≤15s on CI (NFR-003).
**Constraints**: No Glossary feature additions (C-001); no graph-backed seam, protocol, or stub (C-002); no DRG-resident middleware implementation (C-003); no CLI UX changes (C-004); no version bump (C-008); repo-root `glossary/` content directory untouched (C-009); `src/glossary/` must not import `specify_cli.*`, `rich.*`, `typer.*` (C-007, enforced by FR-004 pytest).
**Scale/Scope**: ~5 500 LOC of canonical module payload moves (15 files); ~380 LOC of CLI-coupled code (rendering + prompts) lifts to the adapter layer; ~700 LOC monolithic CLI file expands into a `src/specify_cli/cli/commands/glossary/` subpackage; ~243 import-site renames across 41 files; one shim package (~200 LOC with deprecation attributes); one registry entry; one migration doc; three new test modules; one entanglement inventory committed pre-move.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-evaluated after Phase 1 design.*

Charter is present at `.kittify/charter/charter.md` (version 1.1.0, 2026-01-27). `spec-kitty charter context --action plan --json` was invoked but returned a permission denial in this agent's sandbox; the plan applies the published charter directly. No dynamic `bootstrap/compact` context was loaded; nothing in this mission scope depends on unpublished doctrine.

| Directive / Policy | Applies to this Mission? | Compliance plan |
|---|---|---|
| **Python 3.11+ with typer/rich/ruamel.yaml/pytest/mypy-strict** | Yes | Toolchain unchanged. Canonical package drops its `typer`/`rich` imports (they move to adapter). |
| **pytest with 90%+ coverage for new code** | Yes | New code is: architectural-import pytest (small), shim deprecation pytest (small), regression test (small), CLI subpackage split (covered by existing CLI tests + new regression snapshots). Coverage ≥90% achievable on all new surface. |
| **`mypy --strict` must pass** | Yes | Canonical package ships with existing annotations preserved. The architectural pytest uses `ast` (no typing surface). CI enforces. |
| **Integration tests for CLI commands** | Yes | No new CLI commands; existing integration tests cover behavioural invariance (acceptance scenario 1). FR-010/FR-011 add a regression snapshot suite. |
| **CLI operations < 2s for typical projects** | Yes | NFR-001 (latency ±10% of baseline) is a tighter version of this; verified by 10-warm-run benchmark on reference project. |
| **DIRECTIVE_003 — Decision documentation** | Yes | Sunset release, rendering-vs-integrity splits, public/private surface decisions captured in `plan.md`, `CHANGELOG.md` entry, and `docs/migration/glossary-extraction.md`. An ADR is not required (no novel architectural trade-off — this is a pattern-replay of charter extraction and the #615 rulebook). |
| **DIRECTIVE_010 — Specification fidelity** | Yes | All 14 FRs, 5 NFRs, and 9 constraints are mapped to tasks in Phase 1. No scope additions. |
| **DIRECTIVE_035 — Bulk-edit classification** | Yes | `meta.json` has `change_mode: bulk_edit`. `occurrence_map.yaml` authored alongside this plan. |
| **Private dependency pattern (spec-kitty-events)** | No | Mission is pure internal refactor; no dependency surface change. |

**Gate status**: PASS. No charter conflicts. No complexity tracking entries needed.

## Project Structure

### Documentation (this Mission)

```
kitty-specs/glossary-functional-module-extraction-01KPDYM9/
├── spec.md                      # /spec-kitty.specify output (existing)
├── meta.json                    # mission identity + change_mode: bulk_edit (existing)
├── plan.md                      # THIS FILE (/spec-kitty.plan output)
├── research.md                  # Phase 0 output
├── data-model.md                # Phase 1 output
├── quickstart.md                # Phase 1 output
├── contracts/                   # Phase 1 output — interface + lint + deprecation contracts
│   ├── README.md
│   ├── glossary-public-import-surface.md
│   ├── shim-deprecation-contract.md
│   ├── architectural-import-lint-contract.md
│   ├── cli-adapter-boundary-contract.md
│   └── entanglement-inventory-schema.md
├── occurrence_map.yaml          # DIRECTIVE_035 bulk-edit classification
├── checklists/                  # Populated by /spec-kitty.checklist (deferred)
└── tasks/                       # Populated by /spec-kitty.tasks
```

### Source Code (repository root)

Only touched paths are listed. Single-project Python layout; the refactor shifts import ownership and lifts rendering out of the integrity package.

```
src/glossary/                                      # NEW — canonical owner
├── __init__.py                                    # NEW — public API surface mirrors current specify_cli/glossary/__init__.py (202 LOC, __all__ preserved identically)
├── models.py                                      # MIGRATE (from specify_cli/glossary/models.py, 145 LOC)
├── exceptions.py                                  # MIGRATE (68 LOC)
├── scope.py                                       # MIGRATE (174 LOC) — includes `_parse_sense_status` and `load_seed_file` promoted to public `parse_sense_status` / `load_seed_file` (edge-case resolution, see R-007)
├── store.py                                       # MIGRATE (71 LOC)
├── resolution.py                                  # MIGRATE (38 LOC)
├── extraction.py                                  # MIGRATE (453 LOC)
├── conflict.py                                    # MIGRATE (299 LOC)
├── middleware.py                                  # MIGRATE (689 LOC) — the semantic integrity middleware (FR-002)
├── strictness.py                                  # MIGRATE (220 LOC)
├── checkpoint.py                                  # MIGRATE (387 LOC)
├── clarification.py                               # MIGRATE (255 LOC)
├── events.py                                      # MIGRATE (1074 LOC)
├── pipeline.py                                    # MIGRATE (296 LOC)
└── attachment.py                                  # MIGRATE (296 LOC)

src/specify_cli/glossary/                          # Shim surface — deprecated-in-place per #615
├── __init__.py                                    # REWRITE — re-export canonical symbols + emit single DeprecationWarning (stacklevel=2) + set __deprecated__, __canonical_import__="glossary", __removal_release__="3.3.0", __deprecation_message__
├── models.py                                      # REWRITE — re-export of `glossary.models` (silent sys.modules alias per charter pattern)
├── exceptions.py                                  # REWRITE — re-export of `glossary.exceptions`
├── scope.py                                       # REWRITE — re-export of `glossary.scope`
├── store.py                                       # REWRITE — re-export of `glossary.store`
├── resolution.py                                  # REWRITE — re-export of `glossary.resolution`
├── extraction.py                                  # REWRITE — re-export of `glossary.extraction`
├── conflict.py                                    # REWRITE — re-export of `glossary.conflict`
├── middleware.py                                  # REWRITE — re-export of `glossary.middleware`
├── strictness.py                                  # REWRITE — re-export of `glossary.strictness`
├── checkpoint.py                                  # REWRITE — re-export of `glossary.checkpoint`
├── clarification.py                               # REWRITE — re-export of `glossary.clarification`
├── events.py                                      # REWRITE — re-export of `glossary.events`
├── pipeline.py                                    # REWRITE — re-export of `glossary.pipeline`
└── attachment.py                                  # REWRITE — re-export of `glossary.attachment`
# rendering.py and prompts.py are REMOVED from this directory (they move to the CLI adapter layer — see below)

src/specify_cli/cli/commands/glossary/             # Adapter layer — new subpackage (replaces the single 700-LOC monolithic file)
├── __init__.py                                    # NEW — Typer app assembly, re-exports the command callable
├── commands.py                                    # NEW — thin command handlers (argparse → canonical glossary call → render)
├── rendering.py                                   # RELOCATED from src/specify_cli/glossary/rendering.py (Rich conflict formatting; 179 LOC)
└── prompts.py                                     # RELOCATED from src/specify_cli/glossary/prompts.py (typer.prompt wrappers; 210 LOC)
# The pre-existing src/specify_cli/cli/commands/glossary.py file is REMOVED in the same WP (its contents are split into the subpackage above).

architecture/2.x/
└── shim-registry.yaml                             # EDIT — add entry `specify_cli.glossary` with canonical_import="glossary", deprecated_since="3.2.0", removal_release="3.3.0", doc="docs/migration/glossary-extraction.md"

tests/
├── regression/
│   └── glossary/
│       ├── fixtures/                              # NEW — baseline CLI output snapshots captured PRE-move (FR-010)
│       │   ├── list.stdout
│       │   ├── list.stderr
│       │   ├── list.json
│       │   ├── resolve_hit.stdout
│       │   ├── resolve_miss.stdout
│       │   ├── check_pass.stdout
│       │   ├── check_conflict.stdout
│       │   └── add.stdout
│       └── test_cli_regression.py                 # NEW — asserts post-move CLI output equals fixtures (FR-011)
├── glossary/
│   └── test_architectural_imports.py              # NEW — enforces FR-004/C-007 (no rich/typer/specify_cli imports under src/glossary/)
├── specify_cli/glossary/
│   └── test_shim_deprecation.py                   # NEW — enforces FR-006 (DeprecationWarning + required attributes)
└── agent/glossary/                                # ALL imports rewritten under occurrence_map.yaml (tests_fixtures: rename)
    └── …

src/kernel/
└── glossary_runner.py                             # EDIT — imports rewritten `specify_cli.glossary.*` → `glossary.*` per occurrence_map.yaml

docs/
└── migration/
    └── glossary-extraction.md                     # NEW — (a) entanglement inventory, (b) import translation table, (c) deprecation window + removal release

CHANGELOG.md                                       # EDIT — mission entry + shim removal-target note + link to migration doc
```

**Structure Decision**: Single-project layout preserved. The canonical package lives at `src/glossary/` (NOT `src/specify_cli/glossary/`), matching `src/charter/` precedent and upstream #610 ownership-map expectations. The CLI glossary surface expands from a single file to a subpackage `src/specify_cli/cli/commands/glossary/` because two modules (`rendering.py`, `prompts.py`) lift into it as siblings of the command handlers — the existing flat-file CLI layout is insufficient once those modules land.

## Complexity Tracking

*No Charter Check violations. Complexity tracking section intentionally empty.*

The one structural expansion (CLI single-file → subpackage) is not a charter violation — it is the minimal structure that cleanly holds the lifted rendering and prompts modules. No alternative (e.g., keeping rendering inline or inside `src/glossary/`) satisfies FR-003 + FR-004 + C-007 without violation.

---

## Phase 0 — Outline & Research

See [research.md](./research.md). Summary:

- **R-001**: Baseline inventory of `src/specify_cli/glossary/` — **resolved** (17 modules, 5 756 LOC total, public `__all__` already defined in `__init__.py`).
- **R-002**: CLI coupling audit inside `src/specify_cli/glossary/` — **resolved** (`rendering.py` imports `rich.*`, `prompts.py` imports `typer`; both lift to the adapter layer).
- **R-003**: CLI adapter current state — **resolved** (single 700-LOC `src/specify_cli/cli/commands/glossary.py`; consumes private `_parse_sense_status` and `load_seed_file` from `scope.py`; subpackage conversion with public-surface promotion is required — see R-007).
- **R-004**: Entanglement pre-scan — **resolved** (41 files, ~243 occurrences identified; no dynamic `importlib.import_module("specify_cli.glossary.*")` calls found; Assumption A2 holds).
- **R-005**: Shim sunset release — **resolved** (`3.3.0`, one minor after the shim lands in `3.2.0`; per #615 rulebook).
- **R-006**: Rendering-vs-integrity classification of borderline helpers — **resolved** (`rendering.py` = pure Rich formatting → adapter; `prompts.py` = Typer input wrappers → adapter; truncation rules in `middleware.py` and `conflict.py` are semantically significant and stay canonical).
- **R-007**: Private CLI-consumed helpers — **resolved** (`_parse_sense_status` → public `parse_sense_status`; `load_seed_file` already public in name, not underscore-prefixed; both remain in `src/glossary/scope.py` and are added to `__all__`).
- **R-008**: Regression fixture scope — **resolved** (8 baseline snapshots: `list`, `list --format json`, `resolve` hit, `resolve` miss, `check` pass, `check` with conflict, `add`, plus stderr for warning coverage — see FR-010).

No `NEEDS CLARIFICATION` markers remain after Phase 0. All four spec open questions answered above.

---

## Phase 1 — Design & Contracts

See [data-model.md](./data-model.md), [contracts/](./contracts/), and [quickstart.md](./quickstart.md).

- **Data model**: One new conceptual artifact — the **Entanglement Inventory** (rows: call-site path, line, symbol used, disposition `migrate` / `adapter` / `grandfathered`, rationale). No runtime-data schema changes. Existing Glossary store persistence format is not touched (C-001).
- **Contracts**:
  - **Public import surface** for `src/glossary/*` — mirrors current `specify_cli/glossary/__init__.py` `__all__` exactly; adds `parse_sense_status` + `load_seed_file` promoted from `scope.py` (R-007).
  - **Shim deprecation contract** — top-level `__init__.py` emits one `DeprecationWarning` at import time with `stacklevel=2`; module attributes `__deprecated__=True`, `__canonical_import__="glossary"`, `__removal_release__="3.3.0"`, `__deprecation_message__` set. Submodule shims are silent `sys.modules` aliases (no double-warning on `from specify_cli.glossary.X import Y`).
  - **Architectural import lint contract** — `tests/glossary/test_architectural_imports.py` walks `src/glossary/` with stdlib `ast`, asserts no `rich.*`, no `typer.*`, no `specify_cli.*` imports (direct, aliased, or conditional). Runs ≤3s (NFR-004).
  - **CLI adapter boundary contract** — handlers in `src/specify_cli/cli/commands/glossary/commands.py` must (a) parse args via Typer, (b) invoke canonical `glossary.*` callable, (c) format via `rendering.py` or emit JSON, (d) map exceptions to exit codes. No semantic-integrity logic inline. Enforced by code review during `/spec-kitty.review`; a lightweight AST spot-check in the regression test flags obvious inline integrity calls.
  - **Entanglement inventory schema** — the inventory table in `docs/migration/glossary-extraction.md#entanglement-inventory` has a declared schema (columns, allowed disposition values, required rationale when `grandfathered`).
- **Quickstart**: Developer walkthrough — how to run the regression suite against a reference project; how to regenerate snapshots; how to read the entanglement inventory; how to add a new Glossary consumer post-extraction (canonical import only).

### Bulk-Edit Occurrence Map

[occurrence_map.yaml](./occurrence_map.yaml) is authored alongside this plan with the following category actions (ratified from user's pinned spec + plan decisions):

| Category | Action | Rationale |
|---|---|---|
| `code_symbols` | `rename` | Fully-qualified module paths `specify_cli.glossary.*` → `glossary.*` in strings, dotted mock patches, type references, docs. Local symbol names preserved. |
| `import_paths` | `rename` | Primary target — all `from specify_cli.glossary…` → `from glossary…`. |
| `filesystem_paths` | `manual_review` | `src/specify_cli/glossary/*.py` files are rewritten (shim conversion) or relocated (`rendering.py`, `prompts.py`). Each file change is per-WP reviewed. |
| `serialized_keys` | `do_not_change` | Glossary store YAML/JSON schema keys are persistence contracts (C-001). |
| `cli_commands` | `do_not_change` | C-004 — no CLI UX changes. |
| `user_facing_strings` | `rename_if_user_visible` | Docs / help text / CHANGELOG / migration guide references to `specify_cli.glossary` update to `glossary`; log labels remain stable. |
| `tests_fixtures` | `rename` | Test imports follow production. |
| `logs_telemetry` | `do_not_change` | Event names, log labels, metric keys remain stable. |

Exceptions (enumerated in full in `occurrence_map.yaml`):
- Shim files under `src/specify_cli/glossary/*.py` — `do_not_change` for the rename rule (they are the subject of the deprecation, not targets of it).
- `docs/migration/glossary-extraction.md` — teaches the rename; `do_not_change`.
- Mission-directory bodies (`kitty-specs/glossary-functional-module-extraction-01KPDYM9/**`) — quote the deprecated path as the subject of extraction; `do_not_change` or `manual_review`.
- Historical mission artifacts under `kitty-specs/041-mission-glossary-semantic-integrity/**` — historical record of how the surface came to exist; `do_not_change`.
- Historical ADR `architecture/2.x/adr/2026-03-25-1-glossary-type-ownership.md` — historical record; `do_not_change`.
- Historical dev logs `docs/development/pr305-review-resolution-plan.md` and `docs/development/code-review-2026-03-25.md` — historical record; `do_not_change`.
- Docstring `>>>` examples inside `src/specify_cli/glossary/strictness.py` lines 135 and 187 — rewritten during shim conversion to use the canonical path.

### Upstream Coordination

Implementation is gated on:
1. **#610 ownership map** merged — pins the glossary slice's adapter vs canonical assignments. Plan honours the assignments pre-announced in the spec.
2. **#615 shim rulebook + registry + CI check** merged — provides the shim contract this Mission implements and the registry the Mission adds an entry to. The Mission's shim deprecation contract (`contracts/shim-deprecation-contract.md`) references #615 normatively.
3. **#612 runtime extraction** merged (ideally) — stabilises the runtime interface so `src/kernel/glossary_runner.py` does not move under the Mission's feet. Per spec §Dependencies, plan may overlap #612's review/accept phase.

Planning proceeds now; implementation starts when all three land. The entanglement inventory Work Package is executed first (before any code move) to catch any drift introduced by the upstream merges.

---

## Post-Design Charter Check (re-evaluation)

| Check | Verdict after Phase 1 design |
|---|---|
| DIRECTIVE_003 captures decisions? | PASS — `plan.md` + `research.md` + migration guide + shim registry entry. |
| DIRECTIVE_010 spec fidelity preserved? | PASS — every FR/NFR/C maps to a design artifact and a task in tasks.md; no scope expansion. |
| DIRECTIVE_035 occurrence map authored? | PASS — `./occurrence_map.yaml` generated with all 8 categories + exceptions. |
| Test coverage plan realistic? | PASS — architectural pytest + shim-deprecation pytest + regression snapshot test; existing glossary suite untouched apart from import renames. ≥90% on new code. |
| `mypy --strict` feasible? | PASS — canonical package preserves existing annotations; architectural pytest uses stdlib `ast`; shim files are simple re-exports. |
| CLI behavioural invariance? | PASS — FR-010/FR-011 regression snapshots gate behavioural identity; Rich/Typer imports land in the adapter layer with no UX change (C-004). |
| No new Glossary features? | PASS — C-001 enforced by scope review; no new commands, term sources, or conflict strategies introduced. |
| No graph-backed seam? | PASS — C-002 enforced; neither protocol nor stub introduced in this Mission. |
| Repo-root `glossary/` untouched? | PASS — C-009 enforced; all code paths in this plan target `src/glossary/` and `src/specify_cli/glossary/`. |
| Version bump avoided? | PASS — C-008 enforced; `pyproject.toml` is NOT edited by this Mission. Release maintainers cut `3.2.0`. |

**Gate status after design**: PASS. Ready for `/spec-kitty.tasks`.

---

## Branch Contract (repeated for downstream)

**Planning/base `main` → merge target `main` (single branch; no divergence; `branch_matches_target=true`)**

Next suggested command: `/spec-kitty.tasks`.

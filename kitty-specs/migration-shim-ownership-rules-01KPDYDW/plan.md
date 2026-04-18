# Implementation Plan: Migration and Shim Ownership Rules

**Mission slug**: `migration-shim-ownership-rules-01KPDYDW`
**Mission ID**: `01KPDYDWVF8W838HNJK7FC3S7T`
**Branch**: `main` (planning, implementation, and merge all target `main`) | **Date**: 2026-04-17
**Spec**: [spec.md](spec.md)
**Trackers**: [#615](https://github.com/Priivacy-ai/spec-kitty/issues/615) under epic [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461)
**Upstream**: `functional-ownership-map-01KPDY72` (#610) merged before implementation of this mission begins.
**Change mode**: `standard` (C-005) — no `occurrence_map.yaml` needed; this mission adds new files and a new CLI subcommand, not a cross-file rename.

## Branch Strategy (explicit)

- **Current branch at plan start**: `main`
- **Planning base branch**: `main`
- **Merge target**: `main`
- **`branch_matches_target`**: `true`

All planning artefacts and the subsequent WP worktrees branch off `main` and merge back to `main`.

## Summary

This mission produces three deliverables:

1. A **rulebook** (`architecture/2.x/06_migration_and_shim_rules.md`) that codifies the four rule families for migrations and compatibility shims: (a) project schema/version gating, (b) bundle/runtime migration authoring contract, (c) compatibility shim lifecycle, (d) removal plans and the registry contract. [FR-001, FR-002]
2. A **machine-readable shim registry** (`architecture/2.x/shim-registry.yaml`) enumerating every active or grandfathered shim in the codebase, with one entry per shim. [FR-006, FR-007, FR-008]
3. A new CLI subcommand **`spec-kitty doctor shim-registry`** that parses the registry, compares each entry's `removal_target_release` against the current project version, and fails the build when a shim's removal release has shipped but the shim file still exists. [FR-009, C-004, C-007]

Technical approach: add a new logic module `src/specify_cli/architecture/shim_registry.py` housing the parser, schema validator, and version comparator; wire a `shim-registry` subcommand into the existing single-file `src/specify_cli/cli/commands/doctor.py` typer app; land two architectural pytests under `tests/architectural/` — one for schema (FR-011) and one for unregistered-shim detection (FR-010). The rulebook cites mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` as the worked example (FR-012), cross-references `architecture/2.x/05_ownership_map.md` (FR-014), and names #461 Phase 7 as the doctrine-versioning follow-up (FR-013). No live shim is added, modified, or removed (C-001); non-conforming pre-existing shims are flagged `grandfathered: true` (FR-008).

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty runtime)
**Primary Dependencies**: `ruamel.yaml` (YAML read/write — already vendored), `typer` (CLI — already vendored), `rich` (table output — already vendored), `tomllib` (stdlib, for `pyproject.toml` version read), `packaging` (stdlib-adjacent; `packaging.version.Version` for semver comparison — already a transitive dep of many pinned libs, confirm in Phase 0).
**Storage**: Filesystem only. YAML registry at `architecture/2.x/shim-registry.yaml`; Markdown rulebook at `architecture/2.x/06_migration_and_shim_rules.md`.
**Testing**: pytest with two new architectural tests under `tests/architectural/`; NFR-002 bounds the schema test at ≤500 ms; NFR-001 bounds the doctor subcommand at ≤2 s for up to 50 entries.
**Target Platform**: Linux / macOS developer workstations and CI (Linux container). Runs under `spec-kitty doctor shim-registry` or the umbrella `spec-kitty doctor` group.
**Project Type**: single — monolithic `src/specify_cli/` package; no new subproject.
**Performance Goals**: NFR-001 `spec-kitty doctor shim-registry` completes in ≤2 s at 50 entries; NFR-002 registry schema test ≤500 ms.
**Constraints**: C-001 no live shim touched; C-003 no retrofit of pre-existing non-conforming shims; C-004 check is read-only; C-007 integrate cleanly with existing `doctor` group. NFR-004 error messages must name specific shim, legacy path, canonical import, and remediation.
**Scale/Scope**: A1–A5 assumptions: ≤10 shims at mission start; rulebook ≤15-minute read (NFR-003); zero test regressions (NFR-005).

## Charter Check

The project charter covers architecture-neutrality and shim discipline at a high level. This mission advances both by replacing ad-hoc shim conventions with a codified rulebook + registry + CI enforcement. No charter violations identified. Doctrine coherence: the rulebook will directly reference `#461` Phase 7 (doctrine versioning) as the follow-up that extends the schema-version rule family (FR-013), so this mission's output is coherent with the umbrella epic. No Complexity Tracking entries needed.

*Re-check after Phase 1*: no new gates introduced; Charter Check remains passing.

## Resolved Open Questions

The spec's Open Questions section lists three plan-phase items. All three are now resolved after pre-plan codebase investigation and explicit user direction:

| # | Question | Resolution | Evidence |
|---|----------|------------|----------|
| Q1 | Exact YAML schema keys — should `canonical_import` allow a list only in dict form, or also as a sequence under the string key? | Accept **both**: `canonical_import` is `string` OR `list[string]`. Single-target shims use the string form; umbrella shims use the list form. Schema validation is a `oneOf` over those two shapes. | Spec edge-case (lines 84–86) explicitly allows umbrella modules pointing to multiple canonical imports. Keeping both forms avoids forcing every entry into list syntax for single-target case. |
| Q2 | Precise integration point for `spec-kitty doctor shim-registry` in the existing doctor group's code layout. | `src/specify_cli/cli/commands/doctor.py` is a **single file** containing all four existing subcommands via `@app.command(name="…")` decorators (`command-files`, `state-roots`, `identity`, `sparse-checkout`). Add a 5th `@app.command(name="shim-registry")` to that same file. Keep the logic thin in the command function; delegate parsing/validation/comparison to a new module `src/specify_cli/architecture/shim_registry.py`. | Inspected file, confirmed layout. Pattern matches existing subcommands, which also delegate to helpers in other modules. Satisfies C-007 "integrate cleanly with the existing doctor group." |
| Q3 | Whether the unregistered-shim scanner test lives under `tests/architectural/` or `tests/unit/`. | **`tests/architectural/`** for both FR-010 and FR-011. | Directory exists and contains `test_layer_rules.py`, the canonical home for cross-package structural assertions. Matches the pattern: architectural tests assert properties of the codebase-as-a-whole, not of a single module. |

## Project Structure

### Documentation (this mission)

```
kitty-specs/migration-shim-ownership-rules-01KPDYDW/
├── spec.md              # Authored in the prior phase
├── plan.md              # This file
├── research.md          # Phase 0 — research notes on semver comparison, tomllib, ruamel.yaml schema validation
├── data-model.md        # Phase 1 — registry entry schema + rulebook rule-family structure
├── quickstart.md        # Phase 1 — contributor walkthrough of registering a new shim
├── contracts/           # Phase 1 — registry YAML JSON Schema and doctor-subcommand CLI contract
└── tasks.md             # Phase 2 — produced by /spec-kitty.tasks
```

### Source Code (repository root)

The mission touches three directories. All paths are relative to the repo root `/home/stijn/Documents/_code/CLIENTS/regnology/spec-kitty/`.

```
architecture/2.x/
├── 05_ownership_map.md                    # EXISTS (from mission #610). Cross-referenced by rulebook (FR-014). NOT MODIFIED.
├── 06_migration_and_shim_rules.md         # NEW — the rulebook (FR-001)
└── shim-registry.yaml                     # NEW — the registry (FR-006)

src/specify_cli/
├── architecture/                          # NEW package (may already exist; create __init__.py if absent)
│   ├── __init__.py                        # NEW — exports shim_registry API
│   └── shim_registry.py                   # NEW — parser, validator, version comparator, scanner helper
└── cli/commands/
    └── doctor.py                          # MODIFIED — append `@app.command(name="shim-registry")` and
                                            #            its handler function only; no other edits
                                            # (FR-009, C-007)

tests/architectural/
├── test_layer_rules.py                    # EXISTS — NOT MODIFIED
├── test_shim_registry_schema.py           # NEW — FR-011 (schema validation, NFR-002 ≤500 ms)
└── test_unregistered_shim_scanner.py      # NEW — FR-010 (scans src/specify_cli/ for __deprecated__=True
                                            #         modules and asserts each appears in the registry)

CHANGELOG.md                               # MODIFIED — FR-015 adds Unreleased/Added entry announcing
                                            #            the rulebook, registry, and CI check
```

**Structure Decision**: Single-project Python layout. New rulebook and registry live alongside the existing `architecture/2.x/05_ownership_map.md` from mission #610 (A1). Doctor subcommand stays inside the single-file typer app in `src/specify_cli/cli/commands/doctor.py` per C-007. Shim-registry logic lives in a dedicated module under a new `src/specify_cli/architecture/` package so future architectural-guardrail code has a clear home. Architectural tests sit under `tests/architectural/`.

## Architectural Design Decisions

### ADD-1: Registry schema — `canonical_import` accepts string OR list[string]

**Decision**: The YAML field `canonical_import` is typed `string | list[string]`. Single-target shims render as `canonical_import: specify_cli.runtime.mission`; umbrella shims render as `canonical_import: [specify_cli.runtime.mission, specify_cli.runtime.executor]`.

**Rationale**: Satisfies the umbrella-module edge case (spec lines 84–86) without forcing every single-target entry into list syntax. Schema validation uses a `oneOf` union. [FR-007, spec edge-case #3]

**Alternatives rejected**: (a) list-only — noisy for the majority case; (b) string-only — forbids umbrella shims entirely.

### ADD-2: Doctor subcommand lives in the existing single-file typer app

**Decision**: Append `@app.command(name="shim-registry")` to `src/specify_cli/cli/commands/doctor.py` alongside the four existing subcommands. Delegate business logic to `src/specify_cli/architecture/shim_registry.py`. [FR-009, C-007]

**Rationale**: Matches the established pattern (each existing subcommand delegates to a helper module). Keeps the typer group cohesive without introducing a `doctor/` subpackage refactor that is out of scope for this mission.

**Alternatives rejected**: (a) promote `doctor.py` to `doctor/` package with per-subcommand modules — a useful refactor but out of scope (would force re-routing of 4 existing subcommands, risking regression in NFR-005).

### ADD-3: Architectural tests home

**Decision**: Both FR-010 (unregistered-shim scanner) and FR-011 (schema validator) live under `tests/architectural/` as `test_unregistered_shim_scanner.py` and `test_shim_registry_schema.py` respectively.

**Rationale**: Matches the existing `test_layer_rules.py` precedent — these tests assert properties of the codebase-as-a-whole, which is exactly what `tests/architectural/` exists for.

**Alternatives rejected**: (a) `tests/unit/` — misleading: these are structural assertions, not unit tests of a single function.

### ADD-4: Extension mechanism for `removal_target_release`

**Decision**: Extending a shim's `removal_target_release` beyond the original one-release deprecation window requires three things in the same PR:
1. An explicit edit to the registry entry changing `removal_target_release`.
2. A non-empty `extension_rationale` field on that entry.
3. Reviewer sign-off per the same review bar as any architecture change.

The doctor subcommand and the FR-010 scanner treat entries with `extension_rationale` set as having a bounded rationale; the doctor check still enforces that the *new* `removal_target_release` has not yet been reached. [FR-004, FR-007]

**Rationale**: Preserves the default one-release window while creating a reviewable escape hatch. Avoids the failure mode where contributors silently push removal dates out.

**Alternatives rejected**: (a) no extension — unrealistic for shims with external downstream importers (spec edge case #2); (b) free-form extension without rationale — defeats auditability.

### ADD-5: Doctor subcommand behavioural contract (semantic)

Handler reads:
- Project version from `pyproject.toml` via stdlib `tomllib` (Python 3.11+ guaranteed).
- Registry from `architecture/2.x/shim-registry.yaml` via `ruamel.yaml` safe loader.

Handler produces:
- Rich `Table` with columns `legacy_path`, `canonical_import`, `removal_target`, `status`.
- Status enum: `pending` (current_version < removal_target), `overdue` (current_version ≥ removal_target AND module file exists), `grandfathered` (advisory only), `removed` (current_version ≥ removal_target AND module file absent — this is the "removal was completed cleanly" state).

Exit codes:
- `0`: all entries clean OR only advisory-level items (grandfathered / removed).
- `1`: at least one `overdue` entry.

Module-file existence probe: `legacy_path = "specify_cli.charter"` → probe `src/specify_cli/charter.py` then `src/specify_cli/charter/__init__.py`. First hit counts as "exists."

Read-only guarantee: handler never writes to filesystem (C-004). [FR-009, NFR-001, NFR-004]

### ADD-6: Version comparator

**Decision**: Use `packaging.version.Version` for semver comparison. Confirm it is present transitively; if not, add to `pyproject.toml` dependencies (flagged in Phase 0 research).

**Rationale**: Standard, battle-tested, handles pre-release versioning correctly. Avoids hand-rolled regex comparator.

**Alternatives rejected**: (a) custom semver tuple parser — reinvents wheel, risks bugs on pre-release suffixes; (b) string comparison — wrong for `3.10.0` vs `3.2.0`.

### ADD-7: Rulebook structure (FR-002 four rule families)

Top-level sections, numbered:

1. **Scope & Terminology** — Mission, Work Package, Shim, Rulebook, Registry (aligns with glossary canon C-006 implicitly).
2. **Rule Family (a) — Project Schema/Version Gating** — describes current schema-version contract and names #461 Phase 7 as the follow-up for doctrine artefacts (FR-013).
3. **Rule Family (b) — Bundle/Runtime Migration Authoring Contract** — migration module shape, idempotency expectations, test expectations.
4. **Rule Family (c) — Compatibility Shim Lifecycle** — shim module shape (FR-003), `DeprecationWarning` emission rules, one-release deprecation window (FR-004).
5. **Rule Family (d) — Removal Plans & Registry Contract** — registry schema, removal-PR contract (FR-005), extension mechanism (ADD-4).
6. **Registry Schema Reference** — concrete field definitions (FR-007).
7. **Worked Example: charter-ownership-consolidation-and-neutrality-hardening-01KPD880** — maps each rule to concrete artefacts in that mission (FR-012).
8. **Cross-references** — `architecture/2.x/05_ownership_map.md` (FR-014), #461 Phase 7 (FR-013).

## Phase 0 — Research

Research notes will be consolidated in `research.md`. Investigation areas:

1. **Semver comparator choice** — confirm `packaging.version.Version` is transitively available; document `from packaging.version import Version; Version("3.3.0") >= Version("3.2.0")` pattern.
2. **`pyproject.toml` version reader** — confirm Python 3.11 `tomllib.load(fp)` pattern; document fallback when file missing (rare; doctor returns exit 2 with config error).
3. **`ruamel.yaml` schema validation approach** — document the minimal manual schema check (iterate keys, assert types, regex semver) vs. pulling in a formal validator like `cerberus` or `jsonschema`. Prefer manual check for NFR-002 ≤500 ms budget and to avoid new deps.
4. **Existing test helpers in `tests/architectural/`** — review `test_layer_rules.py` and `conftest.py` for fixtures the new tests can reuse (e.g., project-root discovery).
5. **Charter mission artefacts for FR-012 worked example** — map `charter-ownership-consolidation-and-neutrality-hardening-01KPD880`'s concrete shim files, `__deprecated__` attributes, and registry entry (once #610 lands or during this mission's implementation based on the latest commit of #610) for citation in the rulebook.

## Phase 1 — Design & Contracts

**Prerequisites**: Phase 0 research complete.

Phase 1 outputs:

### `data-model.md`

- **Registry entry entity** — fields, types, optionality, semver regex.
- **Shim module entity** — required attributes (`__deprecated__`, `__canonical_import__`, `__removal_release__`, `__deprecation_message__`) and warning-emission pattern.
- **Rulebook rule-family entity** — structural sections (a)–(d) and their required sub-sections.

### `contracts/`

- `shim-registry-schema.yaml` — formal JSON-Schema-like description of the YAML registry (for human readers and to pin the FR-011 test expectations).
- `doctor-shim-registry-cli.md` — CLI contract for `spec-kitty doctor shim-registry`: invocation, flags (`--json`, `--fix` NOT implemented per C-004), exit codes, output schema.

### `quickstart.md`

Contributor walkthrough: "You just extracted a new slice and produced a shim. Here is how to register it" — step-by-step from shim file to registry entry to passing `spec-kitty doctor shim-registry`.

## Complexity Tracking

No Charter Check violations identified. Table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Branch Strategy Confirmation (2nd)

- **Current branch**: `main`
- **Planning base branch**: `main`
- **Merge target**: `main`
- **`branch_matches_target`**: `true`

All WP worktrees for this mission branch off `main` and merge back to `main`. Run `/spec-kitty.tasks` next to break this plan into Work Packages.

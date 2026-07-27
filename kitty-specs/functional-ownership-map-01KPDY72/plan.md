# Implementation Plan: Functional Ownership Map

**Branch contract**: planning/base `feature/module_ownership` → merge target `feature/module_ownership` (single branch; no divergence). `branch_matches_target=true` confirmed at setup-plan.
**Date**: 2026-04-17
**Spec**: [./spec.md](./spec.md)
**Mission ID**: `01KPDY72HV348TA2ERN9S1WM91` · **mid8**: `01KPDY72`
**Change mode**: `standard` (no `occurrence_map.yaml` required per C-006)
**Exemplar reference**: mission `charter-ownership-consolidation-and-neutrality-hardening-01KPD880` (FR-006)

---

## Summary

This mission produces the canonical **functional ownership map** for every remaining major slice of `src/specify_cli/*` (FR-001, FR-002) and a parallel **machine-readable ownership manifest** (FR-010, FR-011). It also folds in issue #611 — deleting `src/specify_cli/charter/` (FR-012) so the charter slice entry reads as fully consolidated on the day the map lands (acceptance scenario 4).

**Nothing else moves.** Runtime, glossary, lifecycle, orchestrator, sync, tracker, SaaS, and migration code stay exactly where they are today (C-002, FR-015). The map is a decision artefact for downstream missions #612 (runtime extraction), #613 (glossary extraction), #614 (lifecycle extraction), and #615 (shim rulebook).

Baseline reality check (informing the plan):

- `src/` currently contains four top-level packages: `charter/`, `doctrine/`, `kernel/`, `specify_cli/`. The map must show that shape and name the target shape for each slice.
- The "orchestrator/sync/tracker/SaaS" slice is not a single directory today — it spans `src/specify_cli/orchestrator_api/`, `lanes/`, `merge/`, `sync/`, `tracker/`, `saas/`, and `shims/`. The map must describe that fragmentation factually (edge case in spec §Edge cases).
- The `src/specify_cli/charter/` shim is a single `__init__.py` that already emits `DeprecationWarning` with `__removal_release__ = "3.3.0"` plus three silent re-export submodules (`compiler.py`, `interview.py`, `resolver.py`). All four files are deleted together.
- The canonical charter implementation at `src/charter/` is already the sole definition site for `build_charter_context()` and `ensure_charter_bundle_fresh()` (verified via exemplar mission `01KPD880` baseline inventory).
- `src/doctrine/model_task_routing/` exists today as `__init__.py` + `models.py` defining a Pydantic schema for a model-to-task-type catalog with a `RoutingPolicy` (objective + weights + tier_constraints + override policy + freshness policy). It is procedural ("given task type, pick a model per this policy"), which determines its parent kind (see Structure Decision below).

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement).
**Primary Dependencies**: `ruamel.yaml` (manifest authoring + parsing), `pytest` (schema test), stdlib only otherwise. No new package pins.
**Storage**: Filesystem only. Two new artefacts under `architecture/2.x/`; one directory deleted under `src/specify_cli/`; one CHANGELOG entry.
**Testing**: pytest. One new test module verifies manifest schema coverage of all eight slices (FR-011, NFR-002). Existing test suite must continue to pass with zero new exceptions (NFR-003); three test-fixture exceptions previously scoped to the charter shim (C-005 exceptions from mission `01KPD880`) are **deleted, not replaced**.
**Target Platform**: Developer machines and CI (Linux, macOS). No runtime platform surface change.
**Project Type**: Single project. This mission **does not alter directory topology** beyond deleting one subdirectory under `src/specify_cli/`.
**Performance Goals**: Manifest schema validation test runs in ≤1s on a baseline dev machine (NFR-002). `import specify_cli.charter` raises `ModuleNotFoundError` within Python's normal import resolution time, <100 ms on a warm interpreter (NFR-004).
**Constraints**: `pyproject.toml` version stays at `3.1.6` (C-001). `change_mode: standard` — no occurrence map, no cross-file same-string rewrite (C-006). Terminology follows **Mission** / **Work Package** per C-005.
**Scale/Scope**: 1 new Markdown document (`architecture/2.x/05_ownership_map.md`, ~8 slice sections + exemplar + safeguards + direction + glossary/legend), 1 new YAML manifest (`architecture/2.x/05_ownership_manifest.yaml`, 8 top-level keys), 1 new pytest module, 4 files deleted under `src/specify_cli/charter/`, 1 cross-reference added to `architecture/2.x/04_implementation_mapping/README.md`, 1 CHANGELOG entry under *Unreleased* / "Removed".

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Directive / Policy                            | Applies? | Compliance plan                                                                                                                                                                                                    |
|-----------------------------------------------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **DIRECTIVE_003** — Decision Documentation    | Yes      | All plan-phase decisions (canonical paths for runtime & lifecycle, `model_task_routing` parent kind, manifest schema shape) are recorded in this `plan.md` with rationale. No separate ADR required — the map is itself the ADR-equivalent artefact. |
| **DIRECTIVE_010** — Specification Fidelity    | Yes      | All 15 FRs, 4 NFRs, and 6 Cs in `spec.md` are addressed by tasks in this plan. Any deviation during implementation lands as a spec amendment.                                                                       |
| **DIRECTIVE_035** — Bulk-edit classification  | No       | `meta.json` has `change_mode: standard`. The charter shim deletion is a whole-directory removal with zero cross-file same-string rewrite (its re-exports have no live internal call sites per baseline from mission `01KPD880`). No occurrence map needed (C-006). |
| **Test coverage ≥ 90%** on new code           | Yes      | Applies to the manifest schema test and any helper code that loads the manifest. The Markdown map itself is content, not code.                                                                                      |
| **`mypy --strict` must pass**                 | Yes      | New test module is pure pytest + pyyaml/ruamel load; straightforward types.                                                                                                                                         |
| **Integration tests for CLI commands**        | No       | No CLI surface changes in this mission.                                                                                                                                                                             |
| **Terminology canon: Mission / Work Package** | Yes      | Map uses "Mission" (not feature) and "Work Package" (not task) throughout. Legend in the map's front matter states this explicitly.                                                                                 |

**Gate status**: PASS. No charter conflicts. No complexity tracking entries.

## Project Structure

### Documentation (this mission)

```
kitty-specs/functional-ownership-map-01KPDY72/
├── spec.md                    # /spec-kitty.specify output (complete)
├── meta.json                  # mission identity + change_mode: standard
├── plan.md                    # THIS FILE (/spec-kitty.plan output)
├── research.md                # Phase 0 output
├── data-model.md              # Phase 1 output — manifest schema + slice entry shape
├── quickstart.md              # Phase 1 output — "How to use the ownership map" walkthrough for reviewers & extraction-PR authors
├── contracts/                 # Phase 1 output — manifest schema contract + cross-reference contract
├── checklists/
│   └── requirements.md        # Spec-phase quality checklist (already present)
└── tasks/                     # Populated by /spec-kitty.tasks
```

### Source Code / Architecture Docs (repository root)

Only touched paths are listed.

```
architecture/2.x/
├── 04_implementation_mapping/
│   └── README.md                              # EDIT — add prominent cross-link "For slice-level ownership, see ../05_ownership_map.md" (FR-007)
├── 05_ownership_map.md                        # NEW — canonical ownership map (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-008, FR-009)
└── 05_ownership_manifest.yaml                 # NEW — machine-readable manifest (FR-010)

src/specify_cli/charter/                        # DELETE ENTIRE DIRECTORY (FR-012)
├── __init__.py                                 # DELETE (the sole DeprecationWarning site)
├── compiler.py                                 # DELETE (silent re-export)
├── interview.py                                # DELETE (silent re-export)
└── resolver.py                                 # DELETE (silent re-export)

tests/
└── architecture/
    └── test_ownership_manifest_schema.py      # NEW — validates manifest structure (FR-011, NFR-002)

CHANGELOG.md                                    # EDIT — add *Unreleased* entry under "Removed" (FR-013)
```

No other files are touched. `pyproject.toml` is **not** edited (C-001). The canonical packages `src/charter/`, `src/doctrine/`, `src/kernel/`, and `src/specify_cli/` keep their current layouts. Runtime, glossary, lifecycle, orchestrator, sync, tracker, SaaS, and migration code is **not** moved or renamed (C-002, FR-015).

### Structure Decisions (pinned in plan phase)

These are the two items the spec explicitly deferred to plan phase (spec §Open Questions, lines 198–201). They are recorded here so the ownership map authors them verbatim.

| Decision                                              | Pinned value                                    | Rationale                                                                                                                                                                                                                                             |
|-------------------------------------------------------|-------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Runtime slice canonical package path**              | `src/runtime/`                                  | Mirrors the already-pinned pattern for charter (`src/charter/`) and glossary (`src/glossary/`, pinned for #613). Top-level `src/` placement signals "standalone package, not owned by CLI". The parent issue #612 draft uses this as its working candidate.                              |
| **Lifecycle/status slice canonical package path**     | `src/lifecycle/`                                | Slice taxonomy name in spec FR-002 is "lifecycle/status" — lifecycle is the broader concept (events, transitions, reducer, recovery, doctor). The concrete modules that move in mission #614 span `status/` + `lanes/` + parts of `events/` + parts of `state/`; a single `src/lifecycle/` umbrella gives the extraction one target instead of three. |
| **Parent kind for `model_task_routing` specialization** | **Tactic**                                    | The module's `RoutingPolicy` is an executable procedure: load catalog → evaluate task_fit scores weighted by objective → apply `tier_constraints` → apply `override_policy` → emit chosen model. That is the canonical tactic shape (step-by-step execution procedure, per `architecture/2.x/04_implementation_mapping/README.md` doctrine stack). It is **not** a directive (no `enforcement: required\|advisory` semantics), **not** a paradigm (too concrete), **not** a styleguide (not an output shape), **not** a toolguide (models are subjects, not tools). The specialization adds a schema-validated catalog + routing policy on top of the tactic contract. |

### Manifest Schema Shape (authored here, consumed by Phase 1 contract)

Top-level YAML is a mapping keyed by slice canonical identifier. Eight keys, in this order, to match the map's section order:

```yaml
# architecture/2.x/05_ownership_manifest.yaml
cli_shell:              <slice-entry>
charter_governance:     <slice-entry>
doctrine:               <slice-entry>
runtime_mission_execution: <slice-entry>
glossary:               <slice-entry>
lifecycle_status:       <slice-entry>
orchestrator_sync_tracker_saas: <slice-entry>
migration_versioning:   <slice-entry>
```

Each `<slice-entry>` is a mapping with:

| Field                          | Type           | Required? | Notes                                                                                                                                   |
|--------------------------------|----------------|-----------|-----------------------------------------------------------------------------------------------------------------------------------------|
| `canonical_package`            | string         | **yes**   | e.g. `charter`, `src/runtime/`. Dotted or filesystem form — either is valid; convention is filesystem form.                              |
| `current_state`                | list[string]   | **yes**   | Primary files or directories where the slice lives today. Non-empty.                                                                     |
| `adapter_responsibilities`     | list[string]   | **yes**   | CLI-only work that legitimately remains in `src/specify_cli/` post-extraction. May be an empty list for slices whose CLI surface is zero (doctrine, glossary). |
| `shims`                        | list[mapping]  | **yes**   | May be empty. Each entry: `path`, `canonical_import`, `removal_release`, `notes`. The charter slice's list is **empty** post-mission.    |
| `seams`                        | list[string]   | **yes**   | May be empty. Free-form "X reads Y through Z" sentences.                                                                                 |
| `extraction_sequencing_notes`  | string         | **yes**   | Short paragraph on when this slice extracts relative to others; may reference downstream missions by number.                              |
| `dependency_rules`             | mapping        | runtime only | Keys: `may_call` (list), `may_be_called_by` (list). **Required** on the runtime slice (FR-004). Absent on other slices.                  |

The schema test (`tests/architecture/test_ownership_manifest_schema.py`) asserts:

1. The YAML parses without error.
2. Exactly the 8 documented top-level keys exist (no missing, no extra).
3. Each slice entry carries all required fields with the correct types.
4. The runtime slice entry has a `dependency_rules` mapping with both `may_call` and `may_be_called_by` as lists.
5. No other slice carries `dependency_rules` (keeps the runtime-specific scoping honest).
6. Every `shims[].path` that is non-empty points to a directory that actually exists in the repo at the time the test runs. The charter slice's `shims` list is **empty** (the shim is deleted in this mission).

### Charter Shim Deletion Sequencing

The deletion and the map authoring are interlocked to preserve acceptance scenario 4 ("charter slice reads as fully consolidated"):

1. Map and manifest are drafted first, with the charter slice entry already reading as fully consolidated (`shims: []`, `current_state` pointing at `src/charter/` only).
2. The shim deletion lands as its own Work Package *after* the map/manifest WP, but before the schema test WP (so when the schema test runs, the repo state matches the map's description of it — `shims[].path` in the charter entry is empty, and the schema test's "shim paths must exist if listed" check has nothing to verify for charter).
3. The CHANGELOG entry lands alongside the deletion WP.
4. `/spec-kitty.tasks` will sequence WPs accordingly.

## Complexity Tracking

*No Charter Check violations. Complexity tracking section intentionally empty.*

---

## Phase 0 — Outline & Research

See [research.md](./research.md). The plan surfaced **no** `NEEDS CLARIFICATION` markers — the spec pins every scope decision, and the two items it delegated to plan phase (canonical paths + `model_task_routing` parent kind) are resolved in the Structure Decisions table above.

Research notes to capture:

- **R-001** Baseline inventory of `src/specify_cli/charter/` — already known from exemplar mission `01KPD880`: 4 files, single DeprecationWarning site, no live internal call sites.
- **R-002** Confirmation that no CI job, release script, or installer references `specify_cli.charter` (assumption A3 in spec). Plan-phase grep will confirm; if anything is found, it is added as an extra cleanup WP.
- **R-003** Safeguards tracker status: issues #393 (architectural tests), #394 (deprecation scaffolding), #395 (import-graph tooling) — the map cites these and describes which must land before a given slice extracts (FR-008).
- **R-004** Whether the existing three test-fixture exceptions documented in mission `01KPD880` C-005 (legacy-import tests by design) still exist in the tree; all three are deleted by this mission (NFR-003).
- **R-005** Current filesystem reality of the orchestrator/sync/tracker/SaaS slice (fragmented across seven subdirectories); documented factually in the map's slice entry (spec §Edge cases).

No external NEEDS CLARIFICATION research tasks — everything is resolvable from the repo HEAD.

---

## Phase 1 — Design & Contracts

See [data-model.md](./data-model.md), [contracts/](./contracts/), and [quickstart.md](./quickstart.md).

- **Data model** (`data-model.md`): Formal schema for a slice entry (field-by-field), formal schema for a shim sub-entry, formal schema for `dependency_rules`. Enumerates the eight slice keys with their canonical_package values. Cross-references each field to the spec's FR it satisfies.
- **Contracts** (`contracts/`):
  - `ownership_manifest.schema.yaml` — JSON Schema for `architecture/2.x/05_ownership_manifest.yaml`. Used by the schema test.
  - `cross_reference.md` — the exact wording to insert into `architecture/2.x/04_implementation_mapping/README.md` pointing to the ownership map (FR-007).
  - `changelog_entry.md` — the exact *Unreleased* / "Removed" CHANGELOG block (FR-013).
- **Quickstart** (`quickstart.md`): Two audiences — (1) extraction-PR author using the map as a checklist; (2) reviewer using the map as an acceptance filter. Acceptance scenarios 1 and 2 from the spec become the quickstart's worked examples.

### Post-Design Charter Check (re-evaluation)

| Check                                         | Verdict after Phase 1 design                                                                                                                                                                                                                |
|-----------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| DIRECTIVE_003 captures decisions?             | PASS — `plan.md` + `research.md` + the map itself.                                                                                                                                                                                         |
| DIRECTIVE_010 spec fidelity preserved?        | PASS — every FR/NFR/C maps to a design artefact. No scope expansion.                                                                                                                                                                        |
| DIRECTIVE_035 occurrence map required?        | N/A — `change_mode: standard` (C-006).                                                                                                                                                                                                     |
| Test coverage plan realistic?                 | PASS — one schema test on a small YAML. ≥90% trivially.                                                                                                                                                                                    |
| `mypy --strict` feasible?                     | PASS — the new test is pure pytest + yaml load.                                                                                                                                                                                            |
| Terminology canon compliant?                  | PASS — map legend states "Mission / Work Package" canon; no "feature/task" in authored prose.                                                                                                                                              |
| Cross-references resolve?                     | PASS — `04_implementation_mapping/README.md` edit is a single paragraph link; the map's internal tracker references (#393, #394, #395, #461, #612, #613, #614, #615) resolve to real GitHub issues; a quickstart walkthrough validates navigation. |
| Charter slice reads as fully consolidated?    | PASS — deletion WP sequences after map-authoring WP, with CHANGELOG entry in the same WP. `shims[]` for charter is empty in the manifest.                                                                                                   |

**Gate status after design**: PASS. Ready for `/spec-kitty.tasks`.

---

**Branch contract (restated for the final report):** planning/base `feature/module_ownership` → merge target `feature/module_ownership`. No additional feature branch — this mission lands into `feature/module_ownership` via the standard merge workflow. `spec-kitty implement WP##` will still resolve per-WP workspaces per the normal 2.x contract.

**Next**: Run `/spec-kitty.tasks` to decompose into Work Packages.

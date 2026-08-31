# Implementation Plan: Excise Doctrine Curation and Inline References

**Mission ID**: `01KP54J6W03W8B05F3P2RDPS8S` (`mid8`: `01KP54J6`)
**Mission slug**: `excise-doctrine-curation-and-inline-references-01KP54J6`
**Branch**: `main` (planning base = merge target = `main`)
**Date**: 2026-04-14
**Spec**: [spec.md](spec.md)
**Tracking issue**: [Priivacy-ai/spec-kitty#463](https://github.com/Priivacy-ai/spec-kitty/issues/463)

---

## Summary

Execute Phase 1 of [EPIC #461](https://github.com/Priivacy-ai/spec-kitty/issues/461) by excising every surviving carrier of the pre-DRG doctrine model on `main`: the curation pipeline (package, CLI, validator, `_proposed/` trees), the inline `tactic_refs` / `paradigm_refs` / `applies_to` fields on shipped artifacts + schemas + models, the legacy transitive reference resolver, the `include_proposed` catalog flag, and the parallel `build_charter_context` / `build_context_v2` split. The end state is a single context builder (renamed to `build_charter_context`), validators that actively reject inline refs, and `src/doctrine/drg/query.py` exposing a new `resolve_transitive_refs()` that serves the pre-existing callers (`resolve_governance()`, `compile_charter()`) without requiring a deeper Phase 3 rewrite.

The technical approach is a strict three-WP excision (WP1.1 → WP1.2 → WP1.3) guarded by the [#393 occurrence-classification pattern](https://github.com/Priivacy-ai/spec-kitty/issues/393). Every WP ships its own occurrence artifact under `kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/WP1.<n>.yaml`, and a mission-level index aggregates the "must-be-zero" set across WPs. Verification is by completeness (scripted check of the occurrence artifact against the live tree), not by semantic-diff review.

---

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement)
**Primary Dependencies**: `typer`, `rich`, `ruamel.yaml`, `pytest`, `mypy --strict` (unchanged)
**Storage**: Filesystem only — YAML doctrine artifacts, `src/doctrine/graph.yaml`, project-local overlays
**Testing**: `pytest` with ≥90% coverage on changed code per charter; `mypy --strict` must pass
**Target Platform**: The `spec-kitty-cli` Python package distributed via PyPI
**Project Type**: Single project (this is pure refactor inside `src/` and `tests/`)
**Performance Goals**: Do not regress pytest runtime more than 5% (NFR-001); no changes to user-facing runtime performance expected since `build_context_v2()` is already parity-safe
**Constraints**: No fallback, no backwards compatibility, no deprecation shim (C-001); strict #393 guardrail usage (C-002); only SOURCE templates editable (C-005); `m_3_1_1_charter_rename.py` migration is carved out (C-006); strict WP sequencing (C-007)
**Scale/Scope**: ~2500 LOC deletion plus a targeted rewrite of `resolve_references_transitively` into a DRG-backed `resolve_transitive_refs` (~150 LOC). ~27 test files impacted. Twin charter packages (`src/charter/` and `src/specify_cli/charter/`) edited in lockstep.

---

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Charter file**: `/Users/robert/spec-kitty-dev/spec-kitty-charter-14-April/spec-kitty/.kittify/charter/charter.md` exists.

**Governance file**: `/Users/robert/spec-kitty-dev/spec-kitty-charter-14-April/spec-kitty/.kittify/charter/governance.yaml` **does not** exist on `main` today (the bootstrap `spec-kitty charter context` emits `governance.yaml not found. Run 'spec-kitty charter sync'`). This is an informational note, **not a gate violation** for this mission — Phase 1 does not depend on `governance.yaml` and does not write one.

**Charter-derived policy summary applied to this mission**:

| Policy | Applies to this mission? | How we honor it |
| --- | --- | --- |
| `typer`, `rich`, `ruamel.yaml`, `pytest`, `mypy --strict` | Yes | No new runtime deps introduced; validator rejection shape uses existing ruamel.yaml load path |
| ≥90% test coverage on new code | Yes | `resolve_transitive_refs`, validator rejection paths, and rewritten context builder tests must meet this bar |
| `mypy --strict` passes | Yes | Every WP PR blocks on mypy-strict in CI |
| Integration tests for CLI commands | Yes | WP1.1 includes an integration test that asserts `spec-kitty doctrine curate` fails with unknown-command; WP1.3 includes an integration test of `spec-kitty charter generate` against the DRG-backed `compile_charter` path |

**DIRECTIVE_003 (Decision Documentation)**: Every plan-phase decision is recorded in this plan.md and in the mission-level occurrence index. No decisions are deferred to implementation silently.

**DIRECTIVE_010 (Specification Fidelity)**: Any deviation from `spec.md` during implementation must be logged in `spec.md` as an amendment and re-reviewed before merge. The `resolve_transitive_refs` extraction and the rename-only-at-WP1.3 sequencing are plan-phase refinements that this plan records explicitly.

**Gate status**: PASS. No violations. Governance-file absence is informational.

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── occurrence-artifact.schema.yaml
│   ├── validator-rejection-error.schema.json
│   ├── resolve-transitive-refs.contract.md
│   └── removed-cli-surface.md
├── occurrences/                       # created by /spec-kitty.tasks + implementation
│   ├── index.yaml                     # mission-level aggregate
│   ├── WP1.1.yaml
│   ├── WP1.2.yaml
│   └── WP1.3.yaml
├── checklists/
│   └── requirements.md
├── meta.json
└── tasks.md                           # /spec-kitty.tasks output
```

### Source code (repository root)

```
src/
├── charter/                           # library package — edited in WP1.2 + WP1.3
│   ├── __init__.py                    # export surface flipped in WP1.3
│   ├── catalog.py                     # drop include_proposed in WP1.3
│   ├── compiler.py                    # swap resolver import in WP1.3
│   ├── context.py                     # collapse to one builder in WP1.3
│   ├── generator.py                   # untouched (re-export layer)
│   ├── reference_resolver.py          # DELETE in WP1.3
│   ├── resolver.py                    # swap resolver import in WP1.3
│   ├── schemas.py                     # strip applies_to from Directive in WP1.2
│   └── sync.py                        # untouched
├── specify_cli/
│   ├── charter/                       # CLI-facing twin of src/charter/ — lockstep edits
│   │   ├── __init__.py
│   │   ├── compiler.py
│   │   ├── context.py
│   │   └── resolver.py
│   ├── cli/commands/
│   │   ├── __init__.py                # remove doctrine Typer registration in WP1.1
│   │   ├── charter.py                 # call-site flip in WP1.3
│   │   ├── doctrine.py                # DELETE in WP1.1
│   │   └── agent/workflow.py          # call-site flip in WP1.3
│   ├── missions/software-dev/
│   │   └── command-templates/         # SOURCE templates — edited in any WP that changes prose
│   ├── next/
│   │   └── prompt_builder.py          # call-site flip in WP1.3
│   ├── runtime/
│   │   └── doctor.py                  # resolver call-site touched in WP1.3
│   └── validators/
│       └── doctrine_curation.py       # DELETE in WP1.1
├── doctrine/
│   ├── agent_profiles/validation.py   # reject inline refs (if any) in WP1.3
│   ├── directives/
│   │   ├── _proposed/                 # DELETE entire dir in WP1.1
│   │   ├── models.py                  # strip inline fields in WP1.2
│   │   ├── validation.py              # reject inline refs in WP1.3
│   │   └── *.directive.yaml           # strip tactic_refs in WP1.2 (8 files)
│   ├── paradigms/
│   │   ├── _proposed/                 # DELETE entire dir in WP1.1
│   │   ├── models.py                  # strip inline fields in WP1.2
│   │   ├── validation.py              # reject inline refs in WP1.3
│   │   └── *.paradigm.yaml            # strip tactic_refs in WP1.2 (3 files)
│   ├── procedures/
│   │   ├── _proposed/                 # DELETE entire dir in WP1.1
│   │   ├── models.py                  # strip inline fields in WP1.2
│   │   ├── validation.py              # reject inline refs in WP1.3
│   │   └── *.procedure.yaml           # strip tactic_refs in WP1.2 (2 files)
│   ├── styleguides/_proposed/         # DELETE (empty) in WP1.1
│   ├── tactics/
│   │   ├── _proposed/                 # DELETE entire dir in WP1.1
│   │   └── validation.py              # reject inline refs in WP1.3
│   ├── toolguides/
│   │   ├── _proposed/                 # DELETE (empty) in WP1.1
│   │   └── validation.py              # reject inline refs in WP1.3
│   ├── curation/                      # DELETE entire package in WP1.1
│   ├── drg/
│   │   ├── loader.py                  # untouched
│   │   ├── models.py                  # untouched
│   │   ├── query.py                   # ADD resolve_transitive_refs() in WP1.3
│   │   └── validator.py               # untouched
│   ├── graph.yaml                     # additive-only remediation in WP1.2 if missing edges found
│   └── schemas/
│       ├── directive.schema.yaml      # strip inline ref fields in WP1.2
│       ├── paradigm.schema.yaml       # strip inline ref fields in WP1.2
│       └── procedure.schema.yaml      # strip inline ref fields in WP1.2

tests/
├── charter/
│   ├── test_context.py                # REWRITE in WP1.3 to target single builder
│   ├── test_context_parity.py         # DELETE in WP1.3 (after coverage subsumed)
│   └── test_reference_resolver.py     # DELETE in WP1.3 (replaced by drg/query tests)
├── doctrine/
│   ├── curation/                      # DELETE entire tree in WP1.1
│   ├── test_inline_ref_rejection.py   # NEW in WP1.3 — one fixture per kind
│   └── drg/
│       └── test_resolve_transitive_refs.py  # NEW in WP1.3
├── cross_cutting/
│   └── test_doctrine_curation_unit.py # DELETE in WP1.1
├── agent/test_workflow_charter_context.py  # UPDATE in WP1.3
└── (various model/consistency tests)  # UPDATE inline field assertions in WP1.2

scripts/
└── verify_occurrences.py              # NEW in WP1.1 (reused by WP1.2 / WP1.3)

kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/
├── index.yaml
├── WP1.1.yaml
├── WP1.2.yaml
└── WP1.3.yaml
```

**Structure Decision**: Single-project Python layout. All changes land in the existing `src/` and `tests/` trees. No new top-level directories introduced except `kitty-specs/.../occurrences/` (mission-scoped) and `scripts/verify_occurrences.py` (one helper script co-located with the existing `scripts/` directory if present, otherwise created). The twin charter packages (`src/charter/` and `src/specify_cli/charter/`) stay as two separate package trees — deduplicating them is explicitly out of scope for this mission.

---

## Plan-Phase Decisions (locked)

### D-1 — Context builder naming
**Decision**: Rename `build_context_v2` → `build_charter_context` during WP1.3 **only at the point the legacy implementation is removed**. Do not front-load the rename before the live-path cutover is complete.

**Rationale**: Front-loading the rename would leave a window where the legacy implementation and the new (renamed) implementation coexist under the same name — a debugging nightmare. Performing the rename inside the single WP1.3 PR ensures the cutover is atomic.

**Sequencing inside WP1.3**:
1. Add DRG-backed `resolve_transitive_refs` in `src/doctrine/drg/query.py`.
2. Flip `charter/resolver.py` and `charter/compiler.py` (and their `specify_cli/charter/` twins) to import the new function. Keep the legacy `reference_resolver.py` present but now unused by production paths; tests still exercise it.
3. Flip the five+ live `build_charter_context()` call sites to call `build_context_v2()` directly.
4. Run the full pytest suite at this point: legacy builder is imported by nothing in src; still exercised only by `tests/charter/test_context.py` (legacy) and `tests/charter/test_context_parity.py`.
5. Rename `build_context_v2` → `build_charter_context` in `src/charter/context.py`; delete the old `build_charter_context` implementation; update `charter/__init__.py` and `specify_cli/charter/__init__.py` re-exports; flip the five+ call sites back to the renamed import.
6. Delete `src/charter/reference_resolver.py` after the last importer is moved.
7. Delete `tests/charter/test_context_parity.py` and `tests/charter/test_reference_resolver.py` only **after** the replacement suites (`tests/charter/test_context.py` rewritten + `tests/doctrine/drg/test_resolve_transitive_refs.py` new) land green and demonstrably cover their behavioral surface.

### D-2 — Reference-resolver replacement location (Q1 = A) — **amended 2026-04-14**
**Decision**: Place the DRG-backed `resolve_transitive_refs()` in `src/doctrine/drg/query.py` alongside the existing `resolve_context()` primitive. Implement as a thin bucketing wrapper over the existing `walk_edges(graph, start_urns, relations, max_depth)` primitive. Return a `ResolveTransitiveRefsResult` with per-kind bucketed bare IDs (URN prefix stripped) — same field shape as legacy `ResolvedReferenceGraph`, plus `paradigms` and `agent_profiles` buckets that legacy lacked. See [`contracts/resolve-transitive-refs.contract.md`](contracts/resolve-transitive-refs.contract.md) for the full corrected contract.

**Input type**: `DRGGraph` (the live `doctrine.drg.models.DRGGraph`), NOT a fabricated `MergedGraph`. `merge_layers()` returns `DRGGraph`.

**Relation selection**: callers pass `{Relation.REQUIRES, Relation.SUGGESTS}` for legacy parity — these are the two relation kinds the Phase 0 migration extractor used when translating inline `tactic_refs`/`paradigm_refs` into DRG edges. Confirmed by reading `doctrine.drg.query.resolve_context()` (the Phase 0 reference implementation), which uses `REQUIRES` (transitive) and `SUGGESTS` (depth-limited) for artifact reachability.

**Caller-side helper**: introduce `src/charter/_drg_helpers.py :: _load_validated_graph(repo_root)` (+ `src/specify_cli/charter/_drg_helpers.py` twin) to encapsulate the `load_graph(doctrine_root/'graph.yaml')` + `merge_layers(shipped, project_overlay)` + `assert_valid(merged)` sequence. `resolver.py` and `compiler.py` each import the helper once. This avoids duplicating the 4-line graph-load sequence at every call site.

**Rationale**: Minimizes blast radius on the live path and keeps `charter/resolver.py` / `charter/compiler.py` / `charter generate` behavior-stable without requiring the deeper Phase 3 rewrite. The function is a DRG-layer capability (walk the merged graph), not a charter-layer capability, so it belongs in `src/doctrine/drg/`. Cycle detection is NOT relocated to this function — `assert_valid()` already rejects `requires` cycles at graph load; `walk_edges` is BFS-with-visited-set so `suggests` cycles are benign.

### D-3 — Twin-package lockstep
**Decision**: Every edit that touches `src/charter/{context,compiler,resolver,catalog,__init__}.py` also touches the equivalent `src/specify_cli/charter/*` file in the same WP PR. Occurrence artifacts list both file paths as separate `import_path` entries so the verifier catches a one-sided edit.

**Rationale**: The two packages are a known pre-existing wart. Deduplicating them is Phase 3+ work. Phase 1 cannot introduce drift between them.

### D-4 — Test architecture
**Decision**: Coverage is collapsed, not lost.

**Rules enforced in plan**:
- WP1.1: delete curation tests (`tests/doctrine/curation/**`, `tests/cross_cutting/test_doctrine_curation_unit.py`). No coverage loss — those tests only cover deleted code.
- WP1.2: update inline-field assertions in artifact model tests (7+ files) so they now assert the fields are **absent** from shipped YAMLs. No deletions.
- WP1.3: rewrite `tests/charter/test_context.py` as a single-builder suite; add `tests/doctrine/test_inline_ref_rejection.py` (one negative fixture per kind); add `tests/doctrine/drg/test_resolve_transitive_refs.py`. Run the rewritten + new tests in parallel with `test_context_parity.py` and `test_reference_resolver.py` and verify green. **Only then** delete `test_context_parity.py` and `test_reference_resolver.py`. This is the "collapse coverage, do not create a regression hole" rule.

### D-5 — Occurrence-classification artifact shape (per #393 + FR-015)
**Decision**: Per-WP YAML artifacts at `kitty-specs/.../occurrences/WP1.<n>.yaml` + mission-level aggregate at `kitty-specs/.../occurrences/index.yaml`. Schema defined in `contracts/occurrence-artifact.schema.yaml`. Verifier script `scripts/verify_occurrences.py` (added in WP1.1, reused by WP1.2/WP1.3) reads the artifact and asserts the "to-change" set is empty on disk.

**CI enforcement**: The verifier is run in each WP PR as a non-skippable check but implemented cheaply — it's a pure Python walk, no external services. If the implementation lands heavier than "cheap," per the user's guidance downgrade to a local pre-merge script + a mission-level aggregate check in the final WP PR.

### D-6 — Charter Check note
**Decision**: Informational only, not a gate. Governance-file absence does not block Phase 1.

### D-7 — Strict sequencing
**Decision**: WP1.1 → WP1.2 → WP1.3, each its own merged PR, each preflight-verified, each verifier-green before the next begins.

### D-8 — Research scope
**Decision**: Three narrow Phase 0 investigations captured in `research.md`:
- R-1: exhaustive inline-field inventory vs `graph.yaml` edge coverage — produce the "missing edges" remediation list for WP1.2.
- R-2: behavioral-equivalence proof for `resolve_references_transitively` vs proposed DRG walk — produce the `resolve_transitive_refs` contract in `contracts/`.
- R-3: stringly-typed reference audit for dynamic dispatch of `doctrine` / `curate` / `build_charter_context` / etc. — produce the final "string occurrences that static grep missed" list.

### D-9 — Phase 1 artifacts
**Decision**: Produced together with this plan — `data-model.md`, `quickstart.md`, and four contract files under `contracts/`.

---

## Work Package Shape (recommended for `/spec-kitty.tasks`)

Three sequential WPs. Each WP PR includes: source edits, test edits, its occurrence artifact, and a verifier-green CI run.

### WP1.1 — Excise curation surface (tracks [#476](https://github.com/Priivacy-ai/spec-kitty/issues/476))
**Scope**:
- Delete `src/doctrine/curation/` (entire package)
- Delete `src/specify_cli/cli/commands/doctrine.py`
- Delete `src/specify_cli/validators/doctrine_curation.py`
- Remove `app.add_typer(doctrine_module.app, name="doctrine")` from `src/specify_cli/cli/commands/__init__.py`
- Delete `src/doctrine/{directives,tactics,procedures,styleguides,toolguides,paradigms}/_proposed/` trees
- Delete `tests/doctrine/curation/**` and `tests/cross_cutting/test_doctrine_curation_unit.py`
- Update SOURCE templates under `src/specify_cli/missions/*/command-templates/` and `src/specify_cli/skills/` that reference any of the deleted surfaces (no agent-copy edits — agent dirs re-flow on upgrade)
- Add `scripts/verify_occurrences.py` (reused by WP1.2/WP1.3)
- Author `kitty-specs/.../occurrences/WP1.1.yaml` and seed `kitty-specs/.../occurrences/index.yaml`

**Acceptance gates for WP1.1 PR**:
- All tests green
- Verifier green against WP1.1.yaml
- `find src/doctrine -type d -name _proposed` → no output
- `test -d src/doctrine/curation` → non-zero
- `spec-kitty doctrine <anything>` on a dev-install returns unknown-command
- `mypy --strict` passes

### WP1.2 — Strip inline reference fields from shipped artifacts, schemas, models (tracks [#477](https://github.com/Priivacy-ai/spec-kitty/issues/477))
**Depends on**: WP1.1 merged.

**Scope**:
- Cross-check R-1 findings from `research.md` against `src/doctrine/graph.yaml`; add any missing edges to `graph.yaml` as an additive-only remediation before stripping inline refs
- Strip `tactic_refs:` from 8 directive YAMLs, 3 paradigm YAMLs, 2 procedure YAMLs in `src/doctrine/`
- Remove `tactic_refs`, `paradigm_refs`, `applies_to` field declarations from:
  - `src/doctrine/schemas/directive.schema.yaml`
  - `src/doctrine/schemas/paradigm.schema.yaml`
  - `src/doctrine/schemas/procedure.schema.yaml`
- Remove corresponding fields from Pydantic models under `src/doctrine/<kind>/models.py`
- Strip `applies_to: list[str]` from `src/charter/schemas.py :: Directive`
- Update model tests in `tests/doctrine/<kind>/test_models.py` and consistency tests under `tests/doctrine/` to assert the fields are absent
- Author `kitty-specs/.../occurrences/WP1.2.yaml` and update `index.yaml`

**Acceptance gates for WP1.2 PR**:
- All tests green
- Verifier green against WP1.2.yaml
- `grep -R "tactic_refs\|paradigm_refs\|applies_to" src/doctrine src/charter/schemas.py` returns zero hits outside explicit carve-outs listed in `index.yaml`
- `mypy --strict` passes
- WP1.1 acceptance gates still hold

### WP1.3 — Validators reject inline refs + single context builder + reference-resolver excision (tracks [#475](https://github.com/Priivacy-ai/spec-kitty/issues/475))
**Depends on**: WP1.2 merged.

**Scope** (amended 2026-04-14 per internal review):

**A. Baseline capture (must happen BEFORE any cutover step)**:
- Before touching any source, capture the pre-WP03 rendered-text baseline for NFR-002b: run `spec-kitty charter context --action <act> --json` for each bootstrap action (`specify`, `plan`, `implement`, `review`) on current `main` and commit the JSON responses under `kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/baseline/pre-wp03-context.json` (or one file per action). This file is the golden reference for the post-cutover byte-identity check.

**B. DRG-backed helper + tests**:
- Add `resolve_transitive_refs()` to `src/doctrine/drg/query.py` per the corrected [contracts/resolve-transitive-refs.contract.md](contracts/resolve-transitive-refs.contract.md) — uses the live `DRGGraph` / `Relation` / `walk_edges` API; callers pass `{Relation.REQUIRES, Relation.SUGGESTS}` for legacy parity
- Add `src/charter/_drg_helpers.py` + `src/specify_cli/charter/_drg_helpers.py` with `_load_validated_graph(repo_root)`
- Add `tests/doctrine/drg/test_resolve_transitive_refs.py` including the 7-dimensional coverage in the contract and the behavioral-equivalence fixture against the still-present legacy resolver

**C. Validator rejection**:
- Add `InlineReferenceRejectedError` (in `src/doctrine/shared/errors.py` or the existing shared-errors module)
- Update per-kind `validation.py` (7 files: directives/tactics/procedures/paradigms/styleguides/toolguides/agent_profiles) to pre-scan raw YAML for `tactic_refs`/`paradigm_refs`/`applies_to` and raise the structured error
- **Procedures path (FR-008 amendment)**: the procedures pre-scan checks both top-level keys AND each `steps[*]` entry, since `ProcedureStep.tactic_refs` is a declared Pydantic field on current `main` (line 54). The field is removed from `ProcedureStep` in WP02 as part of the model edits; WP03 adds the pre-Pydantic scan so procedures get the structured error rather than Pydantic's `extra_forbidden` generic error.
- Add `tests/doctrine/test_inline_ref_rejection.py` with one negative fixture per kind (7 total); the procedures fixture includes a step-level `tactic_refs:` entry to exercise the step-scan path

**D. Resolver/compiler flip**:
- Swap `resolve_references_transitively` → `resolve_transitive_refs` in `src/charter/resolver.py` and `src/charter/compiler.py` (and their `specify_cli/charter/*` twins)

**E. Context-builder cutover (strict D-1 sequencing)**:
- Flip the five live `build_charter_context()` call sites to `build_context_v2()` (temporary intermediate state)
- Rename `build_context_v2` → `build_charter_context`, delete legacy implementation, update re-exports in both `__init__.py` files, flip the five call sites back to the renamed import
- Add `tests/charter/test_merged_graph_on_live_path.py` asserting `assert_valid()` runs on bootstrap context builds (FR-016)
- **NFR-002b byte-parity check**: `spec-kitty charter context --action <act> --json` for each bootstrap action must now byte-match the baseline captured in step A. Diff must be empty.

**F. Legacy excision**:
- Delete `src/charter/reference_resolver.py`
- Delete `include_proposed` parameter from `src/charter/catalog.py :: load_doctrine_catalog()` and update all callers

**G. Test-coverage collapse (per D-4 — only after replacement green)**:
- Rewrite `tests/charter/test_context.py` as a single-builder suite; include the NFR-002a artifact-reachability parity contract inherited from the soon-to-be-deleted `test_context_parity.py`
- Add `tests/doctrine/drg/test_shipped_graph_valid.py` that calls `assert_valid(merge_layers(load_graph(graph.yaml), None))` — subsumes the cycle-detection coverage currently in `tests/doctrine/test_cycle_detection.py` and `tests/doctrine/test_shipped_doctrine_cycle_free.py`
- Delete `tests/charter/test_context_parity.py`
- Delete `tests/charter/test_reference_resolver.py`
- Delete `tests/doctrine/test_cycle_detection.py` (coverage rehomed to `test_shipped_graph_valid.py`)
- Delete `tests/doctrine/test_shipped_doctrine_cycle_free.py` (coverage rehomed)
- Update `tests/doctrine/test_artifact_kinds.py` — replace the three `from charter.reference_resolver import _REF_TYPE_MAP` uses with the equivalent `doctrine.artifact_kinds.ArtifactKind` public enum (or delete the affected test cases if they were purely about the private mapping)
- Update `tests/charter/test_resolver.py:293` — change the `patch("charter.resolver.resolve_references_transitively", ...)` target to `patch("charter.resolver.resolve_transitive_refs", ...)` with the new return-value shape
- Update `tests/charter/test_compiler.py:107` — comment reference to `resolve_references_transitively` becomes `resolve_transitive_refs`
- Update `tests/agent/test_workflow_charter_context.py` for the single-builder name

**H. Occurrence artifacts**:
- Author `kitty-specs/.../occurrences/WP1.3.yaml` and finalize `index.yaml` with the complete mission-level "zero occurrences" assertion; add `resolve_references_transitively`, `ResolvedReferenceGraph`, `_REF_TYPE_MAP`, `_Walker` to the must-be-zero set alongside the existing strings

**Acceptance gates for WP1.3 PR**:
- All tests green
- Verifier green against WP1.3.yaml and mission-level `index.yaml`
- `grep -R "build_context_v2\|reference_resolver\|resolve_references_transitively\|ResolvedReferenceGraph\|_REF_TYPE_MAP\|_Walker\|include_proposed" src tests` returns zero hits outside explicit carve-outs
- `grep -R "curation\|_proposed\|tactic_refs\|paradigm_refs\|applies_to" src tests` returns zero hits outside explicit carve-outs
- NFR-002a: post-WP03 `tests/charter/test_context.py` inherits the artifact-reachability parity contract from `test_context_parity.py` and passes for every (profile, action, depth) case previously exercised
- NFR-002b: `spec-kitty charter context --action <act> --json` for each bootstrap action byte-matches the pre-WP03 baseline committed under `kitty-specs/.../baseline/pre-wp03-context.json`
- Test suite runtime within the 5% regression budget vs the pre-WP1.1 baseline (NFR-001)
- `mypy --strict` passes

---

## Risk & Mitigation Plan (operational)

Cross-reference spec Risks section. Operational mitigations:

| Spec risk | Plan-phase mitigation |
| --- | --- |
| Missing `graph.yaml` edges for inline `tactic_refs` | Phase 0 R-1 produces the exhaustive inventory. WP1.2 adds missing edges **before** stripping YAML fields, atomically in the same PR. |
| Five-call-site inventory incomplete | Phase 0 R-3 runs static grep + Python AST walk + importlib/string-based dispatch search. The WP1.3 occurrence artifact must list every hit. |
| `compiler.py` / `resolver.py` carry non-resolver behavior we'd accidentally lose | Phase 0 R-2 produces the behavioral surface diff. Plan mandates "rewrite-not-delete" for both modules in WP1.3. |
| Per-kind validators drift during rewrite | FR-014 test suite demands one negative fixture per kind (7 kinds). CI blocks on missing coverage. |
| Test deletion cascade breaks unrelated imports | Verifier + `mypy --strict` + pytest collection run per PR. |
| NFR-001 runtime budget breached | Measured at WP1.3 PR; reshape fixtures if needed. |
| Out-of-order WP merge | Branch-level sequencing + the occurrence artifact's `requires_merged: [...]` field gates the verifier. |

---

## Complexity Tracking

No Charter Check violations. No complexity budget items. The only architectural addition is `resolve_transitive_refs()` in `src/doctrine/drg/query.py`, which is a contract-equivalent replacement for an existing (deleted) function.

---

## Branch Contract (restated)

- Current branch at plan start: `main`
- Planning/base branch: `main`
- Final merge target: `main`
- `branch_matches_target`: `true`

All three WP PRs open against `main` and merge back to `main`.

---

## Next Step

User runs `/spec-kitty.tasks --mission excise-doctrine-curation-and-inline-references-01KP54J6` to materialize the three WPs listed above.

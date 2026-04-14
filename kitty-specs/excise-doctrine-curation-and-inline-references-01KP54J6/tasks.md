# Tasks: Excise Doctrine Curation and Inline References

**Mission**: `excise-doctrine-curation-and-inline-references-01KP54J6`
**Plan**: [plan.md](plan.md)
**Spec**: [spec.md](spec.md)
**Branch**: `main` (planning base = merge target)
**Date**: 2026-04-14

## Branch Strategy

- **Current branch at task generation**: `main`
- **Planning/base branch**: `main`
- **Final merge target**: `main`
- Every WP opens a PR against `main` and merges back to `main`
- Execution workspaces are lane-based; `lanes.json` is computed by `finalize-tasks`

## Execution Order (strict, per spec C-007)

```
WP01 (tracks #476) ──► WP02 (tracks #477) ──► WP03 (tracks #475)
```

No WP can start until its predecessor is merged to `main`.

## Work Package Summary

| WP | Title | Issue | Subtasks | Estimated prompt | Depends on |
| --- | --- | --- | --- | --- | --- |
| WP01 | Excise curation surface | [#476](https://github.com/Priivacy-ai/spec-kitty/issues/476) | 6 | ~450 lines | — |
| WP02 | Strip inline reference fields from artifacts, schemas, models | [#477](https://github.com/Priivacy-ai/spec-kitty/issues/477) | 6 | ~450 lines | WP01 |
| WP03 | Validators reject + single context builder + legacy excision | [#475](https://github.com/Priivacy-ai/spec-kitty/issues/475) | 6 | ~550 lines | WP02 |

## Subtask Index

| ID | Description | WP | Parallel |
| --- | --- | --- | --- |
| T001 | Add verifier script + author `occurrences/WP01.yaml` | WP01 | | [D] |
| T002 | Delete `src/doctrine/curation/` package, `_proposed/` trees, and curation validator | WP01 | | [D] |
| T003 | Delete doctrine CLI command + Typer registration + add regression test | WP01 | | [D] |
| T004 | Delete curation test files | WP01 | [P] with T002/T003 | [D] |
| T005 | Update SOURCE templates + doctrine READMEs referencing removed surfaces | WP01 | [D] |
| T006 | Run gates + seed `occurrences/index.yaml` | WP01 | | [D] |
| T007 | Author `occurrences/WP02.yaml`; run R-1 inline-vs-graph audit | WP02 | |
| T008 | Patch `src/doctrine/graph.yaml` with any missing edges (additive-only) | WP02 | |
| T009 | Strip `tactic_refs:` from 13 shipped artifact YAMLs | WP02 | |
| T010 | Remove inline ref fields from schemas + Pydantic models + `src/charter/schemas.py` | WP02 | [P] with T009 |
| T011 | Update model and consistency tests to assert fields are absent | WP02 | |
| T012 | Delete R-1 script, run gates, update `occurrences/index.yaml` | WP02 | |
| T013 | Capture NFR-002b baseline; add `resolve_transitive_refs()` in `src/doctrine/drg/query.py` using live `DRGGraph`/`Relation`/`walk_edges` API; equivalence test suite vs legacy resolver | WP03 | |
| T014 | Add `InlineReferenceRejectedError` (incl. procedures step-level scan) to 7 per-kind validators + negative-fixture test suite covering top-level AND step-level rejection | WP03 | [P] with T013 |
| T015 | Add `_load_validated_graph` helper (twin packages); flip `resolver.py`/`compiler.py` (twins) to `resolve_transitive_refs` with `{REQUIRES, SUGGESTS}`; add live-path regression test | WP03 | |
| T016 | Flip 5 call sites to `build_context_v2`; rename `build_context_v2` → `build_charter_context`; delete legacy; update re-exports; NFR-002b byte-parity check against baseline | WP03 | |
| T017 | Delete `src/charter/reference_resolver.py`; remove `include_proposed` from `src/charter/catalog.py` + callers | WP03 | |
| T018 | Rewrite `tests/charter/test_context.py` (inherits NFR-002a reachability parity); add `test_shipped_graph_valid.py` (cycle-detection rehome); delete `test_context_parity.py`/`test_reference_resolver.py`/`test_cycle_detection.py`/`test_shipped_doctrine_cycle_free.py` only after replacement green; update `test_artifact_kinds.py`/`test_resolver.py`/`test_compiler.py`/`test_workflow_charter_context.py`; finalize occurrence artifacts | WP03 | |

The `[P]` markers indicate subtasks that can run in parallel within the same WP (different concerns, no shared files). All WP-level sequencing is strict.

---

## WP01 — Excise curation surface

**Tracks**: [#476](https://github.com/Priivacy-ai/spec-kitty/issues/476)
**Prompt**: [tasks/WP01-excise-curation-surface.md](tasks/WP01-excise-curation-surface.md)
**Dependencies**: none (first WP in the Phase 1 tranche)

### Summary

**Goal**: Delete every file, package, CLI surface, validator, and test that implements the `_proposed/` → `shipped/` curation workflow. After this WP merges, `src/doctrine/curation/` is gone, the `spec-kitty doctrine` CLI is unregistered, the six `_proposed/` directories (5 kinds empty + 1 kind populated + 1 kind populated) are gone, and a regression test prevents the CLI from ever being re-registered.

**Priority**: P0 — blocks WP02 and WP03.

**Independent test**: `spec-kitty doctrine <anything>` returns an unknown-command error. `find src/doctrine -type d -name _proposed` returns no rows. `test -d src/doctrine/curation` returns non-zero. `tests/specify_cli/cli/test_doctrine_cli_removed.py` passes.

### Included subtasks

- [x] T001 Add verifier script + author `occurrences/WP01.yaml` (WP01)
- [x] T002 Delete `src/doctrine/curation/` package, `_proposed/` trees, and `src/specify_cli/validators/doctrine_curation.py` (WP01)
- [x] T003 Delete `src/specify_cli/cli/commands/doctrine.py` + Typer registration + add regression test (WP01)
- [x] T004 Delete curation test files (`tests/doctrine/curation/**`, `tests/cross_cutting/test_doctrine_curation_unit.py`) (WP01)
- [x] T005 Update SOURCE templates + doctrine READMEs referencing removed surfaces (WP01)
- [x] T006 Run gates (pytest, mypy --strict, verifier) and seed `occurrences/index.yaml` with WP01 segment (WP01)

### Implementation sketch

1. Author occurrence artifact and verifier FIRST (T001) — it is the spec of what the WP deletes.
2. Delete files in dependency order (T002–T004): remove code packages before tests that depend on them.
3. Update SOURCE prose (T005) — agent copy dirs are NOT edited.
4. Run all gates locally (T006); open PR against `main`.

### Parallel opportunities

T004 (test deletions) can run in parallel with T002/T003 (source deletions) — different file trees.
T005 (prose updates) is independent and can run at any time.

### Risks

- SOURCE template references not caught by grep (e.g. string-based dispatch) → mitigated by R-3 audit captured in WP01 occurrence artifact.
- An unrelated test importing from a deleted module will go red → acceptable; fix imports or the test in the same PR.

### Requirements satisfied

FR-001, FR-002, FR-003, FR-004, FR-012 (partial — templates scope), FR-013 (curation-test scope), FR-015 (WP01 artifact).

---

## WP02 — Strip inline reference fields from artifacts, schemas, models

**Tracks**: [#477](https://github.com/Priivacy-ai/spec-kitty/issues/477)
**Prompt**: [tasks/WP02-strip-inline-reference-fields.md](tasks/WP02-strip-inline-reference-fields.md)
**Dependencies**: WP01

### Summary

**Goal**: Remove `tactic_refs`, `paradigm_refs`, `applies_to` from every shipped artifact YAML, every artifact schema, every Pydantic model, and from `src/charter/schemas.py :: Directive`. Before stripping YAML fields, audit `src/doctrine/graph.yaml` for missing edges that inline `tactic_refs:` implicitly encoded and add them atomically in the same PR. After this WP merges, the only source of truth for cross-artifact relationships is `graph.yaml` edges.

**Priority**: P0 — blocks WP03.

**Independent test**: `grep -R "tactic_refs\|paradigm_refs\|applies_to" src/doctrine src/charter/schemas.py` returns zero hits (outside explicit carve-outs documented in `occurrences/index.yaml`). All existing tests pass. `assert_valid()` on the merged graph still succeeds.

### Included subtasks

- [ ] T007 Author `occurrences/WP02.yaml`; add + run `scripts/r1_inline_vs_graph_audit.py`; generate missing-edges list (WP02)
- [ ] T008 Patch `src/doctrine/graph.yaml` with any missing edges (additive-only) (WP02)
- [ ] T009 Strip `tactic_refs:` from 13 shipped artifact YAMLs (8 directives, 3 paradigms, 2 procedures) (WP02)
- [ ] T010 Remove inline ref fields from 3 schemas + 7 Pydantic model files + strip `applies_to` from `src/charter/schemas.py :: Directive` (WP02)
- [ ] T011 Update model and consistency tests to assert fields are absent (WP02)
- [ ] T012 Delete R-1 script, run gates, update `occurrences/index.yaml` (WP02)

### Implementation sketch

1. Author WP02 occurrence artifact + run R-1 audit (T007). If `missing_edges.yaml` is non-empty, proceed to T008; else skip directly to T009.
2. Patch `graph.yaml` atomically before any YAML field stripping (T008) — this is the "atomicity" guarantee from the research.
3. Strip inline fields from YAML (T009) and from schema/model declarations (T010) — can run in parallel.
4. Update tests (T011) — single pass across the affected test directory.
5. Gate + update index (T012); open PR.

### Parallel opportunities

T009 (YAML edits) and T010 (schema/model edits) touch different file types — run in parallel once T008 lands.

### Risks

- R-1 reveals unexpectedly many missing edges → escalate per quickstart.md; possibly signals Phase 0 calibration gap.
- Pydantic model change breaks a fixture or test not caught by `test_models.py` → caught by full pytest run in T012.
- Schema comment/ordering churn from `ruamel.yaml` round-trip → use `ruamel.yaml` round-trip mode with preserved keys; minimize surface churn.

### Requirements satisfied

FR-005, FR-006, FR-007, FR-013 (model/consistency test scope), FR-015 (WP02 artifact).

---

## WP03 — Validators reject + single context builder + legacy excision

**Tracks**: [#475](https://github.com/Priivacy-ai/spec-kitty/issues/475)
**Prompt**: [tasks/WP03-single-context-builder-and-legacy-excision.md](tasks/WP03-single-context-builder-and-legacy-excision.md)
**Dependencies**: WP02

### Summary

**Goal**: (1) Add the DRG-backed replacement function `resolve_transitive_refs()` in `src/doctrine/drg/query.py` with a behavioral-equivalence proof against the legacy resolver. (2) Make every per-kind `validation.py` reject inline ref fields with `InlineReferenceRejectedError`. (3) Flip `resolver.py` + `compiler.py` (twin packages) to the DRG helper. (4) Flip the five `build_charter_context()` call sites to `build_context_v2()`, then rename `build_context_v2` → `build_charter_context`, delete the legacy implementation, and update re-exports. (5) Delete `src/charter/reference_resolver.py` and remove `include_proposed` from `src/charter/catalog.py`. (6) Rewrite `tests/charter/test_context.py` as a single-builder suite and delete parity + legacy resolver tests only after replacement coverage is green.

**Priority**: P0 — completes Phase 1 of EPIC #461.

**Independent test**:
- `grep -R "build_context_v2\|reference_resolver\|include_proposed" src tests` returns zero hits outside documented carve-outs
- `grep -R "curation\|_proposed\|tactic_refs\|paradigm_refs\|applies_to" src tests` returns zero hits outside documented carve-outs
- `spec-kitty charter context --action specify --json` matches the NFR-002 byte-identical Phase 0 golden set
- `tests/charter/test_merged_graph_on_live_path.py` passes
- `tests/doctrine/test_inline_ref_rejection.py` passes for all 7 kinds
- `tests/doctrine/drg/test_resolve_transitive_refs.py` passes including the behavioral-equivalence fixtures
- Full pytest runtime regression ≤5% vs pre-WP01 baseline (NFR-001)

### Included subtasks

- [ ] T013 Add `resolve_transitive_refs()` in `src/doctrine/drg/query.py` + `tests/doctrine/drg/test_resolve_transitive_refs.py` (including behavioral-equivalence suite against legacy resolver) (WP03)
- [ ] T014 Add `InlineReferenceRejectedError` to 7 per-kind `validation.py` files + `tests/doctrine/test_inline_ref_rejection.py` with one negative fixture per kind (WP03)
- [ ] T015 Flip `src/charter/resolver.py`, `src/charter/compiler.py`, and their `src/specify_cli/charter/*` twins to use `resolve_transitive_refs`; add `tests/charter/test_merged_graph_on_live_path.py` (WP03)
- [ ] T016 Flip 5 `build_charter_context` call sites to `build_context_v2` (intermediate); rename `build_context_v2` → `build_charter_context`; delete legacy implementation; update re-exports; flip call sites back to canonical name (WP03)
- [ ] T017 Delete `src/charter/reference_resolver.py`; remove `include_proposed` from `src/charter/catalog.py` + update all callers (WP03)
- [ ] T018 Rewrite `tests/charter/test_context.py` as single-builder suite; delete `tests/charter/test_context_parity.py` + `tests/charter/test_reference_resolver.py` (only after replacement green); author `occurrences/WP03.yaml`; finalize `occurrences/index.yaml` (WP03)

### Implementation sketch

Follow plan.md D-1 sequencing strictly. The subtask order above mirrors it:

1. **T013** additive: new function + its test suite (including behavioral equivalence vs the still-present legacy resolver) — nothing breaks.
2. **T014** additive: validators reject inline refs + negative-fixture tests — nothing in production references these paths yet.
3. **T015** cutover step 1: resolver.py/compiler.py use the new DRG helper; legacy build_charter_context still operates (now via DRG under the hood); add live-path regression test.
4. **T016** cutover step 2: flip call sites, rename, delete legacy implementation.
5. **T017** cleanup: delete `reference_resolver.py` + `include_proposed`.
6. **T018** test collapse: rewrite, delete parity/legacy tests only after replacement passes; finalize the mission-level occurrence assertion.

### Parallel opportunities

T013 and T014 are independent (different modules, different test files). T015+T016+T017+T018 are strictly sequential.

### Risks

- Behavioral equivalence fails for one shipped directive in T013 → fix `resolve_transitive_refs`, not the legacy resolver. Do NOT proceed to T015 until equivalence is green.
- Fifth or hidden call site missed in T016 → R-3 audit captured in WP03 occurrence artifact should catch it; if not, verifier fails and WP03 PR stays open.
- `assert_valid()` spy test (T015) is flaky due to module import ordering → use `unittest.mock.patch` at the call site not at definition.
- Parity/legacy test deletion in T018 is premature → explicit rule: run the full pytest suite with BOTH replacement and legacy present; only delete when replacement is independently green.

### Requirements satisfied

FR-008, FR-009, FR-010, FR-011, FR-013 (context/resolver test scope), FR-014, FR-015 (WP03 + index), FR-016, NFR-001, NFR-002, NFR-003, NFR-004.

---

## MVP Scope

There is no MVP subset here — the three WPs form an indivisible Phase 1 excision. WP01 alone leaves inline refs live; WP01+WP02 alone leaves the legacy resolver live. Only all three WPs landed together deliver the spec's Success Criteria. Per spec C-001 "no fallback, no backwards compatibility" and C-007 "strict sequencing," partial delivery is not a supported end state.

## Parallelization Highlights

- Within WP01: T004 (test deletion) runs in parallel with T002/T003 (source deletion).
- Within WP02: T009 (YAML edits) runs in parallel with T010 (schema/model edits) once T008 lands.
- Within WP03: T013 (DRG helper) runs in parallel with T014 (validator rejection).
- **Across WPs**: NO parallelization — strict sequential dependency per C-007.

## Next Steps

1. Run `spec-kitty agent mission finalize-tasks --mission excise-doctrine-curation-and-inline-references-01KP54J6 --json` to compute lanes, normalize metadata, and commit.
2. Start WP01 via `/spec-kitty.implement` (or the `/spec-kitty-implement-review` skill if implementing autonomously).
3. After WP01 merges to `main`, proceed to WP02, then WP03.

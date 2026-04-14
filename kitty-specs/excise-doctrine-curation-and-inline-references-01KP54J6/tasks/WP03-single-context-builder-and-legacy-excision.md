---
work_package_id: WP03
title: Validators reject + single context builder + legacy excision
dependencies:
- WP02
requirement_refs:
- FR-008
- FR-009
- FR-010
- FR-011
- FR-013
- FR-014
- FR-015
- FR-016
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
history:
- at: '2026-04-14T05:02:32Z'
  actor: claude
  event: created
authoritative_surface: src/charter/
execution_mode: code_change
owned_files:
- src/doctrine/drg/query.py
- src/doctrine/directives/validation.py
- src/doctrine/tactics/validation.py
- src/doctrine/procedures/validation.py
- src/doctrine/paradigms/validation.py
- src/doctrine/styleguides/validation.py
- src/doctrine/toolguides/validation.py
- src/doctrine/agent_profiles/validation.py
- src/charter/context.py
- src/charter/resolver.py
- src/charter/compiler.py
- src/charter/catalog.py
- src/charter/reference_resolver.py
- src/charter/__init__.py
- src/charter/README.md
- src/specify_cli/charter/context.py
- src/specify_cli/charter/resolver.py
- src/specify_cli/charter/compiler.py
- src/specify_cli/charter/__init__.py
- src/specify_cli/cli/commands/charter.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/next/prompt_builder.py
- src/specify_cli/runtime/doctor.py
- tests/charter/test_context.py
- tests/charter/test_context_parity.py
- tests/charter/test_reference_resolver.py
- tests/charter/test_merged_graph_on_live_path.py
- tests/charter/test_resolver.py
- tests/doctrine/drg/test_resolve_transitive_refs.py
- tests/doctrine/test_inline_ref_rejection.py
- tests/agent/test_workflow_charter_context.py
tags: []
---

# WP03 — Validators reject + single context builder + legacy excision

**Tracks**: [Priivacy-ai/spec-kitty#475](https://github.com/Priivacy-ai/spec-kitty/issues/475)
**Depends on**: WP02 merged to `main`
**Merges to**: `main`
**Completes**: Phase 1 of EPIC [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461)

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Execution mode**: lane-based worktree allocated by `finalize-tasks`. Run `spec-kitty agent action implement WP03 --agent <name> --mission excise-doctrine-curation-and-inline-references-01KP54J6` to resolve the actual workspace path and branch.
- **Do NOT start** until WP02 is merged to `main` (per spec C-007).

---

## Objective

Close Phase 1 with the final cutover:

1. **Add** the DRG-backed replacement `resolve_transitive_refs()` in `src/doctrine/drg/query.py`.
2. **Add** validator rejection of inline refs across 7 per-kind `validation.py` files.
3. **Flip** `resolver.py` and `compiler.py` (both twin packages) to use the DRG helper.
4. **Flip** the 5 live `build_charter_context` call sites to `build_context_v2`; **rename** `build_context_v2` → `build_charter_context`; **delete** the legacy implementation.
5. **Delete** `src/charter/reference_resolver.py` and the `include_proposed` parameter on `src/charter/catalog.py`.
6. **Collapse** test coverage: rewrite `tests/charter/test_context.py` as single-builder suite; delete parity + legacy resolver tests ONLY after replacement coverage is green (per plan D-4 "collapse coverage, do not create a regression hole").

After this WP merges, `build_charter_context` is the only context builder, `resolve_transitive_refs` is the only transitive resolution path, every inline-ref field on any doctrine artifact is a hard error, and Phase 1 of EPIC #461 is complete.

## Context

- Legacy `build_charter_context()` has 5 live call sites on `main`:
  - `src/specify_cli/next/prompt_builder.py:273`
  - `src/specify_cli/cli/commands/charter.py:314`
  - `src/specify_cli/cli/commands/agent/workflow.py:192`
  - `src/charter/__init__.py:23` (re-export)
  - `src/specify_cli/charter/__init__.py:23` (re-export)
  - Also `src/specify_cli/charter/context.py:30` defines its own wrapper.
- `resolve_references_transitively()` is used by `src/charter/resolver.py:14` and indirectly by `src/charter/compiler.py` via the resolver layer.
- `resolve_governance()` (which uses `resolve_references_transitively` via `resolver.py`) is called from 6 places; this is the legacy governance pipeline that underpins `build_charter_context`.
- `build_context_v2()` at `src/charter/context.py:495` is parity-safe after PR #609, has zero callers on `main`, and already uses DRG query primitives internally.
- Twin charter packages `src/charter/` and `src/specify_cli/charter/` carry parallel copies of `context.py`, `compiler.py`, `resolver.py`, `__init__.py`. Both get updated in this WP per plan D-3.

## Authoritative files (read before starting)

- [spec.md](../spec.md) — FR-008…FR-016; NFR-001…NFR-004; C-001…C-007
- [plan.md](../plan.md) — WP1.3 section + D-1 sequencing + D-3 twin-package + D-4 test architecture
- [research.md](../research.md) — R-2 (resolver equivalence) + R-3 (stringly-typed audit)
- [data-model.md](../data-model.md) — E-3 (Validator Rejection Error) + E-4 (ResolveTransitiveRefsResult) + E-6 (Artifact post-shape)
- [contracts/resolve-transitive-refs.contract.md](../contracts/resolve-transitive-refs.contract.md) — the replacement function contract
- [contracts/validator-rejection-error.schema.json](../contracts/validator-rejection-error.schema.json) — structured error shape
- [contracts/occurrence-artifact.schema.yaml](../contracts/occurrence-artifact.schema.yaml) — artifact schema

---

## Subtask details

### T013 — Add `resolve_transitive_refs()` in `src/doctrine/drg/query.py` + equivalence test suite

**Purpose**: Introduce the DRG-backed replacement for the legacy transitive resolver. Must be behaviorally equivalent to `resolve_references_transitively()` for every shipped artifact. Tests prove the equivalence BEFORE any call-site flip happens.

**Steps**:

1. Edit `src/doctrine/drg/query.py` to add:
   - `ResolveTransitiveRefsResult` dataclass (frozen) matching the field shape of `charter.reference_resolver.ResolvedReferenceGraph`. See [contracts/resolve-transitive-refs.contract.md](../contracts/resolve-transitive-refs.contract.md) for exact signature.
   - `resolve_transitive_refs(merged_graph, *, starting_artifact_ids) -> ResolveTransitiveRefsResult` function implementing DFS over `uses` / `references` edges with cycle detection.
   - Raise `DoctrineResolutionCycleError` on cycle; import from `doctrine.shared.exceptions`.
   - Sort all returned lists lexicographically for determinism.

2. Create `tests/doctrine/drg/test_resolve_transitive_refs.py` covering:
   - **Deterministic output**: same graph + same starting IDs → same result, ordering stable.
   - **DAG convergence**: a fixture where A uses B, A uses C, both B and C use D — D appears once in result.
   - **Cycle detection**: a `uses` cycle raises `DoctrineResolutionCycleError`.
   - **Unknown starting ID**: recorded in `unresolved`, no raise.
   - **Edge kind filter**: `requires` edges NOT walked (fixture with both `uses` and `requires` edges from same source; only `uses`-reachable artifacts returned).
   - **Behavioral equivalence**: for each of the 8 shipped directives that carried inline `tactic_refs:` on pre-WP02 state, the legacy resolver (if still reachable in the codebase at this step — which it is; T017 deletes it later) and the new function produce identical output sets. Use a golden fixture snapshot of the legacy output captured at plan time if the legacy resolver is difficult to instantiate in test context.

3. Run the test suite:
   ```bash
   pytest tests/doctrine/drg/test_resolve_transitive_refs.py -v
   ```
   All tests must pass. Equivalence failures block progression to T015.

**Files**:
- Modified: `src/doctrine/drg/query.py` (add ~120 LOC)
- Created: `tests/doctrine/drg/test_resolve_transitive_refs.py` (~250 LOC)
- Optional: `tests/doctrine/drg/fixtures/` for graph fixtures used by this suite

**Validation**:
- [ ] `pytest tests/doctrine/drg/test_resolve_transitive_refs.py` passes
- [ ] `mypy --strict src/doctrine/drg/query.py` passes
- [ ] The behavioral-equivalence test covers at least 8 directives (one per pre-WP02 inline-ref carrier)

**Parallel opportunity**: T013 and T014 are independent.

---

### T014 — Add `InlineReferenceRejectedError` to 7 per-kind validators + negative-fixture test suite

**Purpose**: Enforce the new "no inline refs" contract at the validator boundary. Each per-kind `validation.py` rejects any YAML containing `tactic_refs`, `paradigm_refs`, or `applies_to` with a structured error.

**Steps**:

1. Create `src/doctrine/shared/errors.py` (or add to an existing shared errors module if one exists) with:
   ```python
   from dataclasses import dataclass

   @dataclass
   class InlineReferenceRejectedError(ValueError):
       """Raised when a doctrine artifact YAML carries a forbidden inline reference field.

       See contracts/validator-rejection-error.schema.json for the structured shape.
       """
       file_path: str
       forbidden_field: str   # "tactic_refs" | "paradigm_refs" | "applies_to"
       artifact_kind: str     # "directive" | "tactic" | "procedure" | "paradigm" | "styleguide" | "toolguide" | "agent_profile"
       migration_hint: str

       def __post_init__(self) -> None:
           super().__init__(
               f"Inline reference rejected in {self.file_path}:\n"
               f"  artifact_kind: {self.artifact_kind}\n"
               f"  forbidden_field: {self.forbidden_field}\n"
               f"  migration: {self.migration_hint}"
           )
   ```

2. Update each of 7 per-kind `validation.py` files:
   ```
   src/doctrine/directives/validation.py
   src/doctrine/tactics/validation.py
   src/doctrine/procedures/validation.py
   src/doctrine/paradigms/validation.py
   src/doctrine/styleguides/validation.py
   src/doctrine/toolguides/validation.py
   src/doctrine/agent_profiles/validation.py
   ```

   In each: after parsing the YAML but before schema validation, check for any of the three forbidden keys at the top level (and for `procedures`, also inside `steps[*]`). On hit, raise `InlineReferenceRejectedError` with the structured fields.

   `migration_hint` format per [contracts/validator-rejection-error.schema.json](../contracts/validator-rejection-error.schema.json):
   ```
   Remove <field> from YAML; add edge {from: <kind>:<id>, to: <target-kind>:<target-id>, kind: uses} to src/doctrine/graph.yaml
   ```

3. Create `tests/doctrine/test_inline_ref_rejection.py` with one negative fixture per artifact kind (7 fixtures total). Each fixture:
   - Creates a temporary YAML on disk containing the forbidden field
   - Invokes the kind's validator
   - Asserts `InlineReferenceRejectedError` is raised
   - Asserts the error fields (`file_path`, `forbidden_field`, `artifact_kind`, `migration_hint`) match expectations

4. Run:
   ```bash
   pytest tests/doctrine/test_inline_ref_rejection.py -v
   ```
   All 7 test cases must pass.

**Files**:
- Created: `src/doctrine/shared/errors.py` (~30 LOC) (or extended if exists)
- Modified: 7 per-kind `validation.py` files (~20 LOC each)
- Created: `tests/doctrine/test_inline_ref_rejection.py` (~200 LOC)

**Validation**:
- [ ] `pytest tests/doctrine/test_inline_ref_rejection.py` passes for all 7 kinds
- [ ] `mypy --strict src/doctrine/` passes
- [ ] Loading any shipped artifact still succeeds (WP02 already stripped the forbidden fields, so no false positives)

**Parallel opportunity**: T014 runs in parallel with T013.

---

### T015 — Flip `resolver.py` + `compiler.py` (twin packages) to `resolve_transitive_refs` + add live-path regression test

**Purpose**: Switch the first live-path caller to the DRG helper. After this subtask, `resolve_governance()` and `compile_charter()` use the DRG merged-graph walk. Legacy `build_charter_context()` still operates (it delegates to `resolve_governance`, which is now DRG-backed). This is the first cutover step in plan D-1.

**Steps**:

1. Edit `src/charter/resolver.py`:
   - Remove `from charter.reference_resolver import resolve_references_transitively` (line 14)
   - Add `from doctrine.drg.query import resolve_transitive_refs` and helpers (`load_graph`, `merge_layers`, `assert_valid`)
   - At each former call site of `resolve_references_transitively(doctrine_service, starting_ids)`:
     - Load merged graph + validate (can be factored into a helper `_load_merged_validated_graph(repo_root)` if used multiple times)
     - Call `resolve_transitive_refs(merged, starting_artifact_ids=starting_ids)`
     - Consume the returned result (same field names as the legacy — no downstream call-site changes needed)

2. Edit `src/charter/compiler.py`:
   - Same treatment — remove the legacy resolver import, add the DRG helper
   - Preserve `compile_charter()`'s signature and behavior except that transitive refs now come from DRG

3. Edit the twin files `src/specify_cli/charter/resolver.py` and `src/specify_cli/charter/compiler.py` identically.

4. Run full pytest:
   ```bash
   pytest tests/
   ```
   All tests must pass. The behavioral-equivalence test from T013 is the authority for "legacy output == DRG output."

5. Create `tests/charter/test_merged_graph_on_live_path.py` (FR-016 regression):
   ```python
   """Regression test: assert_valid() runs on the live path of build_charter_context.

   Ensures the Phase 0 merged-graph validator is not bypassed as the live path
   evolves through Phase 1 cutovers.
   """
   from unittest.mock import patch
   from pathlib import Path
   from charter.context import build_charter_context


   def test_assert_valid_runs_on_bootstrap_context_build(tmp_path_with_charter):
       """build_charter_context for a bootstrap action triggers assert_valid()."""
       with patch("doctrine.drg.validator.assert_valid") as mock_validator:
           build_charter_context(tmp_path_with_charter, action="specify", mark_loaded=False)
       assert mock_validator.called, "assert_valid() was not called during context build"


   # Additional tests: non-bootstrap action does NOT trigger validator (compact mode)
   # Non-bootstrap action returns compact text without invoking full DRG load
   ```
   Note: at this subtask step, `build_charter_context` still delegates to `resolve_governance` which is now DRG-backed. The assertion target may need to be `charter.resolver.assert_valid` or similar — adjust based on the actual import path in resolver.py.

6. Run:
   ```bash
   pytest tests/charter/test_merged_graph_on_live_path.py -v
   ```
   Must pass.

**Files**:
- Modified: `src/charter/resolver.py`
- Modified: `src/charter/compiler.py`
- Modified: `src/specify_cli/charter/resolver.py`
- Modified: `src/specify_cli/charter/compiler.py`
- Created: `tests/charter/test_merged_graph_on_live_path.py` (~80 LOC)

**Validation**:
- [ ] Full pytest green
- [ ] `mypy --strict src/` passes
- [ ] `grep -n "resolve_references_transitively" src/` — only `reference_resolver.py` (the file to be deleted in T017) hits
- [ ] Manual smoke: `spec-kitty charter generate` in a test project succeeds (exercises `compile_charter`)

---

### T016 — Flip 5 call sites to `build_context_v2`; rename; delete legacy

**Purpose**: Atomically cut over `build_charter_context` from legacy implementation to the `build_context_v2` implementation. This is the critical rename sequence in plan D-1.

**Steps** (follow order exactly — intermediate state between steps is coherent but temporary):

1. **Flip 5 call sites to `build_context_v2`** (intermediate):
   - `src/specify_cli/next/prompt_builder.py:273` — change `build_charter_context(...)` → `build_context_v2(...)`, update import at top
   - `src/specify_cli/cli/commands/charter.py:314` — same treatment
   - `src/specify_cli/cli/commands/agent/workflow.py:192` — same treatment
   - `src/charter/__init__.py` — re-export `build_context_v2` alongside (or instead of) `build_charter_context`
   - `src/specify_cli/charter/__init__.py` — same
   - `src/specify_cli/charter/context.py` — if this file defines its own `build_charter_context` wrapper, update it to delegate to `build_context_v2`

   Run pytest — must pass. At this step, `build_context_v2` is the real live builder; legacy `build_charter_context` is reachable only through the old re-export (if retained) and internal tests.

2. **Rename `build_context_v2` → `build_charter_context`** in `src/charter/context.py`:
   - Delete the legacy `build_charter_context()` function (lines ~33–119 on current `main`)
   - Rename `build_context_v2` (lines ~495+) to `build_charter_context`. Remove the `profile` parameter docstring note that says "Phase 0 degenerate — ignored" if appropriate (the parameter itself stays for Phase 4).
   - Update the module docstring and section comment (`# build_context_v2 -- DRG-based context assembly (T020)` → remove or rename)

3. **Update re-exports**:
   - `src/charter/__init__.py` — remove any `build_context_v2` export; keep `build_charter_context`
   - `src/specify_cli/charter/__init__.py` — same
   - `src/specify_cli/charter/context.py` — flip call/wrapper back to canonical name

4. **Flip 5 call sites back to `build_charter_context`**:
   - `src/specify_cli/next/prompt_builder.py` — back to `build_charter_context(...)`
   - `src/specify_cli/cli/commands/charter.py` — same
   - `src/specify_cli/cli/commands/agent/workflow.py` — same
   - (The `__init__.py` re-exports are already at the new single name)

5. **Update `src/charter/README.md`** — the table at the top mentions `context.py :: build_charter_context()`; the description no longer needs the "legacy" qualifier (if it exists).

6. Run full pytest:
   ```bash
   pytest tests/
   ```
   All tests must pass. The ONLY place `build_context_v2` may still appear is in `tests/charter/test_context_parity.py` and possibly `tests/charter/test_context.py` — those are addressed in T018.

**Files**:
- Modified: `src/charter/context.py` (delete legacy impl, rename v2)
- Modified: `src/specify_cli/next/prompt_builder.py`
- Modified: `src/specify_cli/cli/commands/charter.py`
- Modified: `src/specify_cli/cli/commands/agent/workflow.py`
- Modified: `src/charter/__init__.py`
- Modified: `src/specify_cli/charter/__init__.py`
- Modified: `src/specify_cli/charter/context.py`
- Modified: `src/charter/README.md`

**Validation**:
- [ ] `grep -nE "build_context_v2" src/` returns only references being removed; after step 4, zero src hits
- [ ] `grep -nE "^def build_charter_context" src/charter/context.py src/specify_cli/charter/context.py` returns each file's single definition (the renamed v2)
- [ ] Full pytest green
- [ ] `mypy --strict src/` clean
- [ ] Smoke: `spec-kitty charter context --action specify --json` returns same output as pre-WP03 Phase 0 golden fixture (NFR-002 parity check)

---

### T017 — Delete `src/charter/reference_resolver.py`; remove `include_proposed` from `src/charter/catalog.py`

**Purpose**: Final code deletion. Legacy transitive resolver and the catalog's `include_proposed` flag.

**Steps**:

1. Verify no remaining in-src importers of `reference_resolver` before deletion:
   ```bash
   grep -rn "reference_resolver\|resolve_references_transitively\|ResolvedReferenceGraph" src/
   ```
   Must return zero hits. If it still returns hits, go back to T015 and finish the flip.

2. Delete the file:
   ```bash
   rm -f src/charter/reference_resolver.py
   ```

3. Edit `src/charter/catalog.py`:
   - Find `load_doctrine_catalog(..., include_proposed: bool = False, ...)` signature (~line 44)
   - Remove the `include_proposed` parameter from the signature
   - Remove the internal logic (lines 60–101 on current `main`) that conditionally includes `_proposed/` artifacts
   - Clean up the resulting function body

4. Update every caller of `load_doctrine_catalog(...)`. Grep:
   ```bash
   grep -rn "load_doctrine_catalog" src/ tests/
   ```
   Remove any `include_proposed=...` keyword arguments.

5. Run pytest:
   ```bash
   pytest tests/
   ```
   All tests must pass. `tests/charter/test_reference_resolver.py` is still present and still passes (it tests file that no longer exists? — no, the file deletion in step 2 SHOULD break this test; it will be deleted in T018 after replacement is green).

   Actually, at this point, `tests/charter/test_reference_resolver.py` will FAIL with `ImportError`. That is the signal to proceed to T018 which deletes it. **DO NOT** silently delete the test in this subtask — keep the failure visible so T018 has the explicit justification.

   If you want pytest to stay green here (recommended to keep the subtask-level gate meaningful), delete `tests/charter/test_reference_resolver.py` as part of T017 AFTER the behavioral-equivalence test in `tests/doctrine/drg/test_resolve_transitive_refs.py` from T013 is confirmed green. Note this in the PR description.

6. Run `mypy --strict src/` — must pass.

**Files**:
- Deleted: `src/charter/reference_resolver.py`
- Modified: `src/charter/catalog.py` (remove `include_proposed`)
- Modified: caller files (any that passed `include_proposed=...`)
- (Conditional): Deleted: `tests/charter/test_reference_resolver.py` — see discussion above

**Validation**:
- [ ] `test -f src/charter/reference_resolver.py` returns non-zero
- [ ] `grep -rn "reference_resolver\|resolve_references_transitively\|ResolvedReferenceGraph\|include_proposed" src/` returns zero hits
- [ ] Full pytest green
- [ ] `mypy --strict src/` clean

---

### T018 — Rewrite `tests/charter/test_context.py`; delete parity + legacy resolver tests; finalize occurrence artifacts

**Purpose**: Collapse test coverage onto the single builder and the new DRG helper. Delete parity and legacy resolver tests ONLY after their replacement coverage is demonstrably green (plan D-4 "collapse coverage, do not create a regression hole"). Finalize mission-level occurrence assertion.

**Steps**:

1. **Rewrite `tests/charter/test_context.py`** as a single-builder suite. Target the renamed `build_charter_context()` (which is the former `build_context_v2`). Coverage dimensions required:
   - Bootstrap vs compact mode (state-dependent depth)
   - First-load state management + persistence (`context-state.json`)
   - Non-bootstrap action always returns compact
   - Missing charter file returns `mode="missing"`
   - Directive filtering via `governance.doctrine.selected_directives`
   - Action guideline rendering via `MissionTemplateRepository.get_action_guidelines()`
   - Merged-graph validation called on the live path (may delegate to `tests/charter/test_merged_graph_on_live_path.py` for that dimension)

   Use the Phase 0 golden fixture outputs (from `tests/charter/test_context_parity.py` era) as the golden set for NFR-002 byte-identical output per spec.

2. **Verify replacement coverage** by running:
   ```bash
   pytest tests/charter/test_context.py tests/charter/test_merged_graph_on_live_path.py tests/doctrine/drg/test_resolve_transitive_refs.py tests/doctrine/test_inline_ref_rejection.py -v
   ```
   All must be green. Visually confirm the new test surface covers:
   - Context-builder semantics (previously in `test_context.py` + `test_context_parity.py`)
   - Transitive resolution semantics (previously in `test_reference_resolver.py`)
   - Graph-validation-on-live-path (new dimension; FR-016)

3. **Delete legacy tests** — ONLY after step 2 is green:
   ```bash
   rm -f tests/charter/test_context_parity.py
   ```
   If `tests/charter/test_reference_resolver.py` wasn't already deleted in T017, delete it here:
   ```bash
   rm -f tests/charter/test_reference_resolver.py
   ```

4. **Update related tests**:
   - `tests/agent/test_workflow_charter_context.py` — update any `build_charter_context` references if the signature changed (profile parameter, etc.)
   - `tests/charter/test_resolver.py` — update if it imported `resolve_references_transitively`

5. **Run full pytest**:
   ```bash
   pytest tests/
   ```
   All green.

6. **Author `occurrences/WP03.yaml`** per [contracts/occurrence-artifact.schema.yaml](../contracts/occurrence-artifact.schema.yaml):
   - Categories: `import_path`, `symbol_name`, `template_reference`, `test_identifier`
   - Strings tracked: `reference_resolver`, `resolve_references_transitively`, `ResolvedReferenceGraph`, `build_context_v2`, `include_proposed`
   - `expected_final_count: 0` for each string outside permitted exceptions
   - `requires_merged: [WP01, WP02]`

7. **Finalize `occurrences/index.yaml`**:
   - `wps: [WP01, WP02, WP03]`
   - Full `must_be_zero` list per spec NFR-004:
     ```
     curation, _proposed, tactic_refs, paradigm_refs, applies_to,
     reference_resolver, include_proposed, build_context_v2
     ```
   - `permitted_exceptions` union across all three WPs

8. **Run all verifier checks**:
   ```bash
   python scripts/verify_occurrences.py kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/WP03.yaml
   python scripts/verify_occurrences.py kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/index.yaml
   ```
   Both `VERIFIER GREEN`.

9. **NFR-002 byte-parity check**:
   ```bash
   # Capture pre-WP03 baseline BEFORE starting this WP (save to /tmp/preWP03_context.json)
   # Then compare:
   diff <(spec-kitty charter context --action specify --json --mission excise-doctrine-curation-and-inline-references-01KP54J6) /tmp/preWP03_context.json
   ```
   Diff should be empty (byte-identical). If non-empty, the cutover introduced parity drift; debug.

10. **NFR-001 runtime-budget check**:
    ```bash
    pytest --durations=0 > /tmp/post_wp03_durations.txt
    # Compare total runtime against baseline captured before WP01:
    #   p50 over three CI runs; must stay within 5%.
    ```

11. **Final comprehensive grep**:
    ```bash
    grep -rEn "curation|_proposed|tactic_refs|paradigm_refs|applies_to|reference_resolver|include_proposed|build_context_v2" src tests \
      | grep -v 'kitty-specs/' \
      | grep -v 'scripts/verify_occurrences.py' \
      | grep -v 'm_3_1_1_charter_rename.py'
    ```
    Must return zero rows.

**Files**:
- Rewritten: `tests/charter/test_context.py`
- Deleted: `tests/charter/test_context_parity.py`
- Deleted (if not already in T017): `tests/charter/test_reference_resolver.py`
- Modified: `tests/agent/test_workflow_charter_context.py`
- Modified: `tests/charter/test_resolver.py`
- Created: `kitty-specs/.../occurrences/WP03.yaml`
- Modified: `kitty-specs/.../occurrences/index.yaml`

**Validation**:
- [ ] Full pytest green
- [ ] `mypy --strict src/` clean
- [ ] Both verifier commands green
- [ ] NFR-002 byte-parity diff empty
- [ ] NFR-001 runtime within 5% of baseline
- [ ] Final comprehensive grep returns zero rows

---

## Definition of Done

- All six subtasks (T013-T018) complete
- `resolve_transitive_refs()` exists in `src/doctrine/drg/query.py`; equivalence suite passes
- `InlineReferenceRejectedError` raised by all 7 per-kind validators; negative-fixture test suite passes
- `src/charter/resolver.py` and `src/charter/compiler.py` (+ their `specify_cli/charter/` twins) flipped to the DRG helper
- `build_charter_context` exists as the single context-builder name; legacy implementation deleted; `build_context_v2` removed
- `src/charter/reference_resolver.py` deleted
- `include_proposed` parameter removed from `src/charter/catalog.py` and all callers
- `tests/charter/test_context.py` rewritten; parity + legacy resolver tests deleted; new regression test for merged-graph-on-live-path passes
- `kitty-specs/.../occurrences/WP03.yaml` green; mission-level `index.yaml` finalized with full must-be-zero set
- NFR-002 byte parity empty; NFR-001 runtime within budget
- `mypy --strict src/` clean; full pytest green
- PR opened against `main`, body references #475, includes every verifier/grep/parity/runtime output

**After this PR merges, Phase 1 of EPIC #461 is complete.**

## Risks & Reviewer Guidance

**Reviewer must check**:

1. **Equivalence proof**: T013's behavioral-equivalence test covers every shipped directive that carried `tactic_refs:` on pre-WP02 state (8 directives). Not a subset.

2. **Cutover atomicity**: T016's intermediate state (post step 1, pre step 5) is held for the minimum duration; ideally steps 1-5 are one commit or tightly adjacent commits. The PR should read as a single coherent cutover, not a migration across many unrelated commits.

3. **Test collapse, not test loss**: `git log --diff-filter=D --stat` should show the deleted parity/legacy-resolver tests, and `git log --diff-filter=A` should show the new/rewritten tests. Reviewer confirms the new suite covers the dimensions the deleted suite did. The specify-phase inventory and plan D-4 name the responsible surfaces.

4. **Twin-package lockstep**: every change to `src/charter/*` has a corresponding change to `src/specify_cli/charter/*`. A one-sided edit is a bug.

5. **No silent fallback introduced**: no try/except blocks that swallow the new `InlineReferenceRejectedError`; no deprecation shims; no backwards-compat aliases.

6. **Parity check**: the NFR-002 byte-identical diff is genuinely empty. Any output drift even of whitespace means the cutover changed behavior.

7. **Occurrence artifact accuracy**: the mission-level `index.yaml` permitted_exceptions list is minimal and every entry has a rationale. The canonical must-be-zero set matches spec NFR-004 literally.

**Common mistakes to avoid**:

- Front-loading the rename (violates plan D-1 — rename happens after the call-site flip)
- Deleting `tests/charter/test_context_parity.py` before the rewritten `tests/charter/test_context.py` is green (violates plan D-4 and spec user-adjustment #3)
- Forgetting one of the `src/specify_cli/charter/*` twin files (D-3 violation)
- Replacing the legacy resolver with a `DoctrineService`-based fallback instead of the DRG helper (violates R-2 decision — the DRG is the authority)
- Adding a deprecation warning to `build_charter_context` or `load_doctrine_catalog` (violates C-001)
- Letting `mypy --strict` slip with a `# type: ignore` comment on the new helper (violates NFR-003)

## Escalation criteria

Stop and comment on [#475](https://github.com/Priivacy-ai/spec-kitty/issues/475) if:
- Behavioral-equivalence test (T013) fails for any shipped directive — debug in `resolve_transitive_refs`, NOT in the legacy resolver
- NFR-002 byte-parity diff is non-empty after T018 — investigate whether the rename introduced any semantic drift
- NFR-001 runtime budget projected to breach — reshape test fixtures before relaxing the budget
- A caller of `build_charter_context` discovered outside the known five sites — R-3 audit was incomplete; document and expand scope
- A production module depends on `include_proposed=True` that the specify-phase inventory missed — escalate rather than reinstating the flag
- `assert_valid()` starts raising on `main` after the graph-patch from WP02 — indicates a cycle or duplicate edge was introduced; regress WP02 if needed

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
agent: "opencode:gpt-5:python-reviewer:reviewer"
shell_pid: "85568"
history:
- at: '2026-04-14T05:02:32Z'
  actor: claude
  event: created
authoritative_surface: src/charter/
execution_mode: code_change
owned_files:
- src/doctrine/drg/query.py
- src/doctrine/shared/errors.py
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
- src/charter/_drg_helpers.py
- src/charter/__init__.py
- src/charter/README.md
- src/specify_cli/charter/context.py
- src/specify_cli/charter/resolver.py
- src/specify_cli/charter/compiler.py
- src/specify_cli/charter/_drg_helpers.py
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
- tests/charter/test_compiler.py
- tests/doctrine/drg/test_resolve_transitive_refs.py
- tests/doctrine/drg/test_shipped_graph_valid.py
- tests/doctrine/test_inline_ref_rejection.py
- tests/doctrine/test_cycle_detection.py
- tests/doctrine/test_shipped_doctrine_cycle_free.py
- tests/doctrine/test_artifact_kinds.py
- tests/agent/test_workflow_charter_context.py
- kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/baseline/**
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

### T013 — Capture NFR-002b baseline; add `resolve_transitive_refs()`; equivalence test suite

**Purpose**: (a) capture the rendered-text baseline BEFORE any source touches (NFR-002b has no golden set on `main` today), (b) introduce the DRG-backed replacement for the legacy transitive resolver using the **live** `DRGGraph` / `Relation` / `walk_edges` API, (c) prove behavioral equivalence to the legacy resolver BEFORE any call-site flip.

> **Contract correction (2026-04-14)**: the earlier contract referenced a fabricated `MergedGraph` type and `uses`/`references` edge kinds. The live DRG uses `DRGGraph` as the merged-graph type and the `Relation` enum with 8 values (`requires, suggests, applies, scope, vocabulary, instantiates, replaces, delegates_to`). For legacy parity with `resolve_references_transitively`, callers pass `{Relation.REQUIRES, Relation.SUGGESTS}` — these are the two relation kinds the Phase 0 migration extractor used when translating inline `tactic_refs` into DRG edges. See the updated [contracts/resolve-transitive-refs.contract.md](../contracts/resolve-transitive-refs.contract.md).

**Steps**:

1. **Capture NFR-002b baseline FIRST** (before touching any source):
   ```bash
   mkdir -p kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/baseline
   for action in specify plan implement review; do
     spec-kitty charter context --action "$action" --json \
       > "kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/baseline/pre-wp03-context-$action.json"
   done
   ```
   Commit these files at the start of WP03. They are the golden reference for T016's byte-identity check.

2. Edit `src/doctrine/drg/query.py` to add:
   - `ResolveTransitiveRefsResult` frozen dataclass with per-kind bucketed lists (directives, tactics, paradigms, styleguides, toolguides, procedures, agent_profiles) plus `unresolved` — see the corrected contract.
   - `resolve_transitive_refs(graph: DRGGraph, *, start_urns: set[str], relations: set[Relation], max_depth: int | None = None) -> ResolveTransitiveRefsResult` — thin bucketing wrapper over `walk_edges`. Do **not** reimplement BFS; delegate to the existing `walk_edges` primitive.

   Skeleton:
   ```python
   from doctrine.drg.models import DRGGraph, NodeKind, Relation

   @dataclass(frozen=True)
   class ResolveTransitiveRefsResult:
       directives: list[str] = field(default_factory=list)
       tactics: list[str] = field(default_factory=list)
       paradigms: list[str] = field(default_factory=list)
       styleguides: list[str] = field(default_factory=list)
       toolguides: list[str] = field(default_factory=list)
       procedures: list[str] = field(default_factory=list)
       agent_profiles: list[str] = field(default_factory=list)
       unresolved: list[tuple[str, str]] = field(default_factory=list)

       @property
       def is_complete(self) -> bool:
           return len(self.unresolved) == 0


   def resolve_transitive_refs(
       graph: DRGGraph,
       *,
       start_urns: set[str],
       relations: set[Relation],
       max_depth: int | None = None,
   ) -> ResolveTransitiveRefsResult:
       visited_urns = walk_edges(graph, start_urns=start_urns, relations=relations, max_depth=max_depth)
       buckets: dict[NodeKind, list[str]] = {k: [] for k in NodeKind}
       unresolved: list[tuple[str, str]] = []
       for urn in visited_urns:
           node = graph.get_node(urn)
           if node is None:
               unresolved.append((urn, urn))  # defensive; assert_valid should prevent this
               continue
           # Strip "<kind>:" prefix per contract
           bare_id = urn.split(":", 1)[1] if ":" in urn else urn
           buckets[node.kind].append(bare_id)
       for k in NodeKind:
           buckets[k].sort()
       return ResolveTransitiveRefsResult(
           directives=buckets[NodeKind.DIRECTIVE],
           tactics=buckets[NodeKind.TACTIC],
           paradigms=buckets[NodeKind.PARADIGM],
           styleguides=buckets[NodeKind.STYLEGUIDE],
           toolguides=buckets[NodeKind.TOOLGUIDE],
           procedures=buckets[NodeKind.PROCEDURE],
           agent_profiles=buckets[NodeKind.AGENT_PROFILE],
           unresolved=unresolved,
       )
   ```

3. Create `tests/doctrine/drg/test_resolve_transitive_refs.py` covering all seven dimensions from the contract:
   - **Deterministic output** — lists lex-sorted.
   - **Empty start set** — returns empty result.
   - **Unknown starting URN** — appears in `unresolved`, no raise.
   - **Edge-kind filter** — given `{REQUIRES: A→B, SUGGESTS: A→C, SCOPE: A→D}`, walking with `relations={REQUIRES}` from `{A}` returns only `B`.
   - **Bucketing by kind** — visited URNs across kinds land in the correct lists; URN prefix stripped.
   - **`max_depth` forwarding** — `max_depth=1` excludes depth-2 nodes.
   - **Behavioral equivalence against legacy** — for every shipped directive that carried inline `tactic_refs:` on pre-WP02 state, assert:
     ```python
     legacy = resolve_references_transitively([directive_id], doctrine_service)
     drg = resolve_transitive_refs(
         graph, start_urns={f"directive:{directive_id}"},
         relations={Relation.REQUIRES, Relation.SUGGESTS},
     )
     assert sorted(legacy.directives) == sorted(drg.directives)
     assert sorted(legacy.tactics) == sorted(drg.tactics)
     assert sorted(legacy.styleguides) == sorted(drg.styleguides)
     assert sorted(legacy.toolguides) == sorted(drg.toolguides)
     assert sorted(legacy.procedures) == sorted(drg.procedures)
     assert legacy.is_complete == drg.is_complete
     ```
     The legacy resolver is still present at this subtask step (T017 deletes it). If equivalence fails, either the migration extractor didn't map an inline ref to a `{REQUIRES, SUGGESTS}` edge (escalate per research.md R-2), or the caller has passed the wrong relation set.

4. Run:
   ```bash
   pytest tests/doctrine/drg/test_resolve_transitive_refs.py -v
   ```
   All tests must pass. Equivalence failures **block** progression to T015.

**Files**:
- Created: `kitty-specs/.../baseline/pre-wp03-context-{specify,plan,implement,review}.json` (4 JSON captures)
- Modified: `src/doctrine/drg/query.py` (add ~80–120 LOC)
- Created: `tests/doctrine/drg/test_resolve_transitive_refs.py` (~200–250 LOC)
- Optional: `tests/doctrine/drg/fixtures/` for graph fixtures used by this suite

**Validation**:
- [ ] Four `pre-wp03-context-*.json` files exist and are committed
- [ ] `pytest tests/doctrine/drg/test_resolve_transitive_refs.py` passes all 7 dimensions
- [ ] `mypy --strict src/doctrine/drg/query.py` passes
- [ ] Behavioral-equivalence test covers every pre-WP02 `tactic_refs:` carrier (≥8 directives)

**Parallel opportunity**: T013 (excluding baseline capture in step 1, which must happen first) and T014 are independent.

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

   In each: after parsing the YAML (raw dict form) but BEFORE Pydantic schema validation, check for any of the three forbidden keys at the top level. On hit, raise `InlineReferenceRejectedError`.

   **Procedures (step-level) — MANDATORY**: `src/doctrine/procedures/validation.py` must additionally iterate every entry in `steps[*]` and check for `tactic_refs` on each step. On hit, raise `InlineReferenceRejectedError` with `artifact_kind="procedure"` and a migration hint that references the step context. Without this scan, procedures would fall through to Pydantic's `extra_forbidden` error (after WP02 removes `ProcedureStep.tactic_refs`), which is a valid rejection but lacks the structured migration hint the spec requires.

   Example procedures check:
   ```python
   def _reject_inline_refs(raw: dict, file_path: str) -> None:
       for forbidden in ("tactic_refs", "paradigm_refs", "applies_to"):
           if forbidden in raw:
               raise InlineReferenceRejectedError(
                   file_path=file_path,
                   forbidden_field=forbidden,
                   artifact_kind="procedure",
                   migration_hint=_build_migration_hint(forbidden, raw.get("id", "?"), "procedure"),
               )
       for i, step in enumerate(raw.get("steps", []) or []):
           if isinstance(step, dict):
               for forbidden in ("tactic_refs", "paradigm_refs"):
                   if forbidden in step:
                       raise InlineReferenceRejectedError(
                           file_path=file_path,
                           forbidden_field=forbidden,
                           artifact_kind="procedure",
                           migration_hint=(
                               f"Remove {forbidden} from YAML steps[{i}]; add edge "
                               f"{{from: procedure:{raw.get('id','?')}, to: <target-kind>:<target-id>, kind: uses}} "
                               f"to src/doctrine/graph.yaml"
                           ),
                       )
   ```

   `migration_hint` format per [contracts/validator-rejection-error.schema.json](../contracts/validator-rejection-error.schema.json):
   ```
   Remove <field> from YAML; add edge {from: <kind>:<id>, to: <target-kind>:<target-id>, kind: uses} to src/doctrine/graph.yaml
   ```

3. Create `tests/doctrine/test_inline_ref_rejection.py` with negative fixtures per artifact kind (7 top-level fixtures + 1 extra procedures step-level fixture = 8 cases total). Each fixture:
   - Creates a temporary YAML on disk containing the forbidden field
   - Invokes the kind's validator
   - Asserts `InlineReferenceRejectedError` is raised
   - Asserts the error fields (`file_path`, `forbidden_field`, `artifact_kind`, `migration_hint`) match expectations

   **Procedures fixtures are doubled**:
   - `test_procedure_top_level_tactic_refs_rejected` — YAML with top-level `tactic_refs: [...]`
   - `test_procedure_step_level_tactic_refs_rejected` — YAML with `steps: [{..., tactic_refs: [...]}]`. The second fixture proves the step-level scan works; without it, a regression (deleting the loop over `steps`) would silently revert to Pydantic's generic error.

4. Run:
   ```bash
   pytest tests/doctrine/test_inline_ref_rejection.py -v
   ```
   All 8 test cases must pass.

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

### T015 — Add `_drg_helpers`; flip `resolver.py` + `compiler.py` (twin packages) to `resolve_transitive_refs`; add live-path regression test

**Purpose**: Switch the first live-path caller to the DRG helper. After this subtask, `resolve_governance()` and `compile_charter()` use the DRG merged-graph walk. Legacy `build_charter_context()` still operates (it delegates to `resolve_governance`, which is now DRG-backed). This is the first cutover step in plan D-1.

**Steps**:

1. Create `src/charter/_drg_helpers.py` with a shared helper so resolver.py/compiler.py don't duplicate the graph-load sequence:
   ```python
   """Shared DRG graph-load helpers for charter resolver and compiler."""
   from __future__ import annotations
   from pathlib import Path
   from charter.catalog import resolve_doctrine_root
   from doctrine.drg.loader import load_graph, merge_layers
   from doctrine.drg.models import DRGGraph
   from doctrine.drg.validator import assert_valid


   def load_validated_graph(repo_root: Path) -> DRGGraph:
       """Load shipped + project merged DRG and validate it.

       Returns a validated DRGGraph. Raises any DRG validation error from
       `assert_valid()`.
       """
       doctrine_root = resolve_doctrine_root()
       shipped = load_graph(doctrine_root / "graph.yaml")
       project_path = repo_root / ".kittify" / "doctrine" / "graph.yaml"
       project = load_graph(project_path) if project_path.exists() else None
       merged = merge_layers(shipped, project)
       assert_valid(merged)
       return merged
   ```
   Create an identical `src/specify_cli/charter/_drg_helpers.py` twin.

2. Edit `src/charter/resolver.py`:
   - Remove `from charter.reference_resolver import resolve_references_transitively` (line 14 on current `main`)
   - Add `from charter._drg_helpers import load_validated_graph`, `from doctrine.drg.models import Relation`, `from doctrine.drg.query import resolve_transitive_refs`
   - At each former call site of `resolve_references_transitively([...], doctrine_service)`:
     - Call `graph = load_validated_graph(repo_root)` to get the validated `DRGGraph`
     - Build start URNs: `start_urns = {f"directive:{d}" for d in starting_directive_ids}` (adapt the kind prefix to whatever the caller's starting IDs represent — almost always directives at this site)
     - Call `result = resolve_transitive_refs(graph, start_urns=start_urns, relations={Relation.REQUIRES, Relation.SUGGESTS})`
     - Consume `result.directives`, `result.tactics`, etc. — same field names as the legacy `ResolvedReferenceGraph`

3. Edit `src/charter/compiler.py`:
   - Same treatment — remove the legacy resolver import chain (indirectly via `resolver.py` — `compiler.py` itself may or may not import `reference_resolver` directly; check and handle both cases)
   - Preserve `compile_charter()`'s signature and behavior except that transitive refs now come from DRG

4. Edit the twin files `src/specify_cli/charter/resolver.py` and `src/specify_cli/charter/compiler.py` identically using `src/specify_cli/charter/_drg_helpers.py`.

5. Update `src/specify_cli/runtime/doctor.py` — it calls `resolve_governance(project_dir)` which internally now uses the DRG. No direct code change needed here unless `doctor.py` directly imports from `charter.reference_resolver` (it doesn't on current `main`; double-check). Touched only to verify it still runs.

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

7. **NFR-002b byte-parity check** against the baseline captured in T013:
   ```bash
   for action in specify plan implement review; do
     diff \
       "kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/baseline/pre-wp03-context-$action.json" \
       <(spec-kitty charter context --action "$action" --json)
   done
   ```
   Every diff must be empty. If any diff is non-empty, the cutover introduced rendered-text drift — debug before proceeding to T017.

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

### T018 — Rewrite `tests/charter/test_context.py`; rehome cycle-detection coverage; delete legacy tests; finalize occurrence artifacts

**Purpose**: Collapse test coverage onto the single builder and the new DRG helpers. Delete parity, legacy resolver, and cycle-detection tests ONLY after their replacement coverage is demonstrably green (plan D-4 "collapse coverage, do not create a regression hole"). Finalize mission-level occurrence assertion.

> **Scope correction (2026-04-14)**: an earlier draft of this subtask only enumerated `test_reference_resolver.py` and `test_context_parity.py` for deletion, but four additional test files on `main` import from `charter.reference_resolver` directly — `tests/doctrine/test_cycle_detection.py`, `tests/doctrine/test_shipped_doctrine_cycle_free.py`, `tests/doctrine/test_artifact_kinds.py` (imports private `_REF_TYPE_MAP`), `tests/charter/test_resolver.py` (patches the symbol at line 293), and `tests/charter/test_compiler.py` (comment reference at line 107). All must be handled in this subtask.

**Steps**:

1. **Rewrite `tests/charter/test_context.py`** as a single-builder suite. Target the renamed `build_charter_context()` (which is the former `build_context_v2`). Coverage dimensions required:
   - Bootstrap vs compact mode (state-dependent depth)
   - First-load state management + persistence (`context-state.json`)
   - Non-bootstrap action always returns compact
   - Missing charter file returns `mode="missing"`
   - Directive filtering via `governance.doctrine.selected_directives`
   - Action guideline rendering via `MissionTemplateRepository.get_action_guidelines()`
   - Merged-graph validation called on the live path (may delegate to `tests/charter/test_merged_graph_on_live_path.py` for that dimension)
   - **NFR-002a artifact-reachability parity** — inherit the contract from `tests/charter/test_context_parity.py`: for every (profile, action, depth) combination the current parity suite exercises, the rewritten builder's artifact URN set must match the DRG-resolved set. This is the structural contract. The rendered-text byte-parity (NFR-002b) is separately enforced at T016 against the baseline captured in T013.

2. **Create `tests/doctrine/drg/test_shipped_graph_valid.py`** as the rehome target for cycle-detection coverage:
   ```python
   """Regression test: shipped graph.yaml + project overlay is always cycle-free and valid.

   Replaces coverage previously in tests/doctrine/test_cycle_detection.py and
   tests/doctrine/test_shipped_doctrine_cycle_free.py, which imported from the
   deleted charter.reference_resolver module.

   assert_valid() rejects:
   - dangling edges (target URN not in nodes)
   - duplicate edges
   - cycles in the 'requires' subgraph
   """
   from pathlib import Path
   from doctrine.drg.loader import load_graph, merge_layers
   from doctrine.drg.validator import assert_valid

   SHIPPED_GRAPH = Path(__file__).resolve().parents[3] / "src" / "doctrine" / "graph.yaml"


   def test_shipped_graph_loads_and_validates() -> None:
       graph = load_graph(SHIPPED_GRAPH)
       merged = merge_layers(graph, None)
       assert_valid(merged)  # raises on any violation


   def test_shipped_graph_has_no_requires_cycles() -> None:
       graph = load_graph(SHIPPED_GRAPH)
       merged = merge_layers(graph, None)
       # assert_valid checks requires cycles; exercise it as an explicit assertion
       assert_valid(merged)
   ```

3. **Verify replacement coverage** by running:
   ```bash
   pytest tests/charter/test_context.py \
          tests/charter/test_merged_graph_on_live_path.py \
          tests/doctrine/drg/test_resolve_transitive_refs.py \
          tests/doctrine/drg/test_shipped_graph_valid.py \
          tests/doctrine/test_inline_ref_rejection.py -v
   ```
   All must be green. Visually confirm the new test surface covers:
   - Context-builder semantics (previously in `test_context.py` + `test_context_parity.py`)
   - Transitive resolution semantics (previously in `test_reference_resolver.py`)
   - Cycle detection (previously in `test_cycle_detection.py` + `test_shipped_doctrine_cycle_free.py`)
   - Graph-validation-on-live-path (new dimension; FR-016)

4. **Delete legacy tests** — ONLY after step 3 is green:
   ```bash
   rm -f tests/charter/test_context_parity.py
   rm -f tests/doctrine/test_cycle_detection.py
   rm -f tests/doctrine/test_shipped_doctrine_cycle_free.py
   ```
   If `tests/charter/test_reference_resolver.py` wasn't already deleted in T017, delete it here:
   ```bash
   rm -f tests/charter/test_reference_resolver.py
   ```

5. **Update related tests** (not deleted; edited to remove references to dead symbols):
   - **`tests/doctrine/test_artifact_kinds.py`** — three call sites (lines 121, 126, 131) import `_REF_TYPE_MAP` from `charter.reference_resolver`. Replace with the public `doctrine.artifact_kinds.ArtifactKind` enum. The private mapping was `{kind.value: kind.plural for kind in ArtifactKind}` — reconstruct it inline in the test if the assertion still makes sense, or delete the affected test cases if they were testing private-mapping implementation details rather than artifact-kind semantics.
   - **`tests/charter/test_resolver.py:293`** — change `patch("charter.resolver.resolve_references_transitively", return_value=monkeypatch_graph)` to `patch("charter.resolver.resolve_transitive_refs", return_value=monkeypatch_graph_in_new_shape)`. The monkeypatch value must be a `ResolveTransitiveRefsResult` instance (not a `ResolvedReferenceGraph`).
   - **`tests/charter/test_compiler.py:107`** — update the comment reference to the new function name.
   - **`tests/agent/test_workflow_charter_context.py`** — update any `build_charter_context` references if the signature changed (profile parameter handling).

6. **Run full pytest**:
   ```bash
   pytest tests/
   ```
   All green.

6. **Author `occurrences/WP03.yaml`** per [contracts/occurrence-artifact.schema.yaml](../contracts/occurrence-artifact.schema.yaml):
   - Categories: `import_path`, `symbol_name`, `template_reference`, `test_identifier`, `docstring_or_comment`
   - Strings tracked (expanded per 2026-04-14 review): `reference_resolver`, `resolve_references_transitively`, `ResolvedReferenceGraph`, `_REF_TYPE_MAP`, `_Walker`, `build_context_v2`, `include_proposed`
   - `expected_final_count: 0` for each string outside permitted exceptions
   - `requires_merged: [WP01, WP02]`

7. **Finalize `occurrences/index.yaml`**:
   - `wps: [WP01, WP02, WP03]`
   - Full `must_be_zero` list (expanded per 2026-04-14 review):
     ```
     curation, _proposed, tactic_refs, paradigm_refs, applies_to,
     reference_resolver, resolve_references_transitively, ResolvedReferenceGraph,
     _REF_TYPE_MAP, _Walker, include_proposed, build_context_v2
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

## Activity Log

- 2026-04-14T07:03:53Z – claude:opus-4.6:python-implementer:implementer – shell_pid=8091 – Started implementation via action command
- 2026-04-14T07:51:37Z – claude:opus-4.6:python-implementer:implementer – shell_pid=8091 – WP03 complete: resolve_transitive_refs added in doctrine/drg/query.py using live DRGGraph+walk_edges API, InlineReferenceRejectedError rejecting 7 kinds including procedures step-level (FR-008), resolver+compiler twins flipped to DRG helper, build_charter_context renamed from v2 + legacy deleted, reference_resolver.py deleted, include_proposed removed, all 5 expected inter-WP failures now green (4 passing, 1 deleted as obsolete), NFR-002b byte-parity diff empty for all 4 actions, parity/legacy tests deleted after replacement green, occurrences/{WP03.yaml,index.yaml} both VERIFIER GREEN, full pytest 11202 passing.
- 2026-04-14T07:53:35Z – opencode:gpt-5:python-reviewer:reviewer – shell_pid=85568 – Started review via action command

---
work_package_id: WP04
title: DRG Wiring
dependencies:
- WP03
requirement_refs:
- FR-004
- FR-005
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
agent: "claude:opus-4.7:implementer-ivan:implementer"
shell_pid: "52671"
history:
- action: created
  at: '2026-04-26T19:46:00Z'
  by: tasks
authoritative_surface: src/doctrine/graph.yaml
execution_mode: code_change
owned_files:
- src/doctrine/graph.yaml
- tests/specify_cli/test_documentation_drg_nodes.py
tags: []
---

# WP04 — DRG Wiring

## Objective

Add 6 documentation action nodes and ~22 scope edges to `src/doctrine/graph.yaml`, mirroring the research action wiring at `src/doctrine/graph.yaml:5-19` (nodes) and `:577-630` (edges). Author `tests/specify_cli/test_documentation_drg_nodes.py` proving DRG node existence, `resolve_context` non-emptiness, action-bundle ↔ DRG-edge consistency, and the NFR-007 latency bound.

## Context

The validated DRG (`charter._drg_helpers.load_validated_graph`) is the consumer of `action:documentation/*` nodes. Without these nodes, `resolve_context()` returns an empty `artifact_urns` set for documentation actions and the right-sized governance context contract (FR-005) is broken. The research mission added its 5 action nodes + edges by hand-authoring graph.yaml; we mirror exactly.

Reference: [data-model.md → DRG node and edge shapes](../data-model.md#drg-node-and-edge-shapes) for the full node/edge content. [contracts/drg-shape.md](../contracts/drg-shape.md) is the regression contract.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution: `spec-kitty agent action implement WP04 --agent <name>`. Depends on WP03 (action-bundle slugs must match the URN edges 1-to-1).

## Subtasks

### T017 — Add 6 nodes to `src/doctrine/graph.yaml`

**Steps**:
1. Read the existing `src/doctrine/graph.yaml` `nodes:` block, specifically lines 1-40 (the `action:` URN family).
2. Add 6 nodes alphabetically intermixed with the existing `action:` entries:
   ```yaml
   - urn: action:documentation/audit
     kind: action
     label: audit
   - urn: action:documentation/design
     kind: action
     label: design
   - urn: action:documentation/discover
     kind: action
     label: discover
   - urn: action:documentation/generate
     kind: action
     label: generate
   - urn: action:documentation/publish
     kind: action
     label: publish
   - urn: action:documentation/validate
     kind: action
     label: validate
   ```
3. Verify YAML parses cleanly: `python -c "import yaml; yaml.safe_load(open('src/doctrine/graph.yaml'))"`.

**Files**: `src/doctrine/graph.yaml` (edit only).

**Validation**:
- [ ] All 6 nodes present.
- [ ] YAML parses.

### T018 — Add ~22 scope edges to `src/doctrine/graph.yaml`

**Steps**:
1. Locate the `edges:` block (starts around line 450).
2. Append the documentation edges per the [data-model.md edges table](../data-model.md#edges-add-to-srcdoctrinegraphyaml-edges-block). Total 22 edges:
   - `discover` (4): DIRECTIVE_003, DIRECTIVE_010, requirements-validation-workflow, premortem-risk-identification.
   - `audit` (3): DIRECTIVE_003, DIRECTIVE_037, requirements-validation-workflow.
   - `design` (5): DIRECTIVE_001, DIRECTIVE_003, DIRECTIVE_010, adr-drafting-workflow, requirements-validation-workflow.
   - `generate` (3): DIRECTIVE_010, DIRECTIVE_037, requirements-validation-workflow.
   - `validate` (4): DIRECTIVE_010, DIRECTIVE_037, premortem-risk-identification, requirements-validation-workflow.
   - `publish` (3): DIRECTIVE_010, DIRECTIVE_037, requirements-validation-workflow.

   Each edge uses the shape:
   ```yaml
   - source: action:documentation/<action>
     target: directive:DIRECTIVE_<NNN>  # or tactic:<slug>
     relation: scope
   ```

3. Verify validated load succeeds:
   ```bash
   uv run --python 3.13 --extra test python -c "
   from pathlib import Path
   from charter._drg_helpers import load_validated_graph
   g = load_validated_graph(Path('.'))
   for action in ('discover','audit','design','generate','validate','publish'):
       assert g.get_node(f'action:documentation/{action}'), f'missing: {action}'
   print('OK')
   "
   ```

**Files**: `src/doctrine/graph.yaml` (edit only).

**Validation**:
- [ ] 22 edges present.
- [ ] Validated graph load succeeds.
- [ ] Every documentation action has at least 3 scope edges.
- [ ] No duplicate edges.

### T019 — Author `tests/specify_cli/test_documentation_drg_nodes.py`

**Purpose**: enforce FR-004, FR-005, FR-006, NFR-007 + the action-bundle/edge consistency contract.

**Steps**:
1. Create the test file:

   ```python
   """DRG node and resolve_context regression tests for documentation mission (#502)."""

   from __future__ import annotations

   import statistics
   import time
   from pathlib import Path

   import pytest
   import yaml

   from charter._drg_helpers import load_validated_graph
   from doctrine.drg.query import resolve_context

   _REPO_ROOT = Path(__file__).resolve().parents[2]
   _DOC_ACTIONS = ("discover", "audit", "design", "generate", "validate", "publish")
   _RESEARCH_ACTIONS = ("scoping", "methodology", "gathering", "synthesis", "output")


   _SLUG_TO_URN = {
       "001-architectural-integrity-standard": "directive:DIRECTIVE_001",
       "003-decision-documentation-requirement": "directive:DIRECTIVE_003",
       "010-specification-fidelity-requirement": "directive:DIRECTIVE_010",
       "037-living-documentation-sync": "directive:DIRECTIVE_037",
       "requirements-validation-workflow": "tactic:requirements-validation-workflow",
       "premortem-risk-identification": "tactic:premortem-risk-identification",
       "adr-drafting-workflow": "tactic:adr-drafting-workflow",
   }


   @pytest.mark.parametrize("action", _DOC_ACTIONS)
   def test_each_documentation_action_has_drg_node_and_context(action: str) -> None:
       """FR-004 + FR-005: DRG node exists and resolve_context returns artifact_urns."""
       graph = load_validated_graph(_REPO_ROOT)
       node = graph.get_node(f"action:documentation/{action}")
       assert node is not None, f"missing DRG node: action:documentation/{action}"

       ctx = resolve_context(graph, f"action:documentation/{action}", depth=2)
       assert ctx.artifact_urns, (
           f"empty artifact_urns for action:documentation/{action}; "
           "verify graph.yaml edges from this action node to directives/tactics."
       )


   @pytest.mark.parametrize("action", _DOC_ACTIONS)
   def test_action_bundle_matches_drg_edges(action: str) -> None:
       """FR-006: action-bundle index.yaml directives/tactics match graph.yaml URN edges."""
       bundle = yaml.safe_load(
           (_REPO_ROOT / "src" / "doctrine" / "missions" / "documentation" / "actions" / action / "index.yaml").read_text(encoding="utf-8")
       )
       expected_urns = {
           _SLUG_TO_URN[slug]
           for slug in (bundle.get("directives", []) + bundle.get("tactics", []))
       }

       graph_yaml = yaml.safe_load((_REPO_ROOT / "src" / "doctrine" / "graph.yaml").read_text(encoding="utf-8"))
       actual_urns = {
           edge["target"]
           for edge in graph_yaml.get("edges", [])
           if edge.get("source") == f"action:documentation/{action}"
           and edge.get("relation") == "scope"
       }

       assert expected_urns == actual_urns, (
           f"bundle ↔ DRG mismatch for {action}: "
           f"bundle has {expected_urns}, graph has {actual_urns}"
       )


   def test_resolve_context_within_research_2x() -> None:
       """NFR-007: documentation resolve_context median ≤ 2× research median."""
       graph = load_validated_graph(_REPO_ROOT)

       def median_runs(actions: tuple[str, ...], mission: str) -> float:
           durations: list[float] = []
           for _ in range(5):
               for action in actions:
                   t0 = time.perf_counter()
                   resolve_context(graph, f"action:{mission}/{action}", depth=2)
                   durations.append(time.perf_counter() - t0)
           return statistics.median(durations)

       doc_med = median_runs(_DOC_ACTIONS, "documentation")
       research_med = median_runs(_RESEARCH_ACTIONS, "research")
       assert doc_med <= 2 * research_med, (
           f"documentation median {doc_med:.6f}s exceeds 2× research median {research_med:.6f}s"
       )
   ```

2. Run: `uv run --python 3.13 --extra test python -m pytest tests/specify_cli/test_documentation_drg_nodes.py -v`.

**Files**: `tests/specify_cli/test_documentation_drg_nodes.py` (new, ~95 lines).

**Validation**:
- [ ] All 13 tests pass (6 + 6 + 1).
- [ ] No mocks of `load_validated_graph` or `resolve_context`.

## Definition of Done

- [ ] T017/T018 — graph.yaml contains 6 nodes and 22 edges; validated graph loads cleanly.
- [ ] T019 — test_documentation_drg_nodes.py passes 13 tests.
- [ ] `ruff check tests/specify_cli/test_documentation_drg_nodes.py` clean.
- [ ] `mypy --strict tests/specify_cli/test_documentation_drg_nodes.py` clean.

## Risks

1. DIRECTIVE_037 (Living Documentation Sync) may not exist in graph.yaml — verify with grep before authoring edges. If absent, the implementer must drop DIRECTIVE_037 references and update both the action bundles (WP03) and the edge list (T018) in lockstep. WP03 already lands first; if T012/T014/T015/T016's bundles reference 037, T018 must too.
2. NFR-007's "2× research median" is timing-based and could flake on a noisy CI runner. Mitigation: compute the median over 5 runs (already in the test), not the max. If the test is consistently borderline, the implementer can bump the multiplier to 3× with reviewer approval (this is an explicit deviation that must be called out in WP07's CHANGELOG entry).
3. The validated graph loader may reject the file if any node is duplicated. Mitigation: T017 inserts new nodes alphabetically; reviewer greps for duplicate URNs.

## Reviewer Guidance

- Verify graph.yaml diff shows exactly 6 new nodes and 22 new edges, all under `kind: action` / `relation: scope`.
- Verify no edits to existing research or software-dev nodes/edges (regression contract).
- Verify the bundle ↔ DRG consistency test parametrizes over all 6 actions.
- Verify the latency test reads both research and documentation timings for parity.

## Activity Log

- 2026-04-26T20:14:37Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=52671 – Started implementation via action command

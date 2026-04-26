# DRG Shape Contract — Documentation Action Nodes

This contract specifies what `src/doctrine/graph.yaml` MUST contain after the implementer applies WP04. It is a regression contract: the implementer renders the YAML, the test enforces the contract.

## Contract: nodes

For every `<action>` in `{discover, audit, design, generate, validate, publish}`:

```yaml
- urn: action:documentation/<action>
  kind: action
  label: <action>
```

The 6 nodes MUST exist. The `kind` MUST be exactly `action`. The `label` MUST be the bare action verb (no prefix, no underscore, no slash).

## Contract: edges

For every `<action>`, the edges declared in [data-model.md → Edges](../data-model.md#edges-add-to-srcdoctrinegraphyaml-edges-block) MUST exist. Each is a `{source, target, relation: scope}` triple.

Minimum-edge invariant: every documentation action MUST have at least 3 outgoing `relation: scope` edges (mirrors research's lowest-edge action `output`).

## Contract: action bundle ↔ DRG consistency

For every `<action>`:
- `src/doctrine/missions/documentation/actions/<action>/index.yaml` MUST exist.
- The directive slugs in `index.yaml` (e.g. `010-specification-fidelity-requirement`) MUST map 1-to-1 with the directive URN edges in `graph.yaml` for the same action (e.g. `directive:DIRECTIVE_010`).
- Same for tactics.

The mapping is by the URN's numeric / kebab suffix:
- `010-specification-fidelity-requirement` ⇔ `directive:DIRECTIVE_010`
- `003-decision-documentation-requirement` ⇔ `directive:DIRECTIVE_003`
- `037-living-documentation-sync` ⇔ `directive:DIRECTIVE_037`
- `001-architectural-integrity-standard` ⇔ `directive:DIRECTIVE_001`
- `requirements-validation-workflow` ⇔ `tactic:requirements-validation-workflow`
- `premortem-risk-identification` ⇔ `tactic:premortem-risk-identification`
- `adr-drafting-workflow` ⇔ `tactic:adr-drafting-workflow`

## Contract: load + resolve_context

After the nodes/edges are added:

```python
from charter._drg_helpers import load_validated_graph
from doctrine.drg.query import resolve_context

graph = load_validated_graph(repo_root)
for action in ("discover", "audit", "design", "generate", "validate", "publish"):
    node = graph.get_node(f"action:documentation/{action}")
    assert node is not None, f"missing DRG node: action:documentation/{action}"

    ctx = resolve_context(graph, f"action:documentation/{action}", depth=2)
    assert ctx.artifact_urns, f"empty artifact_urns for action:documentation/{action}"
```

The integration walk and `tests/specify_cli/test_documentation_drg_nodes.py` both run this assertion (the test is the formal gate; the walk smoke-tests it via the full runtime path).

## Verification

`tests/specify_cli/test_documentation_drg_nodes.py` MUST contain:

1. `test_each_documentation_action_has_drg_node_and_context` — the load + resolve_context assertions above.
2. `test_action_bundle_matches_drg_edges` — for every action, the URN-form edges in `graph.yaml` match the slug-form lists in `actions/<action>/index.yaml`.
3. `test_resolve_context_within_research_2x` — the median resolve_context latency for documentation actions over 5 runs is at most 2× the median for research actions over 5 runs (NFR-007).

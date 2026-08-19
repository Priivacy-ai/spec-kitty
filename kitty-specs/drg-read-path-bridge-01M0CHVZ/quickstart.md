# Quickstart: DRG Read-Path Bridge (red-first repro)

The executable acceptance contract (ATDD, C-011). This is the flip of
`tests/specify_cli/cli/commands/charter/test_org_cascade_chain.py::
TestGraphlessPackWithFragmentEdgeIsInvisibleToCascade` (FR-005).

## The scenario

An org pack declares `A requires B` **only** in `drg/fragment.yaml` — never in a
root-level `*.graph.yaml`.

```
org-packs/fragment-only-pack/
├── directives/
│   ├── a-directive.directive.yaml   # id: DIRECTIVE_A
│   └── b-directive.directive.yaml   # id: DIRECTIVE_B
└── drg/
    └── fragment.yaml                # nodes A,B; edge A --requires--> directive:DIRECTIVE_B
```

`.kittify/config.yaml` registers the pack and activates `software-dev`.

## Before the bridge (RED — current main)

```bash
spec-kitty charter activate --repo-root <proj> --cascade all directive a-directive
```

- `b-directive` is **not** cascade-activated (edge invisible to cascade).
- A graphless warning fires ("ships no root-level DRG graph").

## After the bridge (GREEN — this mission)

Same command:

- `a-directive` **and** `b-directive` are activated — the fragment `requires`
  edge is walked (SC-001: **0 silently-dropped org fragment edges**).
- `Cascade-activated` appears in output.
- **No** graphless warning fires — the pack ships a `drg/fragment.yaml`, so it is
  not graphless (SC-002).

## Companion checks (same change)

- `pack validate` on a `drg/fragment.yaml`-only pack emits **no**
  `drg_root_graph_missing` "will not be read" finding (SC-003).
- Root-graph cascade tests (`TestSingleOrgPackCascade`,
  `TestTwoPackChainCascade`, `TestGraphlessOrgPackDegradesGracefully`) stay green
  (no regression).
- `doctor doctrine` / `charter list` output unchanged; any cascade-reach delta is
  one reviewed golden update (SC-004 / NFR-001/002).

## Run

```bash
# The flipped integration test (red on base, green after the bridge):
PWHEADLESS=1 python -m pytest \
  tests/specify_cli/cli/commands/charter/test_org_cascade_chain.py -q -p no:cacheprovider

# Layer boundary + diagnostic invariance guards:
PWHEADLESS=1 python -m pytest tests/architectural/test_layer_rules.py \
  tests/architectural/test_runtime_charter_doctrine_boundary.py -q
```

# Contract — `extract_mission_type_edges`

**Location**: `src/doctrine/drg/migration/extractor.py` (sibling of `_discover_mission_type_nodes`).

## Interface

```python
def extract_mission_type_edges(doctrine_root: Path) -> list[DRGEdge]: ...
```

## Guarantees

1. For each `mission_types/<id>.yaml`, emits one `DRGEdge(source="mission_type:<id>",
   target="action:<id>/<step>", relation=Relation.REQUIRES)` per `step` in `action_sequence` — in sequence
   order (the module's deterministic sort re-orders the final list).
2. Emits **only** for existing action targets (every sequence step has an `actions/<step>/` dir today; a
   missing dir must surface as a validator dangling-target failure, not a silent skip).
3. Adds no duplicate edges (existing `_add_edge`/`_ensure` dedup).
4. Output concatenated into `all_edges` before `calibrate_surfaces` + sort.

## Consumers / gates

- `generate_graph` → regenerated `graph.yaml` (byte-identity freshness gate).
- `validator.assert_valid` (dangling / `requires`-cycle / duplicate) — passes.
- `test_shipped_graph_orphan_count_within_documented_residual` — 10 ≤ 14.
- `test_mission_type_nodes_have_no_incident_edges` — re-pinned to assert these edges.

## Test obligations

- `mission_type:plan` emits exactly 4 edges to its plan actions.
- A non-plan type (e.g. `documentation`) emits its full 7-edge sequence.
- No `mission_type:*` node remains orphan after regeneration; count = 10.

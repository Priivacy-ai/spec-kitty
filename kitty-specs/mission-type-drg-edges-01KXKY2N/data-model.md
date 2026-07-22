# Data Model — Mission-Type DRG Edges

No persistent data model change. The "model" is the new edge shape + the generator decision table.

## E-1 — The new edge

| Field | Value |
|-------|-------|
| `source` | `f"mission_type:{id}"` |
| `target` | `f"action:{id}/{step}"` for each `step` in `mission_types/{id}.yaml` `action_sequence` |
| `relation` | `Relation.REQUIRES` |

**Count**: 21 (software-dev 5, documentation 7, research 5, plan 4). All targets are existing `action:*` nodes.

## E-2 — Generator decision table

| Concern | Decision |
|---------|----------|
| Emit point | into `all_edges` @~`extractor.py:847`, before `calibrate_surfaces` @851 + deterministic sort @866-871 |
| `_KIND_MAP` `"mission_type"` entry | **add** (C-007) — safer against future partial-node states |
| `:778` "no `_KIND_MAP` until edges" caveat | **retire** (now obsolete) |
| `models.py:46` "nodes only, no edges yet" | **correct** (FR-005) |
| Regeneration | `spec-kitty doctrine regenerate-graph`; commit `graph.yaml` same WP (byte-identity) |
| `"missions"` literal (3×) | hoist to a helper/const (Sonar S1192) |

## E-3 — Test transitions

| Test | Before | After |
|------|--------|-------|
| `test_mission_type_nodes_have_no_incident_edges` | asserts no edges | **re-pinned** to assert the `requires` edges (+ docstrings) |
| `test_shipped_graph_orphan_count_within_documented_residual` | RED (18 > 14) | GREEN (10 ≤ 14); ceiling unchanged |
| `assert_valid` / freshness twins | green | green (no dangling/cycle/dup; byte-identical) |
| new focused tests | — | `mission_type:plan` = 4 edges; a non-plan type = its full sequence; no mission_type orphan |

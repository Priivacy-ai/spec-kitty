# Contract: `load_validated_graph` org-fragment bridge

**Module**: `src/charter/_drg_helpers.py`

## Signature

```python
def load_validated_graph(
    repo_root: Path,
    org_root: Path | None = None,
    *,
    org_roots: list[Path] | None = None,
    org_fragments: list[OrgDRGFragment] | None = None,   # NEW (FR-001)
) -> DRGGraph: ...
```

- `org_fragments` type is imported without crossing the layer boundary
  (`OrgDRGFragment` is re-exported by `charter.drg`; `_drg_helpers` may import
  from `doctrine.drg.org_pack_loader` / `charter.drg` — never from `specify_cli`).

## Behaviour

| Input | Behaviour | Requirement |
|-------|-----------|-------------|
| `org_fragments` omitted / `None` / `[]` | Byte-identical to today: built-in + root-graph roots + project via `merge_layers`, then `assert_valid`. | FR-003 (build-time inert) |
| `org_fragments` non-empty | Fold via `merge_three_layers(built_in=<built-in+root-graph>, org_fragments=…, project=…)`; then `assert_valid`. Fragment `requires`/`suggests` edges appear in `result.edges`. | FR-001, FR-002 |
| a root with pack-root `*.graph.yaml` | Folded via `merge_layers` (unchanged). | — |
| a root with `drg/fragment.yaml` but no root graph | No graphless warning; its fragment folded via `merge_three_layers`. | FR-004 |
| a root with **neither** root graph **nor** `drg/fragment.yaml` | Graphless warning fires (D-005 degrade preserved). | FR-004, C-003 |
| duplicate edge across root `*.graph.yaml` + `drg/fragment.yaml` | De-duplicated by `_OrgEdgeCollector` (one edge). | Edge Case 1 |
| unresolvable fragment endpoint | Surfaced by existing `_resolve_edge_endpoint` / `_dangling_org_endpoints`, not silently dropped. | Edge Case 2 |

## Non-goals

- Does **not** change `merge_three_layers`, `_resolve_edge_endpoint`, or
  `_OrgEdgeCollector` (C-002 — reuse only).
- Does **not** read `drg/*.graph.yaml` (still an unread shape — see validator
  contract).
- Does **not** widen the followed relation set (C-004 — M5/#2829 scope).

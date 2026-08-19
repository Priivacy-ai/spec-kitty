# Data Model: DRG Read-Path Bridge

This mission changes a **read path**, not a stored schema. There is no new
persistent entity, no migration, and no serialized-format change. The "data
model" here is the in-memory graph-merge data flow and the pack read-set that the
bridge must keep coherent.

## Entities (existing — reused, not introduced)

| Entity | Owner module | Role in this mission |
|--------|--------------|----------------------|
| `OrgDRGFragment` | `doctrine.drg.org_pack_loader` (re-exported by `charter.drg`) | The `drg/fragment.yaml` unit: pack `nodes` + `requires`/`suggests` edges. New `org_fragments` param carries a list of these. |
| `DRGGraph` | `doctrine.drg.models` | The merged, validated graph charter cascade walks (`.nodes`, `.edges`). Bridge output. |
| `DRGEdge` | `doctrine.drg.models` | Carries `source`, `target`, `relation` (`requires`/`suggests`/…). Fragment edges become `DRGEdge`s in the merged graph. |
| `_OrgEdgeCollector` | `doctrine.drg.merge` | **Reused** cross-fragment edge identity + dedup. Not modified. |
| `ValidationIssue` | `specify_cli.doctrine.pack_validator` | The `drg_root_graph_missing` finding record; re-scoped + re-messaged. |

## Pack read-set (the coherence contract)

For each configured org pack, what each surface reads **after** this mission:

| Pack contents | Runtime cascade reads it? | Validator finding? (post-bridge) | Graphless warning? (post-bridge) |
|---------------|---------------------------|----------------------------------|----------------------------------|
| pack-root `*.graph.yaml` | ✅ via `merge_layers` (unchanged) | no | no |
| `drg/fragment.yaml` | ✅ **NEW** via `merge_three_layers` | no | no |
| `drg/*.graph.yaml` only (no root graph, no fragment) | ❌ (no runtime path reads this shape) | ✅ still flagged (genuinely unread) | — (has drg graph content) |
| neither root graph nor `drg/fragment.yaml` | ❌ (nothing to read) | no | ✅ warned (D-005 degrade preserved) |

The two independent "is this pack's DRG read?" signals — the runtime graphless
warning (D2) and the validator finding (D5) — now key off the **same** predicate
("neither a root graph nor a `drg/fragment.yaml`"), so they can never contradict
the runtime (SC-002 / SC-003).

## Merge data flow (after the bridge)

```
load_built_in_graph()                    ── built-in DRGGraph
   │
   ├─ for each org root with pack-root *.graph.yaml:
   │     merge_layers(base, load_graph_or_dir(root))          [existing]
   │        → root_merged  (built-in + root-graph org layer)
   │
   ├─ org_fragments (list[OrgDRGFragment], strict=False load)  [NEW input]
   │
   └─ if org_fragments:
          merge_three_layers(built_in=root_merged,
                             org_fragments=org_fragments,       ── REUSED machinery:
                             project=project)                      _resolve_edge_endpoint,
      else:                                                        _OrgEdgeCollector (dedup),
          merge_layers(root_merged, project)   [today's path]     provenance tagging
              │
              ▼
        assert_valid(merged)  ── dangling / duplicate / requires-cycle guard (unchanged)
              │
              ▼
        DRGGraph  ── cascade walks .edges by relation; fragment requires/suggests now present
```

## Invariants preserved

- **Endpoint resolution & dedup are single-authority** — only `merge_three_layers`
  canonicalises fragment edges; the bridge never re-implements it (C-002).
- **Dedup across shapes** — a pack declaring the *same* edge in both a root
  `*.graph.yaml` and `drg/fragment.yaml` collapses to one edge via
  `_OrgEdgeCollector` identity (spec Edge Case 1), no double-activation.
- **Unresolvable endpoints are not silently dropped** — `_resolve_edge_endpoint`
  / `_dangling_org_endpoints` surface them exactly as they do on the diagnostic
  path (spec Edge Case 2).
- **Malformed `drg/fragment.yaml` fails loud** — `load_org_pack` parse/schema
  errors are unchanged; `strict=False` only skips a *missing* fragment, never a
  *malformed* one (spec Edge Case 3).
- **Diagnostic path unchanged** — no diagnostic caller of `merge_three_layers` is
  touched; their `strict=True` `load_org_drg` default is untouched (NFR-001).

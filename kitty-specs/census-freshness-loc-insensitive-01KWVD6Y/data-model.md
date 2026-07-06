# Data Model: CI-topology census

No new runtime entities. This mission reshapes the committed census artifact and the
derivation that produces it. No API contracts (`contracts/` intentionally absent — the
gate has no request/response surface).

## Entity: census worklist entry

The unit iterated by the SC-001 routing invariants and compared by the freshness gate.

### Before (LOC-sensitive)

```json
{ "dir": "bulk_edit", "loc": 1276, "cone_roots": ["tests/specify_cli/bulk_edit"],
  "target_group": "agent_surface", "target_shard": "specify-cli-rest" }
```

- `loc` — exact recursive `*.py` newline count; **freshness-compared for equality** →
  the tax. List is sorted by `(-loc, dir)`, so ordering is also LOC-derived.

### After (LOC-insensitive)

```json
{ "dir": "bulk_edit", "cone_roots": ["tests/specify_cli/bulk_edit"],
  "target_group": "agent_surface", "target_shard": "specify-cli-rest" }
```

- `loc` **removed** from the emitted/committed entry (C-001). Entries sorted by `dir`
  (LOC-independent, diff-stable).
- `loc` is still computed **internally** by `live_derived_worklist` to decide membership
  (`loc >= t_loc`) — it is just not emitted.

## Derived fields & their freshness rule (after)

| Field | Source authority | Freshness comparison |
|-------|------------------|----------------------|
| `worklist` | live tree ≥ `t_loc` minus frozen `_PRE_MISSION_MAPPED_SRC_DIRS`, annotated by `_COMPOSITE_ROUTING` | dir-keyed routing index (order/LOC-insensitive) |
| `mapped_dirs` | parsed dorny filter groups (src-backed, ≠ `any_src`) | set equality (unchanged; already LOC-free) |
| `arch_blind_groups` | differential arch matrix (empty today) | unchanged this mission (Out of Scope) |
| `t_loc` | committed constant (500) | read as the live floor |

## Invariants

- **Membership floor**: `dir ∈ worklist ⇔ live_loc(dir) ≥ t_loc ∧ dir ∉ frozen_mapped`.
  (Floor-crossing changes membership → gate reds.)
- **Routing plan** per member is exactly its `_COMPOSITE_ROUTING` row (hand-edit → reds).
- **Order independence**: freshness verdict is invariant under any permutation of
  worklist entries (rank-swap stays green).
- **Live floor**: each committed worklist dir satisfies `live_loc(dir) ≥ t_loc`
  (checked against the tree, not a stored snapshot).

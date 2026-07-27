# Data Model: Merge Done-Marking Surface Resolver

---

## Core Entity: StatusSurface

The status surface is the canonical location of `status.events.jsonl` for a mission at a given point in time. It is not a stored entity — it is a resolved value computed from mission metadata.

| Attribute | Type | Description |
|-----------|------|-------------|
| `events_path` | `Path` | Absolute path to `status.events.jsonl` on the canonical surface |
| `topology` | `"coordination"` \| `"primary"` | Which surface was selected |

**Resolution logic:**

```
if meta.json has coordination_branch:
    events_path = .worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>/status.events.jsonl
    topology = "coordination"
else:
    events_path = <repo_root>/kitty-specs/<slug>/status.events.jsonl
    topology = "primary"
```

**Invariant**: For a given `(repo_root, mission_slug)` at a given moment, there is exactly one canonical surface. The resolver is deterministic and stateless.

---

## Entities Consumed by the Resolver

### MissionMeta (read-only)

The resolver reads one field from `meta.json`:

| Field | Type | Used for |
|-------|------|----------|
| `coordination_branch` | `str \| None` | Determines topology selection |
| `slug` | `str` | Derives worktree path segment |
| `mid8` | `str` | Derives worktree path segment (first 8 chars of `mission_id`) |

The resolver does NOT write to `meta.json`.

### CoordinationWorktree (location only)

When `coordination_branch` is present, the resolver derives the coordination worktree path using the same convention as `CoordinationWorkspace.resolve`:

```
<repo_root>/.worktrees/<slug>-<mid8>-coord/
```

The resolver does not create, modify, or tear down the worktree. It only derives the path.

---

## State Transitions Affected

The done-marking loop drives two transitions per WP:

| Transition | From | To | Write surface (after fix) | Read surface (after fix) |
|------------|------|----|--------------------------|--------------------------|
| Mark done | `approved` | `done` | Resolved by `resolve_status_surface` | Resolved by `resolve_status_surface` |

**Before fix**: write → coordination branch; read → primary checkout. **After fix**: both → same resolved surface.

---

## Module Dependency Graph (relevant slice)

```
merge.py
  └── coordination/surface_resolver.py   (NEW import)
       └── coordination/status_transition.py  (existing, for topology logic)
       └── status/store.py or Path resolution only (no circular dependency)

merge.py
  └── status/lane_reader.py   (existing — get_wp_lane, used by _assert_merged_wps_reached_done)
       └── status/store.py

coordination/surface_resolver.py
  └── (reads meta.json via existing meta-reader utility)
  └── (does NOT import from merge.py — no circular dependency)
```

**Circular import check**: `coordination/ → status/` is an existing valid edge. `surface_resolver.py` reads `meta.json` directly (as other coordination modules do) and resolves a `Path`. It does not import from `merge.py` or from `status/lane_reader.py`. No new circular dependencies.

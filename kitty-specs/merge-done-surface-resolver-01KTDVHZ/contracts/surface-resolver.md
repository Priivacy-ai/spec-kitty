# Contract: resolve_status_surface

**Module**: `src/specify_cli/coordination/surface_resolver.py`
**Function**: `resolve_status_surface`

---

## Signature

```python
def resolve_status_surface(
    repo_root: Path,
    mission_slug: str,
) -> Path:
    """
    Return the canonical path to status.events.jsonl for the given mission.

    Reads coordination_branch from the mission's meta.json. If set, returns
    the events file path inside the coordination worktree. If absent, returns
    the primary-checkout path.

    Does not create, modify, or tear down any worktree or branch.
    """
```

---

## Inputs

| Parameter | Type | Description |
|-----------|------|-------------|
| `repo_root` | `Path` | Absolute path to the repository root checkout |
| `mission_slug` | `str` | The mission's human-readable slug (e.g., `my-mission-01ABCDEF`) |

---

## Return Value

`Path` — absolute path to `status.events.jsonl` on the canonical surface for this mission.

- If `coordination_branch` is set in `meta.json`: path is inside the coordination worktree (`.worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>/status.events.jsonl`)
- If `coordination_branch` is absent: path is in the primary checkout (`<repo_root>/kitty-specs/<slug>/status.events.jsonl`)

The returned path may or may not exist on disk at call time. Callers are responsible for checking existence if required.

---

## Errors

| Condition | Exception |
|-----------|-----------|
| `meta.json` is missing for the given `mission_slug` | `MissionMetaNotFoundError` (or equivalent existing exception) |
| `meta.json` is malformed (unparseable) | `MissionMetaParseError` (or equivalent existing exception) |

The resolver does NOT raise an error if the coordination worktree does not exist on disk. Existence checking is the caller's responsibility.

---

## Invariants

- **Deterministic**: Same `(repo_root, mission_slug)` always returns the same path for the same `meta.json` state.
- **Stateless**: Does not modify any filesystem state or git state.
- **Single source of truth**: This function is the only place in the merge path where the topology decision is made. It must not be duplicated.
- **Backward-compatible**: When `coordination_branch` is absent, returns the same path that `resolve_feature_dir_for_mission` + `/ "status.events.jsonl"` would return (no behavioral change for legacy missions).

---

## Callers (post-fix)

| Caller | Call site | Purpose |
|--------|-----------|---------|
| `_mark_wp_merged_done` | `merge.py:~223` | Determine where to write the done event |
| `_assert_merged_wps_reached_done` | `merge.py:~348` | Determine where to read back for assertion |

Both callers must use this function and must not derive the surface independently.

---

## Non-Callers (must NOT be changed to call this)

| Non-caller | Reason |
|------------|--------|
| `status/lane_reader.py` | Already fixed in #1589; has its own coordination-aware logic |
| `status/store.py` | Low-level I/O; must not know about topology |
| `coordination/status_transition.py` | Has its own `_identity_for_request` topology resolution for the transactional emit path |

---

## Type Annotations (mypy --strict)

All parameters and return value must be fully annotated. No `Any`. No `Optional` unless explicitly required by a failure mode. The function body must pass `mypy --strict` with no suppressions.

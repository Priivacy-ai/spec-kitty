# Quickstart: Merge Done-Marking Surface Resolver

This guide is for the developer implementing WP02 and WP03.

---

## What you're building

A single function `resolve_status_surface(repo_root, mission_slug) -> Path` in `src/specify_cli/coordination/surface_resolver.py` that replaces the implicit, divergent surface derivation currently happening independently in two callers inside `merge.py`.

---

## Key files

| File | Role |
|------|------|
| `src/specify_cli/cli/commands/merge.py` | Two callers to update: `_mark_wp_merged_done` (line ~223) and `_assert_merged_wps_reached_done` (line ~348) |
| `src/specify_cli/coordination/status_transition.py` | Reference — shows how topology is currently read from `meta.json` (~lines 318/334) |
| `src/specify_cli/coordination/transaction.py` | Reference — shows how the coordination worktree path is derived (~lines 598, 754, 765) |
| `src/specify_cli/status/lane_reader.py` | Reference — `get_wp_lane` is NOT changed; it reads from whatever path it receives |
| `tests/specify_cli/cli/commands/test_merge.py` | Add coord-branch fixtures in T015 section |
| `tests/merge/test_merge_done_recording.py` | Add coord-branch fixture |

---

## Implementation sketch

```python
# src/specify_cli/coordination/surface_resolver.py

from pathlib import Path
from specify_cli.missions.meta import load_meta  # or equivalent meta reader

KITTY_SPECS_DIR = "kitty-specs"
STATUS_EVENTS_FILENAME = "status.events.jsonl"
COORD_WORKTREE_SUFFIX = "-coord"

def resolve_status_surface(repo_root: Path, mission_slug: str) -> Path:
    meta = load_meta(repo_root / KITTY_SPECS_DIR / mission_slug)
    coord_branch = meta.get("coordination_branch")
    if coord_branch:
        mid8 = meta["mission_id"][:8]
        worktree_root = repo_root / ".worktrees" / f"{mission_slug}-{mid8}{COORD_WORKTREE_SUFFIX}"
        return worktree_root / KITTY_SPECS_DIR / mission_slug / STATUS_EVENTS_FILENAME
    return repo_root / KITTY_SPECS_DIR / mission_slug / STATUS_EVENTS_FILENAME
```

Verify against `coordination/transaction.py` lines ~754–765 to confirm the worktree path convention matches exactly.

---

## Wiring into merge.py

In `_mark_wp_merged_done` (~line 223), the surface is currently derived as `feature_dir / status.events.jsonl` implicitly via `emit_status_transition_transactional`. After the fix, the function should resolve the surface explicitly and pass it to the relevant status write call — OR the write call should accept the resolved surface.

In `_assert_merged_wps_reached_done` (~line 348), replace the implicit `feature_dir` argument to `get_wp_lane` with a path derived from `resolve_status_surface`. Specifically, pass `resolve_status_surface(repo_root, mission_slug).parent` as `feature_dir` (since `get_wp_lane` expects the directory, not the file path) — or check whether `get_wp_lane` can accept a full file path.

Check both callers for how they obtain `repo_root` and `mission_slug` to ensure the resolver receives consistent values.

---

## Test fixture shape (for WP04)

```python
# Fixture: mission with coordination_branch set
meta = {
    "mission_id": "01KTDVHZKGCHCW6HQ4V577PNES",
    "mission_slug": "my-test-mission",
    "coordination_branch": "kitty/coord/my-test-mission-01KTDVHZ",
    ...
}
# Set up coordination worktree at .worktrees/my-test-mission-01KTDVHZ-coord/
# Do NOT mock _mark_wp_merged_done or _assert_merged_wps_reached_done
# Assert get_wp_lane returns Lane.DONE after _mark_wp_merged_done runs
```

---

## Validation checklist before opening PR

- [ ] `uv run mypy --strict src/specify_cli/coordination/surface_resolver.py` passes
- [ ] `uv run pytest tests/specify_cli/cli/commands/test_merge.py -x` passes
- [ ] `uv run pytest tests/merge/test_merge_done_recording.py -x` passes
- [ ] `uv run pytest tests/ -x` (full suite) passes with no regressions
- [ ] `uv run ruff check src/specify_cli/coordination/surface_resolver.py` passes
- [ ] `CHANGELOG.md` entry added under the appropriate version heading
- [ ] `kitty-specs/merge-done-surface-resolver-01KTDVHZ/audit/merge-path-status-sites.md` committed

# Developer Quickstart: Merge Preflight Remote-State Boundary Separation

## Running the affected test suite

```bash
# Run the merge preflight tests directly
pytest tests/merge/test_target_branch_preflight.py -v

# Run all merge tests
pytest tests/merge/ -v

# Verify type checking
mypy src/specify_cli/merge/ --strict

# Full quality check
ruff check src/specify_cli/merge/
```

## Reproducing issue #1706 manually

```bash
# Create a diverged state (local ahead + behind)
git checkout main
git commit --allow-empty -m "local planning commit 1"
git commit --allow-empty -m "local planning commit 2"
# (do NOT push these)

# Try merge — currently blocked, should pass after fix
spec-kitty merge <some-mission-slug>
```

## Testing the push path

```bash
# With push requested — should still check origin sync
spec-kitty merge <mission-slug> --push

# The push check fires AFTER local merge completes
# With "diverged" state, it should block with guidance
# With "ahead" or "in_sync", it should proceed to push
```

## Key files

| File | Role |
|------|------|
| `src/specify_cli/merge/preflight.py` | Domain-only local-graph checks (no network after this mission) |
| `src/specify_cli/merge/push_preflight.py` | NEW: publish-layer remote-state fetch + push-safety check |
| `src/specify_cli/merge/state.py` | `MergeState` with new `push_requested` field |
| `src/specify_cli/cli/commands/merge.py` | Call site: `if push: check_push_safety(...)` |
| `tests/merge/test_target_branch_preflight.py` | Updated and new preflight tests |
| `architecture/3.x/adr/2026-06-05-1-merge-publish-layer-boundary.md` | Decision record |

## Verifying backwards compatibility

```bash
# Create a state.json without push_requested and verify load
python3 -c "
import json
from pathlib import Path
from specify_cli.merge.state import MergeState
old_state = {
    'mission_id': 'test', 'mission_slug': 'test', 'target_branch': 'main',
    'wp_order': ['WP01'], 'completed_wps': [], 'strategy': 'merge',
    'started_at': '2026-01-01T00:00:00+00:00', 'updated_at': '2026-01-01T00:00:00+00:00',
    'mission_number_baked': False
}
s = MergeState.from_dict(old_state)
assert s.push_requested == False, 'Backwards compat broken'
print('OK: legacy state loads with push_requested=False default')
"
```

# Quickstart: Stale Workspace Reproduction

## Planning-base witness

```bash
PWHEADLESS=1 uv run --extra test pytest tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py -q --tb=short
```

Record separately the recoverable matching-branch result, branch-plus-worktree-absent result, divergent-context result, and per-entry-point six-surface deltas.

## Conditional implementation verification

```bash
PWHEADLESS=1 uv run --extra test pytest tests/specify_cli/cli/commands/agent/ tests/integration/test_lane_lifecycle_sync.py -n auto --dist loadfile -p no:cacheprovider
uv run ruff check <touched-files>
uv run mypy --strict <touched-source-files>
PWHEADLESS=1 uv run --extra test pytest tests/architectural/test_no_legacy_terminology.py -q
```

The acceptance test contains no production monkeypatching. Full gates run at Mission closeout.

# Quickstart: Fix Merge Target Branch Resolution

## Problem

`spec-kitty merge --feature <slug>` ignores `meta.json` `target_branch` and defaults to repo primary branch. Features targeting `2.x` get merged into `main`.

## Fix Summary

3 changes:

1. **merge.py lines 721-724**: When `--feature` is provided and `--target` is not, call `get_feature_target_branch(repo_root, feature)` instead of `resolve_primary_branch(repo_root)`.

2. **merge.md template**: Align frontmatter and body to the single canonical API `spec-kitty merge --feature <slug>`. Remove all references to `spec-kitty agent feature merge` from templates.

3. **Regression tests**: 7 test cases covering 2.x target, main target, missing meta.json, explicit override, nonexistent branch error, no-feature backward compat, malformed meta.json.

## Verification

```bash
# After fix, this should show target_branch: "2.x" for a 2.x-targeting feature:
spec-kitty merge --feature 049-fix-merge-target-resolution --dry-run --json | python -m json.tool | grep target_branch

# Run regression tests:
python -m pytest tests/specify_cli/cli/commands/test_merge_target_resolution.py -v
```

## Key Files

| File | Change |
|------|--------|
| `src/specify_cli/cli/commands/merge.py` | Fix target resolution (lines 721-724) |
| `src/specify_cli/missions/software-dev/command-templates/merge.md` | Align template to canonical `spec-kitty merge` path |
| `tests/specify_cli/cli/commands/test_merge_target_resolution.py` | New regression tests |
| `src/specify_cli/core/feature_detection.py` | Unchanged (reused) |

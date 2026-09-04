# Quickstart: Merge Retention Policy (#3131)

## Declare retention at mission creation

```bash
spec-kitty agent mission create "my-mission" \
  --mission-type software-dev --friendly-name "My Mission" \
  --retain-branches --retain-worktrees
# → meta.json now carries retain_branches: true, retain_worktrees: true
```

## Merge honors it (the fix)

```bash
# No cleanup flags: retention wins, branches + worktrees survive, warning shown.
spec-kitty merge --mission my-mission
#   ⚠ Retention: retain_branches/retain_worktrees set in meta.json —
#     keeping lane branches, mission branch, and worktrees. (source: meta)

# Preview the resolved decision (not just flag echo):
spec-kitty merge --mission my-mission --dry-run --json
#   { ... "delete_branch": false, "remove_worktree": false,
#         "retention": {"branch_source": "meta", "worktree_source": "meta"} ... }

# Explicit override still deletes — but on the record, never silently:
spec-kitty merge --mission my-mission --delete-branch --remove-worktree
#   ⚠ Override: --delete-branch/--remove-worktree overrides this mission's
#     retention policy; deleting anyway. (recorded)
```

## Non-retaining missions: unchanged

```bash
# meta.json has no retention fields → default cleanup exactly as before.
spec-kitty merge --mission other-mission   # deletes branches + worktrees (default)
```

## Verify the fix (red-first regression)

```bash
# RED on current main, GREEN after the fix:
PWHEADLESS=1 pytest tests/integration/test_merge_lane_planning_data_loss.py -k retention -q
# Merge tests shell out to spec-kitty — reinstall editable first to avoid stale-install false reds:
pip install -e . && PWHEADLESS=1 pytest tests/merge/ -q
```

## Invariants to remember

- Ambiguity fails closed toward retention (corrupt meta aborts; malformed value retains).
- Coordination branch/worktree/marker are torn down or retained as one unit.
- `merge --abort` also honors worktree retention.
- The internal merge scratch worktree is always cleaned (not a retained resource).
- `retain_branches` ⇔ effective `--keep-branch`; `retain_worktrees` ⇔ effective `--keep-worktree`.

# Quickstart: Worktree-Clean Sync Invariant

How to reproduce the bug, and how to verify the fix once implemented.

## Reproduce (current behavior)

```bash
# In a SaaS-sync-enabled checkout whose .kittify/config.yaml has an incomplete
# identity (e.g. missing build_id) OR a tracker with a pending binding_ref:
git status --short                 # clean
spec-kitty sync status --check     # read-like command
git status --short                 # .kittify/config.yaml now shows as modified  <-- the bug
spec-kitty agent mission record-analysis ...   # refuses: DIRTY_WORKTREE
```

## Verify the fix

```bash
git status --porcelain > /tmp/before.snap
# Run the full covered surface:
spec-kitty sync status --check
spec-kitty sync pull
spec-kitty sync push
spec-kitty sync run
spec-kitty tracker status
spec-kitty tracker map list
# (status-event emission + dashboard daemon tick are exercised by the test suite)
git status --porcelain > /tmp/after.snap
diff /tmp/before.snap /tmp/after.snap && echo "INV-1 holds: tree unchanged"
```

Identity stability (NFR-001) — emit twice, identity must be identical:

```bash
# Pseudocode of the test assertion:
id1 = resolve_identity(repo_root)
id2 = resolve_identity(repo_root)
assert (id1.project_uuid, id1.build_id) == (id2.project_uuid, id2.build_id)
```

Guard still works (FR-007):

```bash
echo "x" >> src/specify_cli/__init__.py     # real source dirt
spec-kitty agent mission record-analysis ... # MUST still refuse: DIRTY_WORKTREE
git checkout -- src/specify_cli/__init__.py
```

## Run the contract test

```bash
PWHEADLESS=1 pytest tests/specify_cli/sync/test_worktree_clean_invariant.py -q
# daemon/real-port variants serially:
PWHEADLESS=1 pytest tests/specify_cli/sync/test_worktree_clean_invariant.py -n0 -q
```

## Done-when

- Every covered command leaves `git status --porcelain` byte-identical on a clean checkout.
- `resolve_identity` is stable across invocations; no `config.yaml` write on read paths.
- `record-analysis` still catches real dirt; the allowlist did not grow.
- `mypy --strict`, `ruff`, and ≥90% new-line coverage pass.

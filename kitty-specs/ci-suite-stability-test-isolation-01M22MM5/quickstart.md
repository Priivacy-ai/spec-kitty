# Quickstart — reproduce & verify

## #4017 (run real e2e — DRIVE, don't assert from API)
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=0; export PWHEADLESS=1
# RED-first (current main, before fix): the quarantined concurrency e2e reproduces the signal
.venv/bin/python -m pytest tests/e2e/test_worktree_owned_root_concurrency.py::test_installed_cli_keeps_two_owned_worktrees_isolated -p no:cacheprovider
#  (quarantined @skip today; the deterministic apply-interleave unit test is the structural red-first)
# After fix — DRIVE both un-skipped e2e tests for real + the deterministic interleave:
.venv/bin/python -m pytest tests/e2e/test_worktree_owned_root_concurrency.py tests/runtime/ -p no:cacheprovider
# Warm-path: assert exactly one assess, no lock. Source-drift guard: genuine source change still caught.
# #4082 regression: upgrade dry-run disclosure byte-unchanged.
```

## #4015
```bash
# Guard stays green; vocab unchanged:
.venv/bin/python -m pytest tests/architectural/test_performance_marker_guard.py -q -p no:cacheprovider
# Relocated budgets run nightly:
SPEC_KITTY_RUN_PERFORMANCE=1 .venv/bin/python -m pytest -m performance <relocated tests> -q
# Functional asserts still per-PR (coverage-mapping table is the diffable proof).
```

## Expected
- #4017: two concurrent cold-home invocations both exit 0; 0 "Global asset input changed" / 0 "global_asset_write_failed"; both quarantined tests un-skipped + green; warm path unchanged.
- #4015: guard green; 74 split (functional per-PR, timing nightly); 9 remediated; deletions signed-off; coverage-mapping shows no loss.

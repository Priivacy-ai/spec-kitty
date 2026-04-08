---
affected_files: []
cycle_number: 2
mission_slug: 075-mission-build-identity-contract-cutover
reproduction_command:
reviewed_at: '2026-04-08T05:54:11Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP03
---

# WP03 Review — Cycle 1 — REJECTED

**Reviewer**: Claude Sonnet 4.6 (reviewer agent)
**Date**: 2026-04-07

---

## BLOCKER: Out-of-scope re-creation of `identity_aliases.py`

`git diff kitty/mission-075-mission-build-identity-contract-cutover..HEAD --name-only` shows:

```
src/specify_cli/core/identity_aliases.py
```

This file was **deleted by WP02** (commit `0f37df1e feat(WP02): remove feature_slug from domain models; delete identity_aliases module`) and **must remain deleted**. The WP03 commit message acknowledges this explicitly: "Add identity_aliases.py stub to unblock import chain (pre-existing worktree breakage from WP02 lane)."

This is a rejection on three grounds:

1. **Out-of-scope file**: WP03 owns only `src/specify_cli/sync/project_identity.py` and `tests/specify_cli/sync/test_project_identity.py`. Adding `src/specify_cli/core/identity_aliases.py` is outside WP03's ownership boundary.
2. **Reversal of approved work**: WP02 is approved. Re-adding a file that WP02 deleted undoes approved work.
3. **Wrong fix**: The cross-lane test collection failure caused by `identity_aliases.py` being absent is an expected consequence of the lane architecture. It is documented in the WP02/WP03 specs as such. It must NOT be papered over with a compatibility stub.

---

## Required Fix

Delete the stub and do not recreate it:

```bash
git rm src/specify_cli/core/identity_aliases.py
git commit -m "fix(WP03): remove out-of-scope identity_aliases.py stub"
```

Do NOT add any import compatibility shim, re-export, or stub for `identity_aliases`. If the cross-lane import causes pytest collection errors during WP03 test runs, that is expected behavior — run tests scoped to the owned test file instead:

```bash
pytest tests/specify_cli/sync/test_project_identity.py -v
```

---

## Also Note: Additional Out-of-Scope Files

The following files appear in the diff but are not owned by WP03:

- `src/specify_cli/core/worktree.py`
- `src/specify_cli/status/progress.py`
- `src/specify_cli/status/wp_metadata.py`
- `tests/specify_cli/core/test_identity_aliases.py`
- `tests/specify_cli/core/test_worktree.py`
- `tests/specify_cli/status/test_wp_metadata.py`

These appear to be from prior WP02 commits in the shared lane-b worktree and are not new WP03 additions. Confirm by checking `git show HEAD --name-status` — if these are not in the WP03 commit, they are not WP03's responsibility to clean up.

However, `src/specify_cli/core/identity_aliases.py` **is** in the WP03 commit (confirmed via `git show HEAD --name-status`) and must be removed.

---

## Implementation Quality (conditional on scope fix)

The WP03-owned code in `src/specify_cli/sync/project_identity.py` and `tests/specify_cli/sync/test_project_identity.py` was not reviewed in depth because the scope blocker requires rejection first. Once the stub is removed and the commit is clean, resubmit for full acceptance criteria review.

---
affected_files: []
cycle_number: 4
mission_slug: private-teamspace-ingress-safeguards-01KQH03Y
reproduction_command:
reviewed_at: '2026-05-01T09:50:17Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

**Issue 1**: Full `tests/auth/` regression: the post-refresh hook can make unmocked real `/api/v1/me` calls from pre-existing refresh tests.

`TokenManager.refresh_if_needed()` now calls `_apply_post_refresh_membership_hook()` after each adoption branch, and that calls `rehydrate_membership_if_needed(force=True)` when the adopted session lacks a Private Teamspace. WP02 updated `tests/auth/test_token_manager.py` fixtures to use `is_private_teamspace=True`, but other pre-existing refresh fixtures still construct shared-only teams, for example `tests/auth/concurrency/test_machine_refresh_lock.py:56`.

Repro attempted:

```bash
uv run pytest tests/auth -q
```

The suite progressed into `tests/auth/concurrency/test_machine_refresh_lock.py` and then stalled for minutes because those refresh tests now enter the sync `fetch_me_payload()` path with fake tokens and no `/api/v1/me` mock. This violates the WP Definition of Done item that all pre-existing `tests/auth/` tests pass and also violates the no-real-network expectation for unit/concurrency tests.

How to fix:

- Audit every pre-existing auth test that calls `TokenManager.refresh_if_needed()` or exercises the refresh path with `Team(...)` fixtures lacking `is_private_teamspace=True`.
- For tests that are not intended to exercise membership rehydrate, make their stored/refreshed sessions include a Private Teamspace so the hook short-circuits. At minimum, update `tests/auth/concurrency/test_machine_refresh_lock.py::_make_expired_session()`.
- For tests that intentionally cover the hook, mock `/api/v1/me` with `respx` or monkeypatch `rehydrate_membership_if_needed()` explicitly.
- Re-run `uv run pytest tests/auth -q` and ensure it completes without live network calls.

Downstream note: WP03, WP04, and WP05 depend on WP02, so they should rebase after this is corrected.

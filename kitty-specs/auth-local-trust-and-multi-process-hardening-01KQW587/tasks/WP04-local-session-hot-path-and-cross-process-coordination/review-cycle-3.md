**Issue 1**: Broader auth concurrency verification still performs hosted membership I/O and does not pass.

The required broader auth concurrency command does not complete cleanly after the WP04 `token_manager.py` changes. It hangs in `tests/auth/concurrency/test_single_flight_refresh.py`, and a focused timeout run shows the test is making a real hosted `/api/v1/me` request through `TokenManager._apply_post_refresh_membership_hook()`:

```text
FAILED tests/auth/concurrency/test_single_flight_refresh.py::test_fifty_concurrent_callers_single_flight - Failed: Timeout (>15.0s) from pytest-timeout.
...
src/specify_cli/auth/token_manager.py:423: in refresh_if_needed
    self._apply_post_refresh_membership_hook(result.session)
src/specify_cli/auth/token_manager.py:353: in _apply_post_refresh_membership_hook
    self.rehydrate_membership_if_needed(force=True)
src/specify_cli/auth/token_manager.py:306: in rehydrate_membership_if_needed
    payload = fetch_me_payload(
src/specify_cli/auth/http/me_fetch.py:29: in fetch_me_payload
    response = request_with_fallback_sync(
...
E   Failed: Timeout (>15.0s) from pytest-timeout.
```

This violates the WP04 verification requirement to run broader auth concurrency tests after `token_manager.py` behavior changes, and it violates the data-model invariant that default concurrency tests perform zero real hosted `/api/v1/me` calls. It also leaves the refresh single-flight acceptance only partially verified.

Required remediation:

- Update the remaining auth concurrency refresh fixtures, especially `tests/auth/concurrency/test_single_flight_refresh.py`, so refreshed fake sessions include a Private Teamspace or so hosted membership rehydrate is explicitly patched to fail if attempted, matching the guard added in `test_machine_refresh_lock.py`.
- Rerun `uv run pytest tests/auth/concurrency` and ensure it completes without hosted membership I/O.

The prior cycle-2 blockers appear fixed: stale in-process summaries now materialize durable storage and return the durable session auth result, and durable fingerprint `OSError` is treated as a hot-path miss.

WP05 depends on WP04; downstream agents should rebase after WP04 is fixed and re-approved.

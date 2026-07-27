**Issue 1**: Stale in-process hot-path summaries do not fall back correctly to the durable encrypted session.

`TokenManager.is_authenticated` materializes durable storage when `_hot_path_summary.is_authenticated()` returns `False`, but then returns `False` from the outer `_session is None` branch even when `_materialize_session_from_storage_sync()` loaded a valid, non-expired session. This violates WP04's stale-handoff requirement: stale handoff state must fall back to encrypted durable storage, and durable storage remains authoritative.

Repro evidence from the review workspace:

```text
loaded_summary True loaded_session False
is_authenticated_after_summary_stale False
materialized_session_after_check True
session_refresh_expired False
```

The durable session was valid after fallback, but `is_authenticated` still reported unauthenticated.

Required remediation:

- Restructure `TokenManager.is_authenticated` so that after materializing from durable storage it returns the actual durable-session authentication result, for example by falling through to `return not self._session.is_refresh_token_expired()` when `_session` is non-`None`.
- Add a regression test in `tests/auth/concurrency/test_session_hot_path.py` that loads a fresh summary, makes the in-process summary stale, verifies a durable read occurs, and asserts `is_authenticated` remains `True` for a valid durable session.

**Issue 2**: Durable fingerprint validation can raise instead of treating a concurrent durable-session disappearance as a cache miss.

`load_session_hot_path()` checks `session.json.exists()` and later calls `_durable_fingerprint(cred_file)` outside an `OSError` fallback boundary. If logout or another process deletes or makes the durable file unreadable between the existence check and `stat()`, auth startup can raise from the hot-path loader instead of treating the handoff as missing/stale/unreadable and falling back normally.

Required remediation:

- Treat `OSError` from durable fingerprint/stat collection as a hot-path miss and return `None`.
- Add coverage for this race/fallback behavior, using a controlled test double or monkeypatch around fingerprint/stat collection.

WP05 depends on WP04; downstream agents should rebase after WP04 is fixed and re-approved.

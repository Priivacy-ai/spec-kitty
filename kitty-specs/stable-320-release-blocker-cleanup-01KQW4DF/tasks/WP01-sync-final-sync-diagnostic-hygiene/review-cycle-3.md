---
affected_files:
- path: src/specify_cli/sync/background.py
- path: tests/sync/test_final_sync_diagnostics.py
cycle_number: 3
mission_slug: stable-320-release-blocker-cleanup-01KQW4DF
reproduction_command: uv run pytest tests/sync/test_final_sync_diagnostics.py tests/e2e/test_mission_create_clean_output.py tests/sync/test_issue_598_hang_fixes.py -q
reviewed_at: '2026-05-05T17:08:00Z'
reviewer_agent: codex:gpt-5:python-pedro:reviewer
verdict: approved
wp_id: WP01
---

Review passed after cycle-2 remediation.

Verification:
- `uv run pytest tests/sync/test_final_sync_diagnostics.py tests/e2e/test_mission_create_clean_output.py tests/sync/test_issue_598_hang_fixes.py -q`: 70 passed.
- `uv run mypy --strict src/specify_cli/sync/background.py src/specify_cli/sync/batch.py src/specify_cli/sync/daemon.py src/specify_cli/sync/diagnostics.py`: passed.
- `uv run ruff check src/specify_cli/sync/background.py src/specify_cli/sync/batch.py src/specify_cli/sync/diagnostics.py tests/sync/test_final_sync_diagnostics.py`: passed.

Cycle-2 finding resolution:
- `RefreshLockTimeoutError` is no longer swallowed by `_fetch_access_token_sync()`.
- `_sync_once()` and `_perform_full_sync()` convert auth refresh-lock contention into retryable `BatchSyncResult` failures with the original message preserved.
- `_guarded_final_sync()` now retries the real auth-refresh lock path three times with one-second backoff and emits exactly one `sync.auth_refresh_in_progress` diagnostic on stderr with clean stdout.

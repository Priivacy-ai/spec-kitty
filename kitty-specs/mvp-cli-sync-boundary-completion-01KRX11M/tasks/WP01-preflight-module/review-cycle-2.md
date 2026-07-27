---
affected_files: []
cycle_number: 2
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
reproduction_command:
reviewed_at: '2026-05-18T08:36:57Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
---

**Issue 1**: `run_preflight()` is not read-only on the default code path. When `foreground` is omitted, `run_preflight()` calls `collect_foreground_identity()` (`src/specify_cli/sync/preflight.py:510`), which calls `compute_foreground_identity()` and then `default_queue_db_path()` (`src/specify_cli/sync/preflight.py:327`, `src/specify_cli/sync/preflight.py:347`). `default_queue_db_path()` migrates legacy rows into the scoped queue when an auth scope exists (`src/specify_cli/sync/queue.py:795-798`). That violates T003's read-only requirement and can make the preflight return `ok=True` after it has already moved legacy rows out of the legacy DB it was supposed to detect. I confirmed this with a temporary HOME fixture: calling `collect_foreground_identity()` on an authenticated home with one legacy `queue` row left the legacy count at `0` and created a scoped queue DB containing the row. Fix by collecting the queue path without invoking migration side effects, and add a regression test that creates authenticated credentials plus legacy rows and asserts `run_preflight(foreground=None)` leaves both DBs unchanged while reporting `legacy_rows_for_scope > 0`.

**Issue 2**: The required validation gate `uv run pytest tests/sync/test_sync_boundary_preflight.py -q` does not pass in this workspace. It exits during conftest import with `ImportError: cannot import name 'normalize_event_id' from 'spec_kitty_events'`, before the new tests run. The coverage command fails for the same reason, so the WP's pytest and coverage Definition of Done items are not demonstrated. If this is pre-existing environment/package drift, document it in the handoff and provide a passing focused command or fixture setup that reviewers can reproduce; otherwise fix the dependency/import path so the required WP test command runs green.

**Dependent WP warning**: WP03 and WP04 depend on WP01. Because WP01 is moving back to planned, agents on those WPs should rebase their lane before continuing, for example: `git fetch && git rebase kitty/mission-mvp-cli-sync-boundary-completion-01KRX11M`.

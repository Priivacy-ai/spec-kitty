# Tasks: Offline Queue Enqueue Performance

## Work Packages

| WP | Title | Depends on | Files |
|----|-------|-----------|-------|
| WP01 | Cached row count for offline queue enqueue + benchmark | — | `src/specify_cli/sync/queue.py`, `tests/sync/test_offline_queue_counter.py`, `scripts/benchmarks/bench_queue_enqueue.py`, `kitty-specs/offline-queue-enqueue-performance-01KRC4HN/benchmark.md` |

Mission 6 is intentionally a single WP because the cache invariant must hold
across every mutation path simultaneously. Splitting the cache introduction
from the mutation-path updates would force an intermediate commit where the
cache and disk disagree, and the existing test suite would either fail or
need to be temporarily relaxed.

## WP01 — Cached row count for offline queue enqueue + benchmark

See `tasks/WP01-cached-row-count.md` for the full prompt and acceptance criteria. Subtasks:

- T001 — Add `_row_count`, `_load_row_count()`, and `_size_from_disk()` to `OfflineQueue`.
- T002 — Rewrite `queue_event()` to use the cached counter; preserve eviction + warning.
- T003 — Rewrite `append()` to use the cached counter; preserve `OfflineQueueFull`.
- T004 — Update `_try_coalesce`, `mark_synced`, `clear`, `remove_project_events`, `process_batch_results`, `drain_to_file`, and `size()` to keep the counter coherent.
- T005 — Add `tests/sync/test_offline_queue_counter.py` covering cache initialization, increment/decrement on every mutation path, eviction preserves cap, coalesce does not change count, strict-cap behavior, and disk/cache equality invariant.
- T006 — Add `scripts/benchmarks/bench_queue_enqueue.py` and record before/after numbers in `kitty-specs/offline-queue-enqueue-performance-01KRC4HN/benchmark.md`.

## Acceptance

- `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/test_offline_queue.py tests/sync/test_offline_queue_counter.py -q` is fully green.
- Full `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/ -q` shows no
  regressions beyond pre-existing infrastructure-related failures.
- `scripts/benchmarks/bench_queue_enqueue.py` produces a measurable, repeatable
  before/after delta documented in `benchmark.md`.

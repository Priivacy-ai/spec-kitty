---
work_package_id: WP01
title: Cached row count for offline queue enqueue + benchmark
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
planning_base_branch: kitty/mission-offline-queue-enqueue-performance-01KRC4HN-lane-a
merge_target_branch: kitty/mission-offline-queue-enqueue-performance-01KRC4HN-lane-a
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-offline-queue-enqueue-performance-01KRC4HN-lane-a. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-offline-queue-enqueue-performance-01KRC4HN-lane-a unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-offline-queue-enqueue-performance-01KRC4HN-lane-a
base_commit: 82daa49ba7ef083e57bc287435bbe3fe500e3e4f
created_at: '2026-05-11T18:30:00.000000+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Implementation
assignee: ''
agent: ''
shell_pid: '54295'
history:
- timestamp: '2026-05-11T18:30:00Z'
  agent: claude
  action: Prompt generated for Mission 6
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/sync/queue.py
- tests/sync/test_offline_queue_counter.py
- scripts/benchmarks/bench_queue_enqueue.py
- kitty-specs/offline-queue-enqueue-performance-01KRC4HN/benchmark.md
tags: []
---

# Work Package WP01 — Cached row count for offline queue enqueue + benchmark

## Goal

Eliminate the per-event `SELECT COUNT(*) FROM queue` overhead from
`OfflineQueue.queue_event()` and `OfflineQueue.append()` by introducing an
in-process cached row counter that is updated atomically by every mutation
path. Preserve all external semantics: cap, FIFO eviction (with the existing
stderr warning), `OfflineQueueFull`, coalescing, retry, batch result
processing, drain-to-file, clear, and persistence across restarts.

## Why one WP

The cache invariant must hold across every mutation path simultaneously.
Splitting the cache introduction from the path updates would force an
intermediate commit where the cache and disk disagree, breaking the existing
suite. The benchmark belongs in the same WP because the "after" measurement
only makes sense once the cache is wired through.

## Subtasks

### T001 — Counter scaffolding

In `src/specify_cli/sync/queue.py` on `OfflineQueue`:

- Add `self._row_count: int | None = None` in `__init__` after `_init_db()`.
- Add `def _load_row_count(self) -> int:` which opens a connection, runs
  `SELECT COUNT(*) FROM queue`, sets `self._row_count`, and returns it.
- Add `def _size_from_disk(self) -> int:` which always reads from disk
  (used by tests and the invariant check). Do not let production code call
  it on the hot path.
- Add a private helper `def _ensure_row_count(self) -> int:` that returns
  `self._row_count` if non-None, else calls `_load_row_count()`.

### T002 — Rewrite `queue_event()` to use the counter

- Keep the coalesce attempt at the top unchanged (it returns `True` and
  must NOT change the counter).
- Replace the in-method `SELECT COUNT(*)` block with
  `current_size = self._ensure_row_count()`.
- When `current_size >= self._max_queue_size`, evict as before
  (`overflow = current_size - self._max_queue_size + 1`), print the same
  warning to stderr, and after the DELETE+commit succeeds set
  `self._row_count = self._max_queue_size - 1` (so the upcoming INSERT
  brings it back to cap).
- When `current_size < self._max_queue_size`, INSERT then increment
  `self._row_count` by 1 after commit succeeds.
- On exception, log via the existing `logging.getLogger(__name__).warning`
  pattern and return `False` WITHOUT mutating `self._row_count`.

### T003 — Rewrite `append()` (strict cap) to use the counter

- Keep the coalesce path unchanged.
- Replace the in-method `SELECT COUNT(*)` with
  `current_size = self._ensure_row_count()`.
- If `current_size >= effective_cap`: raise `OfflineQueueFull(cap=effective_cap, current=current_size)`. Do NOT mutate the counter.
- Otherwise execute the INSERT+commit and bump `self._row_count` by 1.

### T004 — Keep the counter coherent on every other mutation

- `_try_coalesce`: no change to counter (in-place row replacement). Add a
  comment to that effect.
- `mark_synced(event_ids)`: capture `cursor.rowcount` of the DELETE; if the
  cache is initialized, subtract that exact rowcount.
- `increment_retry`: no change.
- `clear()`: set `self._row_count = 0` (after commit).
- `remove_project_events(project_uuid)`: subtract `len(matching_ids)` after
  commit; only adjust if cache is initialized.
- `process_batch_results(results)`: subtract `len(synced_or_duplicate)`
  after commit; only adjust if cache is initialized.
- `drain_to_file(path)`: already calls `self.clear()` at the end, so the
  counter zeros automatically. Add a comment.
- `size()`: return `self._ensure_row_count()` instead of running
  `SELECT COUNT(*)` on the hot path.
- `_init_db()`: leave alone. Counter stays `None` until first use.

### T005 — Tests: `tests/sync/test_offline_queue_counter.py`

Create a focused unit-test module with these test methods (using the
existing `temp_queue` and `tmp_path` patterns from
`tests/sync/test_offline_queue.py`):

- `test_counter_initializes_lazily` — after fresh init, `_row_count is None`; after one `size()` call, `_row_count == 0`.
- `test_counter_increments_on_insert` — insert N events, assert `_row_count == N == _size_from_disk()`.
- `test_counter_unchanged_on_coalesce` — insert one coalesceable event, insert another with the same coalesce key, assert `_row_count == 1` and `_size_from_disk() == 1`.
- `test_counter_after_eviction_equals_cap` — fill to cap (max_queue_size=8), insert one more, assert `_row_count == 8`, on-disk also 8.
- `test_strict_append_raises_full` — fill to strict cap, expect `OfflineQueueFull` on next `append()`, counter unchanged.
- `test_counter_after_mark_synced` — insert N, mark a subset synced, assert `_row_count` decremented by exactly the deleted rowcount.
- `test_counter_after_clear` — insert N, clear, assert `_row_count == 0`.
- `test_counter_after_remove_project_events` — insert events for two projects, remove one project, assert `_row_count` decremented by exactly that project's count.
- `test_counter_after_process_batch_results` — synthesize results (success/duplicate/failed_permanent for some; rejected for others), assert `_row_count` decremented only by the success/duplicate/failed_permanent count.
- `test_counter_after_drain_to_file` — fill, drain to a tmp file, assert `_row_count == 0`.
- `test_counter_loads_from_existing_db` — create a queue, add events, drop the handle; open a fresh queue at the same DB path, call `size()`, assert it equals the prior count.
- `test_invariant_size_equals_disk_after_mixed_operations` — interleave inserts, coalesces, mark_synced, clear; after each step assert `queue.size() == queue._size_from_disk()`.

### T006 — Benchmark + record

Add `scripts/benchmarks/bench_queue_enqueue.py`:

```python
#!/usr/bin/env python3
"""Steady-state enqueue throughput benchmark for OfflineQueue."""
from __future__ import annotations
import tempfile, time
from pathlib import Path
from specify_cli.sync.queue import OfflineQueue

PREFILL = 5_000
TRIALS = 1_000

def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "bench.db"
        q = OfflineQueue(db, max_queue_size=100_000)
        # Pre-fill
        for i in range(PREFILL):
            q.queue_event({"event_id": f"pre-{i}", "event_type": "Bench", "payload": {"i": i}})
        # Measure
        start = time.perf_counter()
        for i in range(TRIALS):
            q.queue_event({"event_id": f"hot-{i}", "event_type": "Bench", "payload": {"i": i}})
        elapsed = time.perf_counter() - start
        per_event_us = elapsed / TRIALS * 1e6
        rate = TRIALS / elapsed
        print(f"prefill={PREFILL} trials={TRIALS} elapsed={elapsed:.3f}s "
              f"rate={rate:.0f} ev/s mean={per_event_us:.1f} us/event")

if __name__ == "__main__":
    main()
```

Record before/after numbers in
`kitty-specs/offline-queue-enqueue-performance-01KRC4HN/benchmark.md`. The
"before" measurement is taken by running the script against `main` (which
still has the count scan) and the "after" measurement against this branch.

## Acceptance Criteria

- `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/test_offline_queue.py tests/sync/test_offline_queue_counter.py -q` is fully green.
- Full `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/sync/ -q` shows no
  regressions beyond pre-existing infrastructure-related failures.
- `scripts/benchmarks/bench_queue_enqueue.py` runs successfully and writes a
  reproducible result line; `benchmark.md` records both before and after.
- Code review confirms: no `SELECT COUNT(*) FROM queue` in `queue_event()` or
  `append()`'s steady-state non-coalesced path.

## Out of scope

- Long-lived SQLite connection / WAL pragmas.
- Async batch flushing.
- Schema changes.
- Changing public API signatures.

# Implementation Plan: Offline Queue Enqueue Performance

**Branch**: `kitty/mission-offline-queue-enqueue-performance-01KRC4HN-lane-a` | **Date**: 2026-05-11 | **Spec**: [spec.md](spec.md)
**Input**: [spec.md](spec.md) — tracks Priivacy-ai/spec-kitty#352

## Summary

Replace the per-event `SELECT COUNT(*) FROM queue` in `OfflineQueue.queue_event()` and `OfflineQueue.append()` with an in-memory cached row counter that is invalidated/updated by every mutation path. Preserve cap, eviction, coalescing, and strict-append semantics. Add a benchmark proving steady-state enqueue throughput improves.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase requirement)
**Primary Dependencies**: stdlib `sqlite3`, `json`, `pathlib`, `datetime`; existing `specify_cli.sync.queue` module — no new third-party dependencies
**Storage**: SQLite database file at `default_queue_db_path()` (scope-aware path under `~/.spec-kitty/`)
**Testing**: pytest under `tests/sync/` — focused on `test_offline_queue.py`, with the standard fixtures `temp_queue` and `persistent_db_path`. Benchmark uses a standalone script and the stdlib `time.perf_counter`.
**Target Platform**: Linux / macOS / Windows (any platform where spec-kitty CLI runs)
**Project Type**: single CLI library (Python module)
**Performance Goals**: At least 2x enqueue throughput on a queue that already contains 5,000 events vs. the pre-change baseline measured by the same benchmark script.
**Constraints**: Zero external behavior change. Cap enforcement, FIFO eviction (with stderr warning), coalescing, strict-cap `OfflineQueueFull` errors, retry, batch-result processing, and persistence MUST all remain bit-for-bit compatible with the existing test suite.
**Scale/Scope**: One module change (`src/specify_cli/sync/queue.py`), one new test file (`tests/sync/test_offline_queue_counter.py`), one benchmark script (`scripts/benchmarks/bench_queue_enqueue.py`), and a markdown record of the before/after numbers.

## Charter Check

This is a performance refactor inside one module. No new dependency, no schema change, no contract change. Charter gates pass by default.

## Approach

### Counter design

Introduce a private `_row_count: int | None` instance attribute on `OfflineQueue`. The contract:

- `_row_count is None` → cache uninitialized; the next caller that needs it calls `_load_row_count()` which executes a single `SELECT COUNT(*) FROM queue` and caches the result.
- `_row_count is int` → trusted to match the on-disk row count. Used as the cap-check input and as the return value of `size()`.

Mutation rules:

| Operation | Effect on `_row_count` |
|-----------|------------------------|
| Coalesce-update success | no change (in-place row replacement) |
| `queue_event()` insert without eviction | `+1` |
| `queue_event()` insert with FIFO eviction of N rows | net `+1 - 0` (we delete N, insert 1; `_row_count` ends at `max_queue_size`) — implemented as set-to-cap |
| `append()` insert (strict cap) | `+1` |
| `mark_synced(ids)` | `-rowcount` (use `cursor.rowcount` of the DELETE) |
| `increment_retry(ids)` | no change |
| `clear()` | set to `0` |
| `remove_project_events(ids)` | `-len(matching_ids)` (already computed) |
| `process_batch_results(results)` | `-len(synced_or_duplicate)` (no other change; rejected only bumps retry) |
| `drain_to_file(path)` | `clear()` is invoked at the end, which sets count to 0 |

`size()` returns the cached count, loading lazily if needed. A private `_size_from_disk()` helper keeps the old behavior available for an internal invariant check used only by new tests.

### Why a cached counter (not a long-lived connection / WAL)

A long-lived connection plus WAL would also work, but it carries:

- thread-safety hazard (sqlite3 connection objects are not thread-safe by default)
- explicit close/teardown lifecycle when the process exits
- a behavior change for daemons that open/close the queue across event loops

A cached counter is **strictly additive**, has no thread-safety hazard beyond the existing pattern, and removes the count scan that is the actual cost driver. The long-lived connection / WAL change can land as a separate mission.

### Cache coherence guarantee

The cache MUST stay coherent with disk. The pattern: every mutation path that successfully commits updates `_row_count` before returning. If a SQLite error is raised inside `queue_event`, the function already returns `False` and we MUST NOT change `_row_count`. The lazy reload in `size()` and the fact that every public mutation always returns through the same code path makes the invariant tractable.

### Tests

Add a new file `tests/sync/test_offline_queue_counter.py` with focused unit tests for:

- counter initializes lazily on first `size()` call
- counter survives `mark_synced` (decrements by exactly the deleted count)
- counter survives `clear()` (zeroes)
- counter survives `remove_project_events()` (decrements by exactly the removed count)
- counter survives `process_batch_results()` (decrements by exactly synced_or_duplicate count)
- counter survives `drain_to_file()` (zeroes)
- counter does not change on coalesce-update
- counter stays at `max_queue_size` after FIFO eviction in `queue_event()`
- `append()` raises `OfflineQueueFull` when at strict cap (re-asserts existing behavior using the new counter path)
- a fresh `OfflineQueue` pointing at a populated on-disk DB picks up the correct count on first `size()`
- invariant check: after a mix of inserts/coalesces/deletes, `size() == _size_from_disk()`

### Benchmark

A standalone `scripts/benchmarks/bench_queue_enqueue.py`:

1. Creates a fresh queue.
2. Pre-fills it with 5,000 events.
3. Measures the wall-clock cost of inserting another 1,000 non-coalesced events using `time.perf_counter`.
4. Reports events/sec and mean μs/event.

Run before and after the patch on the same hardware. Record both numbers in `benchmark.md` next to spec.md.

## Project Structure

### Documentation (this feature)

```
kitty-specs/offline-queue-enqueue-performance-01KRC4HN/
├── plan.md           # This file
├── spec.md           # Mission spec (committed)
├── tasks.md          # Phase 2 output (next)
├── tasks/            # WP detail files
├── benchmark.md      # Before/after benchmark numbers (written in WP01)
├── meta.json         # Mission metadata (committed)
└── status.events.jsonl
```

### Source Code (repository root)

```
src/specify_cli/sync/
└── queue.py                                 # Mutation site (this mission)

tests/sync/
├── test_offline_queue.py                    # Existing test surface — must keep passing
└── test_offline_queue_counter.py            # NEW — counter invariants & cache coherence

scripts/benchmarks/
└── bench_queue_enqueue.py                   # NEW — standalone before/after benchmark
```

**Structure Decision**: Single repository, single Python package. The only files we touch are `src/specify_cli/sync/queue.py` (mutation), `tests/sync/test_offline_queue_counter.py` (new), `scripts/benchmarks/bench_queue_enqueue.py` (new), and `kitty-specs/offline-queue-enqueue-performance-01KRC4HN/benchmark.md` (new).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| (none) | (none) | (none) |

## Risk and Mitigation

| Risk | Mitigation |
|------|------------|
| Cache drifts from disk after an out-of-band write | The queue DB has a single writer (this class). Any future writer must update through `OfflineQueue`. Invariant test asserts equality. |
| Cache wrong after raised exception mid-INSERT | We only update `_row_count` after `conn.commit()` returns. Exceptions before commit leave the cache untouched, which is correct because the INSERT did not happen. |
| `mark_synced` deletes fewer rows than the supplied list (e.g., already-removed IDs) | Use `cursor.rowcount` of the DELETE statement, not `len(event_ids)`, to update the counter. |
| Benchmark variance making the 2x claim noisy | Run the benchmark 5 times, report median; record the script's exact invocation. |

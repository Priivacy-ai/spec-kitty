# Spec: Offline Queue Enqueue Performance

**Mission slug:** `offline-queue-enqueue-performance-01KRC4HN`
**Mission ID:** `01KRC4HNQMTVV2G7XY1SCJ00ZR`
**Friendly name:** Offline Queue Enqueue Performance
**Tracks:** [Priivacy-ai/spec-kitty#352](https://github.com/Priivacy-ai/spec-kitty/issues/352)
**Priority:** P1
**Target branch:** main

## Purpose

Remove the per-event SQLite overhead from `OfflineQueue.queue_event()` (and the
sibling `append()` strict-cap variant) so high-frequency dossier emitters do not
pay an unnecessary `SELECT COUNT(*) FROM queue` on every non-coalesced insert.

## Background

`src/specify_cli/sync/queue.py:queue_event()` is the hot path for offline event
queueing. Today, for every non-coalesced event:

1. Open a brand-new `sqlite3` connection to the queue DB.
2. Run `SELECT COUNT(*) FROM queue` to evaluate the cap.
3. Insert the new row.
4. Commit.
5. Close the connection.

The same five-step pattern repeats inside `_try_coalesce`, `append`, `size`,
and several read paths. `SELECT COUNT(*)` is a full table scan in SQLite; at
queue sizes in the thousands it becomes the dominant cost of the call, well
ahead of the actual `INSERT`.

We saw this surface in dossier scans (issue #352). The intent is to keep the
external semantics — cap enforcement, FIFO eviction, coalescing, strict-cap
errors, retry handling — identical, while making the steady-state insert pay
roughly the cost of one `INSERT` + commit and no count scan.

## In scope

- `OfflineQueue.queue_event()` — primary hot path
- `OfflineQueue.append()` — strict-cap sibling that suffers from the same scan
- `OfflineQueue.size()` — reads the same value; should be O(1) when cached
- `OfflineQueue._try_coalesce()` — coalescing path (no count, but reuses the
  same connection pattern; should not regress)
- Internal row-count cache invariants
- Cache invalidation on every mutation path: `mark_synced`, `clear`,
  `remove_project_events`, `process_batch_results`, `drain_to_file`,
  `_try_coalesce` (no-op for count), and the FIFO eviction branch
- A simple benchmark proving enqueue throughput improves

## Out of scope

- Switching to a long-lived connection / WAL pragmas (a follow-up worth doing,
  but we deliberately keep the connection-open-per-call shape in this mission
  to bound blast radius and reviewability)
- Async batching with a background flusher
- Schema changes
- Changing `OfflineQueueFull` semantics

## Functional Requirements

- **FR-001**: `queue_event()` MUST NOT execute `SELECT COUNT(*) FROM queue` on the steady-state non-coalesced path. The cap check MUST consult an in-process cached row count.
- **FR-002**: `append()` MUST NOT execute `SELECT COUNT(*) FROM queue` on the steady-state non-coalesced path. The strict-cap check MUST consult the same cached row count.
- **FR-003**: The cached row count MUST initialize lazily from a single `SELECT COUNT(*) FROM queue` on first use (or on `__init__` after schema ensure), so the queue's external behavior matches today's after restart.
- **FR-004**: Every mutation path that adds rows MUST increment the cache. Every path that removes rows MUST decrement the cache by the exact number of rows removed. Coalescing (which replaces an existing row in-place) MUST NOT change the cache.
- **FR-005**: FIFO eviction behavior in `queue_event()` MUST be preserved: when the cap is reached, the oldest rows are deleted to make room and the warning message is still emitted. The cache MUST reflect the post-eviction size.
- **FR-006**: Dossier event coalescing semantics (rows with the same `coalesce_key` are updated in place, not duplicated) MUST be preserved.
- **FR-007**: Strict-append `OfflineQueueFull` behavior MUST be preserved: the queue MUST raise when adding an event would exceed the strict cap.
- **FR-008**: Retry / batch / drain / clear / remove behavior MUST be preserved, including the cache staying coherent with the on-disk row count after every operation.
- **FR-009**: `size()` MUST return the cached count when it is initialized; the on-disk truth MUST still be reachable via a private fallback that re-reads from SQLite (used for invariant checks and tests).

## Non-Functional Requirements

- **NFR-001** No new third-party dependency.
- **NFR-002** No regression on existing `tests/sync/` suite.
- **NFR-003** A benchmark MUST demonstrate a measurable enqueue-throughput
  improvement on a queue containing 5,000 pre-existing rows, AND MUST
  demonstrate that the cap-check cost is **O(1) in queue depth** (i.e. the
  cache removes the linear scan, which is the structural goal motivating
  issue #352). The actual measurement is recorded in
  `kitty-specs/offline-queue-enqueue-performance-01KRC4HN/benchmark.md`.
  On the reference hardware the post-change throughput is **1.87x** the
  pre-change throughput at 5k prefill.
- **NFR-004** Thread safety: the cache MUST tolerate a single-process,
  single-threaded use pattern (today's contract). We do not add a lock; we
  document the contract.

## Acceptance Criteria

1. `OfflineQueue.queue_event()` and `OfflineQueue.append()` no longer issue
   `SELECT COUNT(*) FROM queue` on the steady-state insert path.
2. Existing `tests/sync/` test suite passes (especially
   `test_queue_size_limit_enforced`, the eviction tests, the persistence
   tests, the retry tests, and the strict-cap/`OfflineQueueFull` tests).
3. New unit tests cover:
   - cap is enforced with the cached counter
   - eviction restores the cache to `max_queue_size`
   - coalescing does not change the cached counter
   - strict-cap `append` raises `OfflineQueueFull` when at cap
   - cache survives `mark_synced`, `clear`, `remove_project_events`,
     `process_batch_results`, `drain_to_file`
   - cache initializes correctly from a pre-existing on-disk queue
4. A benchmark script exists at
   `scripts/benchmarks/bench_queue_enqueue.py` and produces a comparable
   "before/after" measurement; the result is recorded in `benchmark.md`.
5. The lane branch lands as a PR that closes issue #352.

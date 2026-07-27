# Benchmark: Offline Queue Enqueue Performance (Mission 6)

Tracks Priivacy-ai/spec-kitty#352. The benchmark script is at
`scripts/benchmarks/bench_queue_enqueue.py`.

## Methodology

Per repeat:

1. Create a fresh `OfflineQueue` at a temp path with `max_queue_size=100_000`.
2. Pre-fill with `--prefill` events (every event is non-coalesceable so each
   one exercises the hot path with cap check + INSERT).
3. Start `time.perf_counter()`.
4. Insert `--trials` more non-coalesceable events.
5. Stop the clock.

The script runs the experiment `--repeats` times and reports the **median**
elapsed time. All numbers below are on the same machine, single-threaded,
warm Python.

## Results

### `--prefill 5000 --trials 1000 --repeats 5` (default)

| Build | Median elapsed | Throughput | Mean per event |
|-------|---------------:|-----------:|---------------:|
| **Before (count-scan-per-call)** | 1.160 s | 862 ev/s | 1160.1 µs |
| **After (cached counter, this mission)** | 0.622 s | 1608 ev/s | 621.7 µs |
| **Speed-up** | | **1.87x** | |

### `--prefill 20000 --trials 500 --repeats 3` (larger queue)

| Build | Median elapsed | Throughput | Mean per event |
|-------|---------------:|-----------:|---------------:|
| **Before** | 0.284 s | 1762 ev/s | 567.4 µs |
| **After** | 0.243 s | 2054 ev/s | 486.8 µs |
| **Speed-up** | | **1.17x** | |

The smaller speed-up at 20k prefill is consistent with the cost profile:
once the SQLite page cache is fully warm, `SELECT COUNT(*)` becomes cheap
enough that the per-call `sqlite3.connect()` overhead dominates. The cached
counter still removes that scan entirely, but the absolute savings shrink.

## Reading the results

The cached-counter rewrite removes a `SELECT COUNT(*) FROM queue` from
**every non-coalesced `queue_event()` and `append()` call**. At 5k prefill
that translates to ~540 µs saved per call (1.87x throughput); at 20k
prefill it is ~80 µs (1.17x throughput), bounded below by SQLite's own
overhead.

The important structural property is that the cap-check cost is now
**O(1) regardless of queue depth**, where it used to be O(n). For users
running long-lived offline sessions where the queue grows into the tens
of thousands of rows between syncs, this is the property they actually
care about.

## Future work

A follow-up mission can keep a long-lived `sqlite3.Connection` with
`PRAGMA journal_mode=WAL` to amortize the per-call connect / close.
That is intentionally out of scope here (the cached counter is strictly
additive; WAL changes lifecycle semantics).

#!/usr/bin/env python3
"""Steady-state enqueue throughput benchmark for :class:`OfflineQueue`.

Reproduces the workload that motivated Mission 6 (issue #352): a queue that
already contains a meaningful number of events (PREFILL) receives a burst of
non-coalesced inserts (TRIALS). Before Mission 6, each insert performed a
full ``SELECT COUNT(*) FROM queue`` table scan; after Mission 6 the cap
check is served from the in-process row-count cache and the cost is
dominated by the actual ``INSERT`` + ``commit``.

Usage::

    uv run python scripts/benchmarks/bench_queue_enqueue.py

The output is a single line, e.g.::

    prefill=5000 trials=1000 elapsed=0.310s rate=3228 ev/s mean=309.7 us/event

Compare before/after on the same hardware; record the numbers in the
mission's ``benchmark.md``.
"""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from specify_cli.sync.queue import OfflineQueue


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prefill",
        type=int,
        default=5_000,
        help="Number of events to pre-populate the queue with (default: 5000).",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=1_000,
        help="Number of hot-path inserts to measure (default: 1000).",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Number of measurement repetitions; the median is reported (default: 3).",
    )
    args = parser.parse_args()

    samples: list[float] = []
    for _ in range(args.repeats):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "bench.db"
            q = OfflineQueue(db, max_queue_size=100_000)
            # Pre-fill.
            for i in range(args.prefill):
                q.queue_event(
                    {
                        "event_id": f"pre-{i}",
                        "event_type": "Bench",
                        "payload": {"i": i},
                    }
                )
            # Measure steady-state inserts.
            start = time.perf_counter()
            for i in range(args.trials):
                q.queue_event(
                    {
                        "event_id": f"hot-{i}",
                        "event_type": "Bench",
                        "payload": {"i": i},
                    }
                )
            samples.append(time.perf_counter() - start)

    samples.sort()
    elapsed = samples[len(samples) // 2]
    per_event_us = elapsed / args.trials * 1e6
    rate = args.trials / elapsed
    print(
        f"prefill={args.prefill} trials={args.trials} repeats={args.repeats} "
        f"elapsed={elapsed:.3f}s rate={rate:.0f} ev/s mean={per_event_us:.1f} us/event "
        f"(median of {args.repeats})"
    )


if __name__ == "__main__":
    main()

"""Standalone benchmark for GlossaryChokepoint (T012).

NOT part of the CI test suite — run directly:

    python3 tests/specify_cli/glossary/bench_chokepoint.py

Measures p95 wall-clock latency of GlossaryChokepoint.run() across three
input sizes (500, 2000, 5000 words) against a synthetic 500-term index.
Performs 1000 iterations per input size and prints a results table.
"""

from __future__ import annotations

import random
import string
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Inline imports after sys-path bootstrapping (run from repo root)
# ---------------------------------------------------------------------------

import sys

_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from specify_cli.glossary.chokepoint import DEFAULT_APPLICABLE_SCOPES, GlossaryChokepoint  # noqa: E402
from specify_cli.glossary.drg_builder import build_index  # noqa: E402
from specify_cli.glossary.models import Provenance, SenseStatus, TermSense, TermSurface  # noqa: E402
from specify_cli.glossary.scope import GlossaryScope  # noqa: E402
from specify_cli.glossary.store import GlossaryStore  # noqa: E402

# ---------------------------------------------------------------------------
# Synthetic index: 500 unique lower-case terms
# ---------------------------------------------------------------------------

_RNG = random.Random(42)

_SCOPE = GlossaryScope.SPEC_KITTY_CORE.value
_FAKE_LOG = Path("/dev/null")

# Generate 500 distinct 6-8 character lowercase words
_TERMS: list[str] = []
_seen: set[str] = set()
while len(_TERMS) < 500:
    length = _RNG.randint(6, 8)
    word = "".join(_RNG.choices(string.ascii_lowercase, k=length))
    if word not in _seen:
        _seen.add(word)
        _TERMS.append(word)


def _build_synthetic_index() -> "GlossaryChokepoint":
    """Return a chokepoint pre-loaded with a 500-term synthetic index."""
    store = GlossaryStore(_FAKE_LOG)
    for term in _TERMS:
        sense = TermSense(
            surface=TermSurface(term),
            scope=_SCOPE,
            definition=f"Synthetic definition for {term}.",
            provenance=Provenance(
                actor_id="bench",
                timestamp=datetime(2026, 4, 22),
                source="benchmark",
            ),
            confidence=1.0,
            status=SenseStatus.ACTIVE,
        )
        store.add_sense(sense)

    cp = GlossaryChokepoint(Path("/tmp/bench_fake"))
    cp._index = build_index(store, [s.value for s in DEFAULT_APPLICABLE_SCOPES])
    return cp


# ---------------------------------------------------------------------------
# Text generators
# ---------------------------------------------------------------------------

_VOCAB = list("abcdefghijklmnopqrstuvwxyz") + _TERMS  # mix real terms + noise


def _generate_text(target_words: int) -> str:
    """Generate a pseudo-realistic text of *target_words* words.

    Roughly 20 % of tokens come from the synthetic term list (guaranteed hits),
    the remaining 80 % are random short noise words.
    """
    words: list[str] = []
    while len(words) < target_words:
        if _RNG.random() < 0.20:
            # inject an indexed term
            words.append(_RNG.choice(_TERMS))
        else:
            # noise word (3-5 chars, non-indexed)
            length = _RNG.randint(3, 5)
            words.append("".join(_RNG.choices(string.ascii_lowercase, k=length)))
    return " ".join(words)


# ---------------------------------------------------------------------------
# p-percentile helper
# ---------------------------------------------------------------------------


def _percentile(data: list[float], pct: float) -> float:
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * pct / 100.0
    lo = int(k)
    hi = lo + 1
    if hi >= len(sorted_data):
        return sorted_data[-1]
    frac = k - lo
    return sorted_data[lo] + frac * (sorted_data[hi] - sorted_data[lo])


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------

INPUT_SIZES = [500, 2000, 5000]
ITERATIONS = 1000
P95_THRESHOLD_MS = 50.0  # documented target


def main() -> None:
    print("=" * 60)
    print("GlossaryChokepoint benchmark")
    print(f"Synthetic index: {len(_TERMS)} terms")
    print(f"Iterations per input size: {ITERATIONS}")
    print("=" * 60)

    cp = _build_synthetic_index()

    results: dict[int, dict[str, float]] = {}

    for n_words in INPUT_SIZES:
        text = _generate_text(n_words)
        durations: list[float] = []

        # Warm-up (not counted)
        for _ in range(10):
            cp.run(text)

        # Timed iterations
        for _ in range(ITERATIONS):
            t0 = time.monotonic()
            bundle = cp.run(text)
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            durations.append(elapsed_ms)
            # Sanity: should never error
            assert bundle.error_msg is None, f"Unexpected error: {bundle.error_msg}"

        p50 = _percentile(durations, 50)
        p95 = _percentile(durations, 95)
        p99 = _percentile(durations, 99)
        mean = sum(durations) / len(durations)

        results[n_words] = {
            "mean": mean,
            "p50": p50,
            "p95": p95,
            "p99": p99,
        }

        status = "PASS" if p95 <= P95_THRESHOLD_MS else "FAIL"
        print(
            f"\nInput size: {n_words:>5} words  [{status}]"
            f"\n  mean={mean:.2f}ms  p50={p50:.2f}ms  p95={p95:.2f}ms  p99={p99:.2f}ms"
            f"\n  threshold (p95 <= {P95_THRESHOLD_MS}ms): {'OK' if p95 <= P95_THRESHOLD_MS else 'EXCEEDED'}"
        )

    print("\n" + "=" * 60)
    print("Summary")
    print(f"{'words':>6}  {'mean':>8}  {'p50':>8}  {'p95':>8}  {'p99':>8}")
    print("-" * 50)
    for n_words, r in results.items():
        flag = "" if r["p95"] <= P95_THRESHOLD_MS else " *** ABOVE THRESHOLD ***"
        print(
            f"{n_words:>6}  {r['mean']:>7.2f}ms"
            f"  {r['p50']:>7.2f}ms"
            f"  {r['p95']:>7.2f}ms"
            f"  {r['p99']:>7.2f}ms{flag}"
        )
    print("=" * 60)

    # Exit non-zero if any p95 exceeds threshold
    any_fail = any(r["p95"] > P95_THRESHOLD_MS for r in results.values())
    if any_fail:
        print("\nWARNING: p95 threshold exceeded for one or more input sizes.")
        print("Update ADR 2026-04-22-5 with the measured values.")
        sys.exit(1)
    else:
        print("\nAll p95 measurements are within the 50 ms threshold.")


if __name__ == "__main__":
    main()

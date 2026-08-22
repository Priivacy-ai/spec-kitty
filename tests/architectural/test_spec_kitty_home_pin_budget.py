"""SC-007: NFR-001's budget, the enumerated-set criterion, and both parallel modes (T021).

**The wall-clock budget test in this module carries ``performance``, not ``architectural``.**
Per ADR 2026-08-22-1 the single-shot on-PR ``timing`` gate (``-m timing -n0``,
``timing-nfr-serial``) is retired for this test:
``test_the_guard_completes_inside_the_budget_on_three_warm_runs`` now measures via the
``pytest-benchmark`` ``benchmark.pedantic`` fixture and carries
``@pytest.mark.performance`` (env-gated off every PR/blocking run per ``tests/conftest.py``,
statistically compared against a committed per-domain baseline in the off-PR
``performance.yml`` pipeline — never a single-shot ceiling on a shared runner). The other three
tests in this module are correctness checks, not budget tests (ADR 2026-08-22-1's "stays on the
PR path" carve-out), and carry no timing/performance marker.

``time.perf_counter()``, never ``time.time()``
------------------------------------------------
``time.time()`` is in ``_BANNED_CALLS`` (``tests/_support/wall_clock_assertions.py:10-20``) and
``tests/conftest.py:245-250`` raises a ``pytest.UsageError`` **AT COLLECTION** — so the wrong clock
here does not fail this module, it takes the **whole suite** down. ``pytest-benchmark`` uses its
own internal timer (not a raw ``time.time()`` call inside an assert), so this scan is unaffected.

Why the enumerated set is compared against an INLINE ``rglob``
----------------------------------------------------------------
**The cheapest way to meet a wall-clock budget is to narrow the walk.** The seam exposes exactly
one enumerator, so the natural assertion is ``enumerate_py_files(root) == enumerate_py_files(root)``
— a self-comparison a narrowed walk passes. The expected set is therefore computed by a
``Path(root).rglob("*.py")`` **written inline below**, never obtained from the module under test.
This is why the anti-drift rule bans ``ast.parse`` and ``NodeVisitor`` in the guard modules but
explicitly does **not** ban ``rglob``.

It is a **tripwire**, not a discovery: today both sides are an ``rglob`` and the assertion is
trivially true. Its whole value is future-facing — the day someone adds ``if "node_modules" in
path.parts: continue`` to buy budget headroom, this reds. Per OD-003 the budget may be **RAISED**
against a recorded runner figure with the contention headroom stated; **the walk may NEVER be
narrowed.**

What this cannot see
--------------------
The guard under contention. The off-PR ``performance.yml`` pipeline measures it
**uncontended** while ``arch-adversarial`` runs the rest of this module's tests under ``-n
auto``, so the benchmark figure is a **FLOOR, not the worst case**.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tests.architectural import _home_pin_scan as scan
from tests.architectural._home_pin_verdict import hash_of_key_set

#: The real walk root, exactly as the shipped guard roots it.
TESTS_ROOT = Path("tests")

#: NFR-001's budget, in seconds, for one full pass of the guard's scan (nominal reference).
BUDGET_SECONDS = 6.0

#: Warm runs required inside the budget (SC-007).
WARM_RUNS = 3


@pytest.mark.performance
@pytest.mark.benchmark(group="core")
def test_the_guard_completes_inside_the_budget_on_three_warm_runs(
    benchmark: BenchmarkFixture,
) -> None:
    """SC-007 / NFR-001: warm runs measured statistically (ADR 2026-08-22-1).

    ``benchmark.pedantic`` mirrors the original shape: ``warmup_rounds=1`` discards the
    cold run (it pays the filesystem's cache miss, which is not what the budget is about),
    then ``WARM_RUNS`` rounds are measured individually. The regression signal is now the
    per-domain baseline compare in the off-PR ``performance.yml`` pipeline, not a
    single-shot ceiling — this test carries ``performance`` and is env-gated off every
    PR/blocking run per ``tests/conftest.py``.
    """
    benchmark.pedantic(
        lambda: scan.discover(TESTS_ROOT),
        rounds=WARM_RUNS,
        iterations=1,
        warmup_rounds=1,
    )

    # Very loose sanity ceiling — the statistical baseline compare (off the PR path) is the
    # primary regression signal, not this assert. Per OD-003 the budget may be RAISED
    # against a recorded runner figure with the contention headroom stated — the walk may
    # NEVER be narrowed, and the enumerated-set assertion below makes that impossible anyway.
    assert benchmark.stats.stats.max < BUDGET_SECONDS * 5, (
        f"the slowest warm run took {benchmark.stats.stats.max:.3f}s against a "
        f"{BUDGET_SECONDS}s nominal budget, wildly beyond the generous sanity ceiling."
    )


def test_the_enumerated_set_equals_an_inline_rglob() -> None:
    """SC-007: the walk is **never narrowed** — not by directory, not by filename (C-003).

    ``expected`` is an ``rglob`` written **here**, in the test. Obtaining it from the seam would
    make this a self-comparison, which a narrowed walk passes — and narrowing is exactly the repair
    a red budget invites.

    Set equality, count **REPORTED not asserted** (C-002): ``2737`` is stale the moment anyone adds
    a file, and this lane already measures a different number.
    """
    enumerated = {path.resolve() for path in scan.enumerate_py_files(TESTS_ROOT)}
    expected = {path.resolve() for path in Path(TESTS_ROOT).rglob("*.py")}

    missing = expected - enumerated
    extra = enumerated - expected
    assert enumerated == expected, (
        f"the walk does not match a plain rglob — missing {sorted(missing)[:5]}, "
        f"extra {sorted(extra)[:5]}. NFR-001 permits RAISING the budget and never narrowing."
    )
    print(f"[reported, not asserted] enumerated {len(enumerated)} .py files under {TESTS_ROOT}")


def test_the_enumerated_set_is_not_trivially_empty() -> None:
    """The instrument check for the assertion above.

    ``set() == set()`` is true, so an enumerator returning nothing and an ``rglob`` over a
    mistyped root would agree perfectly. This is what makes the equality above evidence.
    """
    enumerated = scan.enumerate_py_files(TESTS_ROOT)
    assert enumerated, f"{TESTS_ROOT} enumerated no .py files at all — the comparison proves nothing"
    assert all(path.suffix == ".py" for path in enumerated)


def test_the_class_is_deterministic_and_publishes_a_PROCESS_STABLE_digest() -> None:
    """NFR-003's in-process half, named for what it actually asserts.

    **This asserts determinism WITHIN one process. It does not, and cannot, compare two parallel
    modes from inside one of them.** NFR-003 is discharged by RUNNING this module under ``-n0`` and
    under ``-n auto --dist loadfile`` and comparing the digest below across the two runs; this test
    exists to give those runs something to disagree about beyond "the suite passed". The earlier
    name claimed the cross-mode comparison and the docstring alone disclosed otherwise.

    **The digest is process-stable, and that is the fix that makes the comparison possible at all.**
    It was ``hash(frozenset(...))``, which Python randomises per process via ``PYTHONHASHSEED`` — so
    two identical serial runs printed different digests for the same 40-member class and the
    cross-mode comparison was meaningless. It now comes from the seam's own ``render_baseline``
    key-set ``sha256`` (through the verdict seam's :func:`hash_of_key_set`), which is a content
    hash and reproducible across processes and machines.

    **Reading it under ``-n auto``**: xdist swallows worker stdout, so take the digest from the
    ``-n0`` leg, or pass ``-s``. Both legs are required by NFR-003 regardless; only the *printing*
    is mode-sensitive.
    """
    first = {(m.key, m.home_partition, m.kind) for m in scan.discover(TESTS_ROOT)}
    second = {(m.key, m.home_partition, m.kind) for m in scan.discover(TESTS_ROOT)}
    assert first == second, "the pass is not deterministic within a single process"
    assert first, "an empty class would make the determinism claim vacuous"

    digest = hash_of_key_set(frozenset(key for key, _partition, _kind in first))
    print(
        f"[reported, not asserted] members {len(first)}; key-set sha256 {digest}; "
        f"kinds {scan.kind_distribution(TESTS_ROOT)}; "
        f"partitions {_partition_counts(partition for _key, partition, _kind in first)}"
    )


def _partition_counts(partitions: Iterable[str]) -> dict[str, int]:
    """Partition tallies, published beside the key-set hash.

    The ``sha256`` covers only the KEY set — ``render_baseline`` hashes keys and nothing else — so
    a change to a member's ``home_partition`` or ``kind`` would leave it untouched. These two small
    distributions carry the other two axes across the mode comparison.
    """
    counts: dict[str, int] = {}
    for partition in partitions:
        counts[partition] = counts.get(partition, 0) + 1
    return dict(sorted(counts.items()))

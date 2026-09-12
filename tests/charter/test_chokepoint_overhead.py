"""NFR-002: chokepoint warm-overhead budget (<10 ms p95).

The chokepoint (``ensure_charter_bundle_fresh``) is invoked on every
charter-read in the dashboard's hot loop. The warm path — bundle present,
hashes match, no regeneration — must complete under 10 ms p95 with zero
``git`` invocations on the resolver path.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from charter.hasher import hash_content
from charter.activation.sync import ensure_charter_bundle_fresh
from tests._perf_helpers import assert_timing_budget

# Marked for mutmut sandbox skip — see ADR 2026-04-20-1.
# Reason: trampoline bug: subprocess
pytestmark = [pytest.mark.non_sandbox, pytest.mark.git_repo]


_SAMPLE_CHARTER = """# Testing Standards

## Coverage Requirements
- Minimum 80% code coverage

## Quality Gates
- Must pass linters

## Project Directives
1. Never commit secrets
"""


@pytest.fixture
def warm_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a fully-populated, already-fresh charter bundle inside a fresh git repo.

    Returns the canonical root path. consolidate-charter-bundle (IC-04 /
    WP04, T028c): ``sync()`` no longer writes/primes anything (manifest v2's
    ``derived_files`` is ``[]``) -- priming the WARM state now means seeding
    a ``metadata.yaml`` whose ``charter_hash`` already matches ``charter.md``,
    so ``ensure_charter_bundle_fresh``'s staleness check short-circuits to
    the true zero-write warm path on every call, which is exactly what this
    NFR-002 overhead budget measures.
    """
    repo = tmp_path_factory.mktemp("warm_bundle")
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True, capture_output=True)
    charter_dir = repo / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    charter_path = charter_dir / "charter.md"
    charter_path.write_text(_SAMPLE_CHARTER, encoding="utf-8")
    yaml = YAML()
    yaml.dump({"charter_hash": hash_content(_SAMPLE_CHARTER)}, charter_dir / "metadata.yaml")
    # Drop resolver cache so the first chokepoint call inside the test is
    # the one we measure with a clean cache state.
    from charter.resolution import resolve_canonical_repo_root

    resolve_canonical_repo_root.cache_clear()
    return repo


def test_warm_invocation_returns_result_without_resync(warm_bundle: Path) -> None:
    """Functional companion to test_warm_overhead_p95_under_10ms
    (split, #4015): a warm invocation returns a result and does not
    regenerate. Timing budget lives in the @performance sibling below."""
    # Prime the resolver cache + filesystem caches with one warm-up call.
    ensure_charter_bundle_fresh(warm_bundle)

    result = ensure_charter_bundle_fresh(warm_bundle)

    assert result is not None
    assert result.synced is False, "Warm path should not regenerate"


@pytest.mark.performance
def test_warm_overhead_p95_under_10ms(warm_bundle: Path) -> None:
    """NFR-002 timing budget only (split, #4015): 100 warm invocations,
    p95 latency < 10 ms. Functional coverage moved to
    test_warm_invocation_returns_result_without_resync, above."""
    # Prime the resolver cache + filesystem caches with one warm-up call.
    ensure_charter_bundle_fresh(warm_bundle)

    timings_ns: list[int] = []
    for _ in range(100):
        start = time.monotonic_ns()
        ensure_charter_bundle_fresh(warm_bundle)
        elapsed = time.monotonic_ns() - start
        timings_ns.append(elapsed)

    timings_ms = sorted(t / 1_000_000 for t in timings_ns)
    # p95 = the 95th percentile (index 94 of a 0-indexed sorted list of 100).
    p95 = timings_ms[94]
    assert_timing_budget(p95, 10, name="chokepoint_warm_p95_ms")


def test_warm_chokepoint_does_not_shell_out_to_git_on_cache_hit(warm_bundle: Path) -> None:
    """The resolver cache must absorb every warm chokepoint call."""
    # First call warms the resolver cache.
    ensure_charter_bundle_fresh(warm_bundle)

    with patch("kernel.git_topology.subprocess.run") as spy:
        result = ensure_charter_bundle_fresh(warm_bundle)
    assert result is not None
    assert result.synced is False
    assert spy.call_count == 0, (
        f"Warm chokepoint triggered {spy.call_count} git invocations; expected 0."
    )


def test_warm_chokepoint_returns_canonical_root(warm_bundle: Path) -> None:
    """The chokepoint always patches ``canonical_root`` onto the result."""
    result = ensure_charter_bundle_fresh(warm_bundle)
    assert result is not None
    assert result.canonical_root is not None
    assert result.canonical_root == warm_bundle.resolve()

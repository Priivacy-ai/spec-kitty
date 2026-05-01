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

from charter.sync import ensure_charter_bundle_fresh, sync

# Marked for mutmut sandbox skip — see ADR 2026-04-20-1.
# Reason: trampoline bug: subprocess
pytestmark = pytest.mark.non_sandbox


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
    """Build a fully-populated charter bundle inside a fresh git repo.

    Returns the canonical root path. After this fixture runs, every file
    declared in ``CANONICAL_MANIFEST.derived_files`` exists with hashes
    matching the source ``charter.md``.
    """
    repo = tmp_path_factory.mktemp("warm_bundle")
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True, capture_output=True)
    charter_dir = repo / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    charter_path = charter_dir / "charter.md"
    charter_path.write_text(_SAMPLE_CHARTER, encoding="utf-8")
    # Prime the bundle by running sync once.
    result = sync(charter_path, charter_dir, force=True)
    assert result.synced is True, f"Bundle priming failed: {result.error}"
    # Drop resolver cache so the first chokepoint call inside the test is
    # the one we measure with a clean cache state.
    from charter.resolution import resolve_canonical_repo_root

    resolve_canonical_repo_root.cache_clear()
    return repo


def test_warm_overhead_p95_under_10ms(warm_bundle: Path) -> None:
    """100 warm invocations: p95 latency < 10 ms (NFR-002)."""
    # Prime the resolver cache + filesystem caches with one warm-up call.
    ensure_charter_bundle_fresh(warm_bundle)

    timings_ns: list[int] = []
    for _ in range(100):
        start = time.monotonic_ns()
        result = ensure_charter_bundle_fresh(warm_bundle)
        elapsed = time.monotonic_ns() - start
        timings_ns.append(elapsed)
        assert result is not None
        assert result.synced is False, "Warm path should not regenerate"

    timings_ms = sorted(t / 1_000_000 for t in timings_ns)
    # p95 = the 95th percentile (index 94 of a 0-indexed sorted list of 100).
    p95 = timings_ms[94]
    assert p95 < 10, (
        f"Chokepoint warm p95 = {p95:.2f}ms (budget: 10ms). "
        f"Timings (ms): min={timings_ms[0]:.2f}, "
        f"p50={timings_ms[49]:.2f}, p95={p95:.2f}, max={timings_ms[-1]:.2f}"
    )


def test_warm_chokepoint_does_not_shell_out_to_git_on_cache_hit(warm_bundle: Path) -> None:
    """The resolver cache must absorb every warm chokepoint call."""
    # First call warms the resolver cache.
    ensure_charter_bundle_fresh(warm_bundle)

    with patch("charter.resolution.subprocess.run") as spy:
        result = ensure_charter_bundle_fresh(warm_bundle)
    assert result is not None
    assert result.synced is False
    assert spy.call_count == 0, f"Warm chokepoint triggered {spy.call_count} git invocations; expected 0."


def test_warm_chokepoint_returns_canonical_root(warm_bundle: Path) -> None:
    """The chokepoint always patches ``canonical_root`` onto the result."""
    result = ensure_charter_bundle_fresh(warm_bundle)
    assert result is not None
    assert result.canonical_root is not None
    assert result.canonical_root == warm_bundle.resolve()

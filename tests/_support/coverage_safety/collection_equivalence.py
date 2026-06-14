"""Collection-equivalence helper (T005, C-EQUIV, FR-004, NFR-007, E3).

Prove that a shard collects the *exact same* nodeid set serially and under
``-n auto --dist loadfile``. The acceptance check for C-EQUIV is:

    pytest <shard> --collect-only -q          (serial)
    pytest <shard> --collect-only -q -n auto --dist loadfile   (parallel)

must yield identical nodeid sets. :func:`assert_equivalent` raises with the
symmetric difference on any mismatch so a flip that silently drops or adds a
nodeid cannot merge (E3/I1). An intended count change must be asserted
explicitly with a reviewed delta (E3/I2) — this helper never hides one.

The helpers are pure (no shared module state): each call shells out to a fresh
``pytest --collect-only`` subprocess and parses its ``-q`` output. Self-tests
scope to a tiny fixture dir, never the real suite (Risks & Mitigations).
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence

__all__ = [
    "CollectionEquivalenceError",
    "assert_equivalent",
    "collect_nodeids",
]

# Lines emitted by ``pytest --collect-only -q`` that are not nodeids. The quiet
# reporter prints a trailing summary like ``"12 tests collected in 0.03s"`` and
# may emit blank lines, warnings, or ``"no tests ran"`` — none are nodeids.
_SUMMARY_MARKERS = (
    "tests collected",
    "test collected",
    "tests ran",
    "no tests ran",
    "deselected",
    "error",
    "warning",
    "errors",
    "warnings",
)


class CollectionEquivalenceError(AssertionError):
    """Raised when serial and parallel collection disagree.

    Subclasses :class:`AssertionError` so it reads as a test failure while
    still being catchable as a distinct type by callers that want to inspect
    :attr:`only_serial` / :attr:`only_parallel`.
    """

    def __init__(
        self,
        only_serial: frozenset[str],
        only_parallel: frozenset[str],
    ) -> None:
        self.only_serial = only_serial
        self.only_parallel = only_parallel
        parts = [
            "Collection equivalence failed (C-EQUIV / FR-004): serial and "
            "parallel collection collected different nodeid sets.",
        ]
        if only_serial:
            parts.append(
                "  Missing under parallel (collected serially only):\n"
                + "\n".join(f"    - {nid}" for nid in sorted(only_serial))
            )
        if only_parallel:
            parts.append(
                "  Extra under parallel (collected in parallel only):\n"
                + "\n".join(f"    + {nid}" for nid in sorted(only_parallel))
            )
        parts.append(
            "  Any intended count change must be asserted explicitly with a "
            "reviewed delta (NFR-007 / E3 I2), never left silent."
        )
        super().__init__("\n".join(parts))


def _looks_like_nodeid(line: str) -> bool:
    """Return True if *line* is a pytest nodeid (not a summary/warning line)."""
    stripped = line.strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    if any(marker in lowered for marker in _SUMMARY_MARKERS):
        return False
    # A nodeid always references a path::test or at minimum a collected path.
    # The quiet collect reporter prints one nodeid per line with no leading
    # whitespace; summary lines are the only other content and are filtered
    # above. Require a path-like token to be safe.
    return "::" in stripped or "/" in stripped or stripped.endswith(".py")


def collect_nodeids(args: Sequence[str]) -> set[str]:
    """Collect the nodeid set pytest would run for *args*.

    Runs ``pytest --collect-only -q`` (plus *args*) in a subprocess and parses
    the printed nodeids. *args* is the shard selector: paths, ``-m`` marker
    expressions, ``-k`` filters, and/or parallel flags (``-n auto
    --dist loadfile``) — collection is identical whether or not workers run, so
    passing the parallel flags here exercises the same selection path CI uses.

    Returns a set of nodeid strings. Raises :class:`RuntimeError` if pytest
    exits with a hard collection error (exit code >= 2), surfacing stderr.
    """
    completed = subprocess.run(  # noqa: S603 — args are caller-supplied test selectors, not shell input
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    # pytest exit codes: 0 = collected & ok, 1 = tests failed (n/a for
    # collect-only), 5 = no tests collected, >=2 = usage/collection error.
    if completed.returncode not in (0, 5):
        raise RuntimeError(
            "pytest --collect-only failed for "
            f"args={list(args)!r} (exit {completed.returncode}).\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return {
        line.strip()
        for line in completed.stdout.splitlines()
        if _looks_like_nodeid(line)
    }


def assert_equivalent(
    serial_args: Sequence[str],
    parallel_args: Sequence[str],
) -> None:
    """Assert serial and parallel selections collect the identical nodeid set.

    *serial_args* is the shard selector without parallel flags; *parallel_args*
    is the same selector plus ``-n auto --dist loadfile`` (the caller composes
    both). On mismatch, raises :class:`CollectionEquivalenceError` naming the
    symmetric difference (the missing/extra nodeids), satisfying C-EQUIV /
    E3 I1. On match, returns ``None``.
    """
    serial = collect_nodeids(serial_args)
    parallel = collect_nodeids(parallel_args)
    if serial != parallel:
        raise CollectionEquivalenceError(
            only_serial=frozenset(serial - parallel),
            only_parallel=frozenset(parallel - serial),
        )

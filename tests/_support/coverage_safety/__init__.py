"""Coverage-safety harness (WP02, mission test-suite-acceleration).

Reusable, pure/deterministic safeguards that let every later test reduction or
parallelization flip be *proven* coverage-neutral:

* :mod:`collection_equivalence` — prove a shard collects the identical nodeid
  set serially and under ``-n auto --dist loadfile`` (C-EQUIV, FR-004, E3).
* :mod:`ratchet` — accept a flip only after N consecutive green parallel runs
  (C-RATCHET, FR-012, NFR-005, E4).
* :mod:`equivalence` — prove a collapsed/parametrized test still catches a
  planted regression (anti-vacuity; C-001).

The architectural guard ``tests/architectural/test_real_home_isolation_guard.py``
consumes these conventions but lives outside this package (it is the one
architectural test WP02 owns).
"""

from __future__ import annotations

from .collection_equivalence import (
    CollectionEquivalenceError,
    assert_equivalent,
    collect_nodeids,
)
from .equivalence import (
    MutationNotCaughtError,
    Mutation,
    assert_mutation_caught,
)
from .ratchet import RatchetResult, RunOutcome, run_ratchet

__all__ = [
    "CollectionEquivalenceError",
    "Mutation",
    "MutationNotCaughtError",
    "RatchetResult",
    "RunOutcome",
    "assert_equivalent",
    "assert_mutation_caught",
    "collect_nodeids",
    "run_ratchet",
]

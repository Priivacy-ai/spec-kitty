"""Single-source fixed-range real-port test-family registry (data-model E2).

Mission ``ci-test-topology-performance-01KXBJRT`` WP03 (FR-004 / GC-3). Several
``tests/sync/*.py`` files bind ``find_free_port_in_range`` (either directly, via
``tests.sync._daemon_harness``, or through a local re-implementation) to spawn
real loopback daemon subprocesses on a fixed, reserved port range. OS-global
port binds are NOT protected by per-worker HOME isolation, so every file in
this family must run serially (``-n0``) — never inside an xdist ``-n auto`` /
``-n <N>`` parallel pool, which could scatter concurrent binds onto the same
port across workers.

How this list was verified (re-run this to extend/re-check the family)::

    grep -rl "find_free_port_in_range" tests/sync/*.py

As of this mission that grep returns 5 files: ``_daemon_harness.py`` itself
(the shared helper, not a test file — excluded), and the 4 test files listed
in ``FIXED_RANGE_SUITES`` below, each binding the fixed range either via the
harness's re-exported helper or (``test_orphan_sweep.py``) a local
``_find_free_port_in_range`` re-implementation of the same fixed-range scan.

Exclusion note — ephemeral (port-0) binders stay OUT of this registry
------------------------------------------------------------------
A test that lets the OS pick an arbitrary free port (e.g. binding to port
``0``, or a bare ``DaemonHarness`` call with no fixed range) is deliberately
parallel-safe: the OS guarantees a distinct ephemeral port per bind, so
concurrent xdist workers cannot collide. Registering such a test here would
force it needlessly serial, undermining the FR-006 parallelization goal this
mission is chasing. Only *fixed-range* binders — where the range is a shared,
reserved, cross-suite constant an unlucky concurrent worker could also land
on — belong in ``FIXED_RANGE_SUITES``.

Consumed by ``tests/architectural/test_serial_port_preservation.py`` (GC-3)
and ``tests/architectural/test_workflow_dist_lint.py`` (GC-4). This module is
pure data — no pytest import, no side effects — so it stays trivially
unit-testable and reviewable as "just a table," matching ``tests/
_arch_shard_map.py``'s discipline. Keep this registry independent of
``tests/_arch_shard_map.py`` / ``tests/_next_shard_map.py``: those encode a
sharding invariant, this one encodes a serial-isolation invariant — do not
merge the two.
"""

from __future__ import annotations

# Verified via `grep -rl find_free_port_in_range tests/sync/*.py` (see module
# docstring for the exact command and its current 5-file result, minus the
# shared harness module itself which is not a test file).
FIXED_RANGE_SUITES: tuple[str, ...] = (
    "tests/sync/test_orphan_sweep.py",
    "tests/sync/test_daemon_orphan_classification.py",
    "tests/sync/test_daemon_cleanup_boundary.py",
    "tests/sync/test_issue_1071_singleton_reconfirmation.py",
)

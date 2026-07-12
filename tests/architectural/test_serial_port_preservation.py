"""FR-011 / FR-004 — real-port fixed-range family serial-pass preservation invariant.

Mission ``ci-topology-shrink-01KWQAVX`` WP02 introduced this guard red-first for
the single ``tests/sync/test_orphan_sweep.py`` file. Mission
``ci-test-topology-performance-01KXBJRT`` WP03 (GC-3, data-model E2)
generalizes it to the **whole** fixed-range ``find_free_port_in_range`` daemon
family (``tests._real_port_suites.FIXED_RANGE_SUITES``) — every file that binds
the shared, reserved, fixed port range, not just ``test_orphan_sweep.py``.
OS-global port binds are NOT protected by per-worker HOME isolation, so none of
these files may ever run inside an xdist *parallel* pool. This asserts, over
the parsed workflow run scripts, that for **every** family member and on every
job touching the sync suite:

* no **parallel** (``-n auto`` / ``-n <N>``) command collects that family
  member (it is either excluded via ``--ignore`` or the command runs
  serially); and
* a **serial** command still runs that family member somewhere across the
  whole workflow set (the serial ``-n0`` pass is preserved, not silently
  dropped); and
* no command uses bare ``--dist load`` anywhere — parallel distribution is
  always ``--dist loadfile`` (bare ``load`` scatters a file's tests across
  workers and breaks file-scoped fixtures).

FR-011/FR-004 preservation is a "could pass vacuously" relation, so
fault-injection tests prove it BITES if a split were to run any family member
in parallel, drop the serial pass, or use bare ``--dist load``.

**Closed gap (was tracked at https://github.com/Priivacy-ai/spec-kitty/issues/2590):**
``fast-tests-sync``'s parallel step used to structurally ``--ignore`` only
``test_orphan_sweep.py``; the other 3 family members were excluded from that
job's *selection* solely by their module-level ``pytest.mark.integration``
marker not matching the job's ``-m "fast and not windows_ci"`` filter — a
marker-only guarantee, not a structural one. Widening this guard to the whole
family (WP03) made that gap visible; mission
ci-test-topology-performance-01KXBJRT WP06 (owns
``.github/workflows/ci-quality.yml``, sequenced after this WP precisely so the
guard existed first — freeze-before-change) closed it by adding explicit
``--ignore=`` entries for the other 3 members to that same step, and to the
newly-split ``integration-tests-sync`` residual.

The xdist ``-n`` / ``--dist`` flags are NOT part of the WP01 model, so this test
parses the raw workflow run scripts directly (a new relation, not a
re-derivation of the bound model).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests._real_port_suites import FIXED_RANGE_SUITES
from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_CMD_PREVIEW = 130

_PARALLEL_RE = re.compile(r"-n\s*(?:auto|[1-9]\d*)")
_BARE_LOAD_RE = re.compile(r"--dist\s+load(?!file)")
_IGNORE_VALUE_RE = re.compile(r"--ignore=(\S+)")
# Sync-suite positional scope: a family file itself, or the ``tests/sync``
# directory (NOT the whole ``tests/`` tree — a whole-tree run relies on markers
# to skip the family, which a purely path-based scan cannot see; the real
# FR-011/FR-004 risk is a sync-targeted shard, and this family's members all
# live under ``tests/sync``).
_SYNC_DIR_RE = re.compile(r"(?<![\w/])tests/sync/?(?=\s|\\|$)")
# Whole-tree positional (``tests`` or ``tests/`` as a bare positional, NOT
# ``tests/sync`` etc, and NOT an ``--ignore=tests...`` value — the ``=``/``/``
# lookbehind excludes those). A whole-tree ``-n auto`` run CAN marker-select a
# family member (e.g. ``unit``-marked ``test_orphan_sweep.py``), which the
# path-based per-member ``_covers_member_scope`` cannot see; such runs are held
# to a structural require-all-ignored rule in ``serial_port_violations``.
_WHOLE_TREE_RE = re.compile(r"(?<![\w/=])tests/?(?=\s|\\|$)")


def _is_parallel(cmd: str) -> bool:
    return bool(_PARALLEL_RE.search(cmd))


def _is_whole_tree_scope(cmd: str) -> bool:
    """The command's positional scope is the whole ``tests/`` tree."""
    return bool(_WHOLE_TREE_RE.search(cmd))


def _uses_bare_load(cmd: str) -> bool:
    return bool(_BARE_LOAD_RE.search(cmd))


def _ignores_member(cmd: str, member: str) -> bool:
    """The command ``--ignore``s ``member`` itself or an ancestor directory of it."""
    for raw in _IGNORE_VALUE_RE.findall(cmd):
        ignore = raw.strip("'\"").replace("\\", "/").rstrip("/")
        if ignore == member or member.startswith(f"{ignore}/"):
            return True
    return False


def _covers_member_scope(cmd: str, member: str) -> bool:
    """The command's positional scope would collect ``member``."""
    return member in cmd or bool(_SYNC_DIR_RE.search(cmd))


def _collects_member(cmd: str, member: str) -> bool:
    """The command actually runs ``member`` (in scope and not ignored)."""
    return _covers_member_scope(cmd, member) and not _ignores_member(cmd, member)


def serial_port_violations(commands: list[str]) -> list[str]:
    """FR-011/FR-004 violations over the whole workflow command set (pure — fault-injectable).

    The serial-pass guarantee is GLOBAL and PER-MEMBER: a family file may live in
    a serial pass of a different job than a parallel catch-all that excludes it,
    and each ``FIXED_RANGE_SUITES`` entry is checked independently — so
    ``commands`` is every pytest command across the suite, not one job's, and
    the registry is iterated in full (not just its first entry).
    """
    if not any("tests/sync" in cmd or _is_whole_tree_scope(cmd) for cmd in commands):
        return []
    violations: list[str] = []
    for cmd in commands:
        if _uses_bare_load(cmd):
            violations.append(f"bare --dist load (use loadfile): {cmd.strip()[:_CMD_PREVIEW]}")
        # Whole-tree parallel run: a family member may be marker-SELECTED here
        # (a path-based per-member scan cannot evaluate ``-m``), so require every
        # member be structurally ``--ignore``d regardless of markers.
        if _is_parallel(cmd) and _is_whole_tree_scope(cmd):
            for member in FIXED_RANGE_SUITES:
                if not _ignores_member(cmd, member):
                    violations.append(
                        f"whole-tree parallel run does not --ignore {member}: "
                        f"{cmd.strip()[:_CMD_PREVIEW]}",
                    )
    for member in FIXED_RANGE_SUITES:
        for cmd in commands:
            if _is_parallel(cmd) and _collects_member(cmd, member):
                violations.append(f"{member} in parallel pool: {cmd.strip()[:_CMD_PREVIEW]}")
        if not any(_collects_member(cmd, member) and not _is_parallel(cmd) for cmd in commands):
            violations.append(f"no serial (unparallelized) pass runs {member} anywhere")
    return violations


def _pytest_commands(script: str) -> list[str]:
    """Continuation-joined logical lines of ``script`` that invoke pytest."""
    return [
        line
        for line in gc.join_continuations(script)
        if "pytest" in line and not line.lstrip().startswith("#")
    ]


def _job_commands() -> dict[str, list[str]]:
    """``workflow::job`` -> its pytest command lines across all suite workflows."""
    by_job: dict[str, list[str]] = {}
    for name in gc.WORKFLOW_FILES:
        data: dict[str, Any] = yaml.safe_load(
            (gc.WORKFLOWS_DIR / name).read_text(encoding="utf-8"),
        )
        for job_name, job in (data.get("jobs") or {}).items():
            commands: list[str] = []
            for step in job.get("steps") or []:
                if isinstance(step, dict) and "run" in step:
                    commands.extend(_pytest_commands(str(step["run"])))
            if commands:
                by_job[f"{name}::{job_name}"] = commands
    return by_job


def test_at_least_one_job_runs_the_daemon_test() -> None:
    """Anti-vacuous canary: some job runs SOME real-port family member.

    Asserts the workflow parse actually inspected at least one job's pytest
    commands (``> 0``) so an empty/broken parse cannot pass this scan green by
    finding nothing to check.
    """
    jobs = _job_commands()
    assert jobs, "workflow parse found zero jobs with pytest commands — scan would be vacuous"
    running = [
        label
        for label, commands in jobs.items()
        if any(member in cmd for member in FIXED_RANGE_SUITES for cmd in commands)
    ]
    assert running, (
        f"no job references any of {FIXED_RANGE_SUITES} — FR-011/FR-004 scan would be vacuous"
    )


def test_no_daemon_run_in_parallel_and_serial_pass_preserved() -> None:
    """The suite must exclude the whole real-port family from every parallel pool.

    ``fast-tests-core-misc`` excludes ``tests/sync`` from its ``-n auto`` pool
    entirely, and ``fast-tests-sync``'s parallel step structurally ``--ignore``s
    ``test_orphan_sweep.py`` and runs it in a dedicated ``-n0`` pass — that part
    was already GREEN.

    CLOSED (was tracked at https://github.com/Priivacy-ai/spec-kitty/issues/2590):
    that same parallel step now structurally ``--ignore``s the other 3
    ``FIXED_RANGE_SUITES`` members too (mission
    ci-test-topology-performance-01KXBJRT WP06, which owns ``ci-quality.yml``)
    — previously they were excluded from its *selection* only by a
    ``pytest.mark.integration`` marker not matching the job's ``-m "fast and
    not windows_ci"`` filter, a marker-only guarantee this structural
    (``--ignore``-based) guard could not see. WP06 also split
    ``integration-tests-sync`` real-port-first (its own parallel residual now
    structurally ``--ignore``s all 4 members, with a dedicated serial
    ``-n0`` job running them instead), so the whole family stays live-green
    across every job that touches ``tests/sync``.

    The whole-tree ``-n auto`` job (``unit-contract-residual``) is also held to
    the structural require-all-ignored rule — ``test_orphan_sweep.py`` is
    ``unit``-marked and would otherwise be marker-selected into that pool
    (invisible to the per-member path scan). See
    ``test_relation_bites_on_whole_tree_parallel_without_family_ignore``.
    """
    all_commands = [cmd for commands in _job_commands().values() for cmd in commands]
    violations = serial_port_violations(all_commands)
    assert not violations, f"FR-011/FR-004 serial-port violations: {violations}"


def test_relation_bites_on_daemon_in_parallel_pool() -> None:
    """Fault-injection: the checker flags a daemon test in a ``-n auto`` pool."""
    commands = [
        "uv run python -m pytest tests/sync/ -m 'not windows_ci' -n auto --dist loadfile",
    ]
    assert serial_port_violations(commands), (
        "checker missed a daemon test running in a parallel pool"
    )


def test_relation_bites_on_dropped_serial_pass() -> None:
    """Fault-injection: the checker flags a dropped serial pass after exclusion."""
    daemon_test = FIXED_RANGE_SUITES[0]
    commands = [
        "pytest tests/sync/ -n auto --ignore=" + daemon_test + " --dist loadfile",
    ]
    assert serial_port_violations(commands), (
        "checker missed a daemon test excluded from parallel with no serial pass"
    )


def test_relation_bites_on_bare_dist_load() -> None:
    """Fault-injection: the checker flags bare ``--dist load`` (never loadfile)."""
    daemon_test = FIXED_RANGE_SUITES[0]
    commands = [
        "pytest " + daemon_test + " -n0",
        "pytest tests/sync/ -n auto --ignore=" + daemon_test + " --dist load",
    ]
    assert any("bare --dist load" in v for v in serial_port_violations(commands)), (
        "checker missed a bare --dist load invocation"
    )


def test_relation_bites_on_non_orphan_sweep_family_member_in_parallel_pool() -> None:
    """T011 fault-injection: the guard bites for a family member OTHER than
    ``test_orphan_sweep.py`` — closing the gap where earlier fault-injection
    cases only ever referenced the one hardcoded file.
    """
    other_member = next(m for m in FIXED_RANGE_SUITES if "orphan_sweep" not in m)
    commands = [
        f"uv run python -m pytest {other_member} -n auto --dist loadfile",
    ]
    violations = serial_port_violations(commands)
    assert any(other_member in v for v in violations), (
        f"checker missed {other_member} running in a parallel pool"
    )


def test_relation_does_not_over_fire_on_ephemeral_port_binder_in_parallel_pool() -> None:
    """Inverse micro-check (T011): a parallel-safe test, NOT in the fixed-range
    registry, running under ``-n auto`` must NOT be flagged as a family-member
    violation — the guard must not over-fire on parallel-safe tests.

    ``test_daemon_singleton.py`` never binds a real socket (it drives
    ``scan_sync_daemons`` off a fixture-written state file), so it is the
    real-file stand-in for a parallel-safe (ephemeral/no-bind) test that must
    stay outside ``FIXED_RANGE_SUITES``.
    """
    ephemeral_test = "tests/sync/test_daemon_singleton.py"
    assert ephemeral_test not in FIXED_RANGE_SUITES
    commands = [
        f"uv run python -m pytest {ephemeral_test} -n auto --dist loadfile",
    ]
    violations = serial_port_violations(commands)
    assert not any(ephemeral_test in v for v in violations), (
        f"checker over-fired on ephemeral (non-family) test {ephemeral_test}: {violations}"
    )


def test_relation_bites_on_whole_tree_parallel_without_family_ignore() -> None:
    """Fault-injection: a WHOLE-TREE ``-n auto`` run that does not ``--ignore``
    the fixed-range family is flagged — the ``unit-contract-residual`` class the
    per-member path scan is blind to (``test_orphan_sweep.py`` is ``unit``-marked,
    so ``-m "... and not integration"`` does not deselect it).
    """
    commands = [
        'uv run python -m pytest tests/ -m "(unit or contract) and not integration" '
        "-n auto --dist loadfile",
    ]
    violations = serial_port_violations(commands)
    assert any("whole-tree parallel run does not --ignore" in v for v in violations), (
        "checker missed a whole-tree -n auto run that does not --ignore the real-port family"
    )


_FIXED_RANGE_BINDER = "find_free_port_in_range"


def _fixed_range_binders_in_source() -> set[str]:
    """Every pytest-collected ``tests/sync/test_*.py`` that binds the fixed range.

    Implements the recipe ``tests/_real_port_suites.py`` documents
    (``grep -rl find_free_port_in_range tests/sync/*.py``), restricted to
    ``test_*.py`` — non-collected helpers (e.g. the ``_daemon_harness.py``
    provider that *defines* the binder) cannot be scattered onto a parallel
    pool, so they are correctly outside the registry.
    """
    sync_dir = Path(__file__).resolve().parents[1] / "sync"
    return {
        f"tests/sync/{p.name}"
        for p in sorted(sync_dir.glob("test_*.py"))
        if _FIXED_RANGE_BINDER in p.read_text(encoding="utf-8")
    }


def test_fixed_range_registry_matches_source_grep() -> None:
    """Completeness: ``FIXED_RANGE_SUITES`` == every collected ``tests/sync``
    test that binds the fixed range.

    Closes the registry's drift class by construction: a new fixed-range binder
    added to the tree but forgotten from ``FIXED_RANGE_SUITES`` (hence NOT
    ``--ignore``d from ``-n auto`` pools, reintroducing the OS-global
    port-collision hazard) REDS here instead of silently passing the workflow-
    side guards, which only iterate members already in the registry. (Residual:
    a binder using a differently-named helper is outside the documented
    ``find_free_port_in_range`` recipe — same limitation as the recipe itself.)
    """
    source = _fixed_range_binders_in_source()
    registry = set(FIXED_RANGE_SUITES)
    assert source, "source grep found zero fixed-range binders — guard would be vacuous"
    missing = source - registry
    stale = registry - source
    assert not missing, (
        f"fixed-range binders missing from FIXED_RANGE_SUITES (add them, else they run "
        f"un-ignored under -n auto): {sorted(missing)}"
    )
    assert not stale, (
        f"FIXED_RANGE_SUITES entries no longer bind the fixed range (stale): {sorted(stale)}"
    )


def test_relation_does_not_over_fire_on_whole_tree_parallel_with_all_ignored() -> None:
    """Inverse: a whole-tree ``-n auto`` run that structurally ``--ignore``s every
    family member (the fixed ``unit-contract-residual`` shape) is NOT flagged.
    """
    ignores = " ".join(f"--ignore={m}" for m in FIXED_RANGE_SUITES)
    commands = [
        f'uv run python -m pytest tests/ -m "unit or contract" {ignores} '
        "-n auto --dist loadfile",
        # serial passes so the "no serial pass" arm stays green for this micro-check
        *[f"pytest {m} -n0" for m in FIXED_RANGE_SUITES],
    ]
    violations = serial_port_violations(commands)
    assert not any("whole-tree parallel run does not --ignore" in v for v in violations), (
        f"checker over-fired on a whole-tree run that ignores the whole family: {violations}"
    )

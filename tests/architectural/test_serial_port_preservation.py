"""FR-011 — daemon / real-port serial-pass preservation invariant.

Mission ``ci-topology-shrink-01KWQAVX`` WP02 (red-first). ``tests/sync/
test_orphan_sweep.py`` binds the reserved daemon port range 9400-9449; OS-global
port binds are NOT protected by per-worker HOME isolation, so it must never run
inside an xdist *parallel* pool. This asserts, over the parsed workflow run
scripts, that on every job touching the sync suite:

* no **parallel** (``-n auto`` / ``-n <N>``) command collects the daemon test
  (it is either excluded via ``--ignore`` or the command runs serially); and
* if a parallel pool excludes the daemon test, a **serial** command still runs
  it (the serial ``-n0`` pass is preserved, not silently dropped); and
* no command uses bare ``--dist load`` — parallel distribution is always
  ``--dist loadfile`` (bare ``load`` scatters a file's tests across workers and
  breaks file-scoped fixtures).

FR-011 preservation is GREEN on today's topology (``fast-tests-sync`` excludes
the daemon test from its ``-n auto`` pool and runs a dedicated ``-n0`` pass;
``integration-tests-sync`` runs the sync suite serially). The invariant is a
"could pass vacuously" relation, so a fault-injection test proves it BITES if a
split were to run the daemon test in parallel, drop the serial pass, or use bare
``--dist load``.

The xdist ``-n`` / ``--dist`` flags are NOT part of the WP01 model, so this test
parses the raw workflow run scripts directly (a new relation, not a
re-derivation of the bound model).
"""

from __future__ import annotations

import re
from typing import Any

import pytest
import yaml

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_DAEMON_TEST = "tests/sync/test_orphan_sweep.py"
_CMD_PREVIEW = 130

_PARALLEL_RE = re.compile(r"-n\s*(?:auto|[1-9]\d*)")
_BARE_LOAD_RE = re.compile(r"--dist\s+load(?!file)")
_IGNORE_VALUE_RE = re.compile(r"--ignore=(\S+)")
# Sync-suite positional scope: the daemon file, or the ``tests/sync`` directory
# (NOT the whole ``tests/`` tree — a whole-tree run relies on markers to skip the
# daemon test, which a purely path-based scan cannot see; the real FR-011 risk is
# a sync-targeted shard, and WP03's split carves exactly those).
_SYNC_DIR_RE = re.compile(r"(?<![\w/])tests/sync/?(?=\s|\\|$)")


def _is_parallel(cmd: str) -> bool:
    return bool(_PARALLEL_RE.search(cmd))


def _uses_bare_load(cmd: str) -> bool:
    return bool(_BARE_LOAD_RE.search(cmd))


def _ignores_daemon(cmd: str) -> bool:
    """The command ``--ignore``s the daemon test or an ancestor directory of it."""
    for raw in _IGNORE_VALUE_RE.findall(cmd):
        ignore = raw.strip("'\"").replace("\\", "/").rstrip("/")
        if ignore == _DAEMON_TEST or _DAEMON_TEST.startswith(f"{ignore}/"):
            return True
    return False


def _covers_daemon_scope(cmd: str) -> bool:
    """The command's positional scope would collect the daemon test file."""
    return _DAEMON_TEST in cmd or bool(_SYNC_DIR_RE.search(cmd))


def _collects_daemon(cmd: str) -> bool:
    """The command actually runs the daemon test (in scope and not ignored)."""
    return _covers_daemon_scope(cmd) and not _ignores_daemon(cmd)


def serial_port_violations(commands: list[str]) -> list[str]:
    """FR-011 violations over the whole workflow command set (pure — fault-injectable).

    The serial-pass guarantee is GLOBAL: the daemon test may live in a serial pass
    of a different job (``fast-tests-sync``) than a parallel catch-all that excludes
    it (``fast-tests-core-misc``), so ``commands`` is every pytest command across
    the suite, not one job's.
    """
    if not any("tests/sync" in cmd for cmd in commands):
        return []
    violations: list[str] = []
    for cmd in commands:
        if _is_parallel(cmd) and _collects_daemon(cmd):
            violations.append(f"daemon test in parallel pool: {cmd.strip()[:_CMD_PREVIEW]}")
        if _uses_bare_load(cmd):
            violations.append(f"bare --dist load (use loadfile): {cmd.strip()[:_CMD_PREVIEW]}")
    if not any(_collects_daemon(cmd) and not _is_parallel(cmd) for cmd in commands):
        violations.append("no serial (unparallelized) pass runs the daemon test anywhere")
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
    """Guard against a vacuous scan: some job runs the real-port daemon suite."""
    running = [
        label
        for label, commands in _job_commands().items()
        if any(_DAEMON_TEST in cmd for cmd in commands)
    ]
    assert running, f"no job references {_DAEMON_TEST} — FR-011 scan would be vacuous"


def test_no_daemon_run_in_parallel_and_serial_pass_preserved() -> None:
    """GREEN today: the suite excludes the daemon test from every parallel pool.

    ``fast-tests-core-misc`` excludes ``tests/sync`` from its ``-n auto`` pool and
    ``fast-tests-sync`` runs the daemon test in a dedicated ``-n0`` pass — so no
    parallel command collects it and the serial pass is preserved (evaluated
    globally across every job's pytest commands).
    """
    all_commands = [cmd for commands in _job_commands().values() for cmd in commands]
    violations = serial_port_violations(all_commands)
    assert not violations, f"FR-011 serial-port violations: {violations}"


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
    commands = [
        "pytest tests/sync/ -n auto --ignore=" + _DAEMON_TEST + " --dist loadfile",
    ]
    assert serial_port_violations(commands), (
        "checker missed a daemon test excluded from parallel with no serial pass"
    )


def test_relation_bites_on_bare_dist_load() -> None:
    """Fault-injection: the checker flags bare ``--dist load`` (never loadfile)."""
    commands = [
        "pytest tests/sync/test_orphan_sweep.py -n0",
        "pytest tests/sync/ -n auto --ignore=" + _DAEMON_TEST + " --dist load",
    ]
    assert any("bare --dist load" in v for v in serial_port_violations(commands)), (
        "checker missed a bare --dist load invocation"
    )

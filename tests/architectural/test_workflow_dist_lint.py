"""GC-4 — workflow-distribution lint (C-001/C-002/C-006/C-007).

Mission ``ci-test-topology-performance-01KXBJRT`` WP04. A single committed
enforcement point over ``.github/workflows/*.yml`` so every future job edit
either satisfies these four invariants or fails CI, instead of each per-job
WP06 topology edit re-proving distribution correctness ad hoc:

* **C-001** — no run-script uses bare ``--dist load`` (it scatters a file's
  tests across xdist workers and breaks file-scoped fixtures); parallel
  distribution is always ``--dist loadfile``.
* (structural corollary of C-001) — every run-script that requests
  ``-n auto`` also pairs it with ``--dist loadfile`` in the *same* command.
* **C-002/C-007** — the fixed-range real-port daemon family
  (``tests._real_port_suites.FIXED_RANGE_SUITES``, owned by WP03/GC-3) is
  never *collected* under an ``-n auto`` pool. This module imports that
  registry rather than re-deriving a second list (canonical-sources /
  D-044 unification).
* **C-006** — every job that declares a ``strategy.matrix`` sets
  ``fail-fast: false`` structurally on the job mapping (not a regex over
  run-script text — ``fail-fast`` is a YAML field on ``strategy:``, absent
  defaults to ``true`` in GitHub Actions, so "field missing" must fail this
  exactly like "field explicitly true").

**Closed gap (was tracked at https://github.com/Priivacy-ai/spec-kitty/issues/2590,
see ``tests/architectural/test_serial_port_preservation.py`` for the identical
finding under GC-3):** ``fast-tests-sync``'s ``-n auto`` step used to
structurally ``--ignore`` only ``tests/sync/test_orphan_sweep.py``; the other
three ``FIXED_RANGE_SUITES`` members were excluded from that job's *selection*
only by their module-level ``pytest.mark.integration`` marker not matching the
job's ``-m "fast and not windows_ci"`` filter — a marker-only guarantee, not a
structural (``--ignore``-based) one this purely-structural scan could see.
Mission ci-test-topology-performance-01KXBJRT WP06 (owns
``.github/workflows/ci-quality.yml``) closed it by adding explicit
``--ignore=`` entries for the other three members to both ``fast-tests-sync``
and the newly-split ``integration-tests-sync`` — the C-002/C-007 live check
below is now live-green (the ``xfail`` this WP06 landing was sequenced to
remove has been removed). Every other check in this module (bare
``--dist load``, ``-n auto``/``--dist loadfile`` pairing, ``fail-fast: false``)
stays live-green as before.
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

_BARE_LOAD_RE = re.compile(r"--dist\s+load(?!file)\b")
_LOADFILE_RE = re.compile(r"--dist\s+loadfile\b")
_PARALLEL_AUTO_RE = re.compile(r"-n\s+auto\b")
_IGNORE_VALUE_RE = re.compile(r"--ignore=(\S+)")
# Sync-suite positional scope: a family file itself, or the ``tests/sync``
# directory (mirrors test_serial_port_preservation.py's scope predicate — a
# whole-``tests/`` run relies on markers to skip the family, which a purely
# path-based scan cannot see; the real C-002/C-007 risk is a sync-targeted
# shard, and every FIXED_RANGE_SUITES member lives under ``tests/sync``).
_SYNC_DIR_RE = re.compile(r"(?<![\w/])tests/sync/?(?=\s|\\|$)")


def _workflow_paths() -> list[Path]:
    """Every workflow file under ``.github/workflows/`` (the full glob, not
    the narrower five-file ``gc.WORKFLOW_FILES`` subset ``_gate_coverage``
    tracks for test-selection modelling — GC-4 is a lint over the whole
    directory).
    """
    return sorted(gc.WORKFLOWS_DIR.glob("*.yml"))


def _load_jobs() -> dict[str, dict[str, Any]]:
    """``workflow.yml::job_id`` -> raw job mapping, across every workflow file."""
    jobs: dict[str, dict[str, Any]] = {}
    for path in _workflow_paths():
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job_id, job in (data.get("jobs") or {}).items():
            jobs[f"{path.name}::{job_id}"] = job
    return jobs


def _pytest_commands(script: str) -> list[str]:
    """Continuation-joined logical lines of ``script`` that invoke pytest."""
    return [
        line
        for line in gc.join_continuations(script)
        if "pytest" in line and not line.lstrip().startswith("#")
    ]


def _job_commands(job: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    for step in job.get("steps") or []:
        if isinstance(step, dict) and "run" in step:
            commands.extend(_pytest_commands(str(step["run"])))
    return commands


def _all_commands(jobs: dict[str, dict[str, Any]]) -> list[str]:
    return [cmd for job in jobs.values() for cmd in _job_commands(job)]


def _matrix_jobs(jobs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        label: job
        for label, job in jobs.items()
        if isinstance(job.get("strategy"), dict) and "matrix" in job["strategy"]
    }


# ---------------------------------------------------------------------------
# Pure, fault-injectable violation finders (each takes plain data, never
# touches the filesystem, so fault-injection tests can drive them directly).
# ---------------------------------------------------------------------------


def bare_dist_load_violations(commands: list[str]) -> list[str]:
    """C-001: no run-script uses bare ``--dist load`` (must be ``loadfile``)."""
    return [
        f"bare --dist load (use loadfile): {cmd.strip()[:_CMD_PREVIEW]}"
        for cmd in commands
        if _BARE_LOAD_RE.search(cmd)
    ]


def missing_loadfile_pairing_violations(commands: list[str]) -> list[str]:
    """Structural corollary of C-001: every ``-n auto`` pairs with ``--dist loadfile``."""
    return [
        f"-n auto without --dist loadfile in the same command: {cmd.strip()[:_CMD_PREVIEW]}"
        for cmd in commands
        if _PARALLEL_AUTO_RE.search(cmd) and not _LOADFILE_RE.search(cmd)
    ]


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


def fixed_range_under_auto_violations(commands: list[str]) -> list[str]:
    """C-002/C-007: no ``FIXED_RANGE_SUITES`` member is collected under ``-n auto``.

    A member counts as "collected" when the command's positional scope covers
    it (the file itself, or ``tests/sync``) AND no ``--ignore=`` counter-
    evidence excludes it — mirrors
    ``test_serial_port_preservation._collects_member``'s structural relation.
    """
    violations: list[str] = []
    for member in FIXED_RANGE_SUITES:
        for cmd in commands:
            if (
                _PARALLEL_AUTO_RE.search(cmd)
                and _covers_member_scope(cmd, member)
                and not _ignores_member(cmd, member)
            ):
                violations.append(
                    f"{member} collected under -n auto: {cmd.strip()[:_CMD_PREVIEW]}",
                )
    return violations


def fail_fast_violations(jobs: dict[str, dict[str, Any]]) -> list[str]:
    """C-006: every job with a ``strategy.matrix`` sets ``fail-fast: false``.

    A matrix with ``fail-fast`` absent (GitHub Actions defaults it to
    ``true``) or explicitly ``true`` fails this check identically — only an
    explicit ``False`` passes.
    """
    violations: list[str] = []
    for label, job in jobs.items():
        strategy = job.get("strategy")
        if not isinstance(strategy, dict) or "matrix" not in strategy:
            continue
        if strategy.get("fail-fast") is not False:
            violations.append(
                f"{label}: strategy.matrix present without fail-fast: false "
                f"(got {strategy.get('fail-fast')!r})",
            )
    return violations


# ---------------------------------------------------------------------------
# Anti-vacuous canary
# ---------------------------------------------------------------------------


def test_workflow_parse_is_not_vacuous() -> None:
    """The scan must actually inspect real workflow files, commands, and
    matrix jobs — an empty/broken parse must not pass any check below green
    by finding nothing to check.
    """
    paths = _workflow_paths()
    assert paths, "no .github/workflows/*.yml files found — scan would be vacuous"
    jobs = _load_jobs()
    commands = _all_commands(jobs)
    assert commands, "workflow parse found zero pytest run-script commands — scan would be vacuous"
    assert _matrix_jobs(jobs), (
        "workflow parse found zero strategy.matrix jobs — C-006 scan would be vacuous"
    )


# ---------------------------------------------------------------------------
# Live checks against the current tree (a/b/c must stay GREEN today; the
# fixed-range-under-auto check is the one pre-existing #2590 gap — xfail'd
# strict until WP06 lands its --ignore= entries).
# ---------------------------------------------------------------------------


def test_no_bare_dist_load_in_current_workflows() -> None:
    violations = bare_dist_load_violations(_all_commands(_load_jobs()))
    assert not violations, f"C-001 bare --dist load violations: {violations}"


def test_auto_runs_pair_with_loadfile_in_current_workflows() -> None:
    violations = missing_loadfile_pairing_violations(_all_commands(_load_jobs()))
    assert not violations, f"-n auto without --dist loadfile: {violations}"


def test_matrix_jobs_set_fail_fast_false_in_current_workflows() -> None:
    violations = fail_fast_violations(_load_jobs())
    assert not violations, f"C-006 fail-fast violations: {violations}"


def test_fixed_range_suites_not_collected_under_auto_in_current_workflows() -> None:
    violations = fixed_range_under_auto_violations(_all_commands(_load_jobs()))
    assert not violations, f"C-002/C-007 fixed-range-under-auto violations: {violations}"


# ---------------------------------------------------------------------------
# Fault-injection: each pure checker must bite on a synthetic violation.
# ---------------------------------------------------------------------------


def test_fault_injection_bare_dist_load_bites() -> None:
    commands = ["uv run python -m pytest tests/foo -n auto --dist load"]
    violations = bare_dist_load_violations(commands)
    assert violations, "checker missed a bare --dist load invocation"


def test_fault_injection_bare_dist_load_does_not_over_fire_on_loadfile() -> None:
    commands = ["uv run python -m pytest tests/foo -n auto --dist loadfile"]
    assert not bare_dist_load_violations(commands), (
        "checker over-fired on a correct --dist loadfile invocation"
    )


def test_fault_injection_missing_loadfile_pairing_bites() -> None:
    commands = ["uv run python -m pytest tests/foo -n auto --tb=short"]
    violations = missing_loadfile_pairing_violations(commands)
    assert violations, "checker missed -n auto without a paired --dist loadfile"


def test_fault_injection_fixed_range_under_auto_bites() -> None:
    member = FIXED_RANGE_SUITES[0]
    commands = [f"uv run python -m pytest {member} -n auto --dist loadfile"]
    violations = fixed_range_under_auto_violations(commands)
    assert any(member in v for v in violations), (
        f"checker missed {member} collected under -n auto"
    )


def test_fault_injection_fixed_range_under_auto_respects_explicit_ignore() -> None:
    """Inverse micro-check: a member excluded via an explicit ``--ignore=`` must
    NOT be flagged as the *subject* of a violation — the checker must not
    over-fire on the correct pattern ``fast-tests-sync`` already uses for
    ``test_orphan_sweep.py``. Uses the violation message's leading-subject
    prefix (not a bare substring check) because the ignored member's own path
    still appears, textually, inside the *other* members' violation previews
    (each preview embeds the full command, which contains
    ``--ignore=<ignored-member>``) — a bare substring check would false-fail
    on that textual overlap even though the checker behaved correctly.
    """
    member = FIXED_RANGE_SUITES[0]
    commands = [f"uv run python -m pytest tests/sync/ -n auto --ignore={member} --dist loadfile"]
    violations = fixed_range_under_auto_violations(commands)
    assert not any(v.startswith(f"{member} collected") for v in violations), (
        f"checker over-fired on {member} despite an explicit --ignore="
    )


def test_fault_injection_matrix_missing_fail_fast_bites() -> None:
    jobs = {
        "synthetic.yml::shard-job": {"strategy": {"matrix": {"include": [{"shard": "a"}]}}},
    }
    violations = fail_fast_violations(jobs)
    assert violations, "checker missed a strategy.matrix job with fail-fast absent"


def test_fault_injection_matrix_fail_fast_true_bites() -> None:
    jobs = {
        "synthetic.yml::shard-job": {
            "strategy": {"fail-fast": True, "matrix": {"include": [{"shard": "a"}]}},
        },
    }
    violations = fail_fast_violations(jobs)
    assert violations, "checker missed a strategy.matrix job with fail-fast: true"


def test_fault_injection_matrix_fail_fast_false_passes() -> None:
    jobs = {
        "synthetic.yml::shard-job": {
            "strategy": {"fail-fast": False, "matrix": {"include": [{"shard": "a"}]}},
        },
    }
    assert not fail_fast_violations(jobs), (
        "checker over-fired on a correctly configured fail-fast: false matrix job"
    )


def test_fault_injection_non_matrix_job_is_ignored() -> None:
    """A job with no ``strategy.matrix`` (e.g. a plain job, or a ``strategy``
    block without a matrix) must never be flagged — this check is scoped to
    sharded matrix jobs only.
    """
    jobs: dict[str, dict[str, Any]] = {
        "synthetic.yml::plain-job": {"steps": [{"run": "uv run pytest tests/"}]},
        "synthetic.yml::strategy-no-matrix": {"strategy": {"fail-fast": True}},
    }
    assert not fail_fast_violations(jobs), (
        "checker over-fired on a job without a strategy.matrix block"
    )

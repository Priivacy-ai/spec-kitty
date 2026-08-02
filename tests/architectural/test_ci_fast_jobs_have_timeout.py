"""WP12 follow-up — fast-tier CI jobs must carry ``--timeout`` (#3143 gap).

Mission ``verification-trust-3115-01KYVYWM`` WP12 added
``--timeout=240 --timeout-method=signal`` to ~17 fast-tier pytest invocations
in ``.github/workflows/ci-quality.yml`` (the ``signal`` method chosen
explicitly — WP12's T037 measured the ``thread`` method killing a session
mid-run with **no summary and therefore no verdict**, which is exactly the
"a mechanism reporting success for having done nothing" shape the whole
mission exists to close). Nothing asserted the flag *stays* present: a future
YAML edit to any of those jobs could silently drop ``--timeout`` and restore
the pre-WP12 hang-not-fail failure mode, with no gate to catch it.

This module is that gate. It is a real parse of ``ci-quality.yml`` (via
``yaml.safe_load`` and this repo's canonical workflow-parsing primitives in
``tests.architectural._gate_coverage`` — ``join_continuations``,
``parse_pytest_invocation``, ``positive_marker_tokens`` — reused rather than
re-derived, per this repo's canonical-sources discipline), not a brittle
full-file string match.

**Fast-tier classification is a union of two signals, not job-id naming
alone**: a job counts as fast-tier if its id follows the ``fast-tests-*``
convention, OR its pytest selection positively references the ``fast``
marker (``kernel-tests`` selects ``-m "fast and not windows_ci"`` under a
job id that does not carry the ``fast-tests-`` prefix — a naming-only check
would silently miss it, and a marker-only check would miss a hypothetical
future job that scopes by path instead of marker, the exact shape
``fast-tests-docs``/``fast-tests-sync-orphan-sweep`` already take).

**Two jobs are legitimately exempt** (both real, both verified against the
actual test content they run, not asserted from convenience):

- ``fast-tests-docs`` — its pytest invocation scopes to the whole
  ``tests/docs/`` directory with **no** ``-m "fast"`` filter, so it bundles
  ``tests/docs/test_asset_resolution_wheel.py``
  (``pytest.mark.slow``/``distribution``/``non_sandbox`` — builds and
  installs a real wheel into a throwaway venv, documented ``>30s`` by
  design). A blanket ``--timeout=240`` there would risk falsely redding that
  legitimate long-runner instead of catching a genuine hang.
- ``fast-tests-sync-orphan-sweep`` — the real-port daemon suite
  (``tests/sync/test_orphan_sweep.py``, OS-global port binds 9400-9449, not
  HOME-isolated), run serially (``-n0``). ``pytest-timeout``'s ``signal``
  method raises ``SIGALRM``, which is unsafe to deliver mid-teardown of a
  live socket/daemon process.

Both carry a one-line ``# WP12 --timeout exemption: ...`` comment in
``ci-quality.yml`` next to their pytest invocation, stating the reason. This
module asserts that comment is present for both — an allowlist entry with no
recorded rationale is exactly the kind of unreviewable, silently-growable
exemption this gate exists to prevent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_WORKFLOW_PATH = gc.WORKFLOWS_DIR / "ci-quality.yml"

_FAST_JOB_ID_PREFIX = "fast-tests-"
_FAST_MARKER_TOKEN = "fast"

#: Jobs deliberately exempt from carrying --timeout. Closed by construction:
#: adding a member here without also adding the matching
#: `# WP12 --timeout exemption: ...` comment in ci-quality.yml is itself a
#: violation (see test_ci_quality_exempt_jobs_carry_marker_comment below).
_TIMEOUT_EXEMPT_JOBS: frozenset[str] = frozenset(
    {
        "fast-tests-docs",
        "fast-tests-sync-orphan-sweep",
    }
)

_EXEMPTION_MARKER = "WP12 --timeout exemption"

_TIMEOUT_FLAG_RE = re.compile(r"--timeout=\d+")


@dataclass(frozen=True)
class JobInfo:
    """One CI job's pytest-relevant surface.

    ``run_text`` is the raw, unmodified concatenation of every step's
    ``run:`` block-scalar text (comments intact — the exemption marker
    check needs them). ``pytest_commands`` is the continuation-joined,
    comment-stripped set of logical lines that actually invoke pytest (what
    the --timeout check scans). ``marker_tokens`` is the union of every
    positively-referenced ``-m`` marker name across those commands.
    """

    job_id: str
    run_text: str
    pytest_commands: tuple[str, ...] = field(default_factory=tuple)
    marker_tokens: frozenset[str] = frozenset()


def _job_pytest_commands(job: dict[str, Any]) -> list[str]:
    """Continuation-joined, comment-stripped pytest-invoking lines of *job*."""
    commands: list[str] = []
    for step in job.get("steps") or []:
        if isinstance(step, dict) and "run" in step:
            for logical in gc.join_continuations(str(step["run"])):
                if "pytest" in logical and not logical.lstrip().startswith("#"):
                    commands.append(logical)
    return commands


def _job_run_text(job: dict[str, Any]) -> str:
    """Raw concatenation of every step's run-script text, comments intact."""
    return "\n".join(
        str(step["run"]) for step in (job.get("steps") or []) if isinstance(step, dict) and "run" in step
    )


def _job_marker_tokens_by_id(path: Path) -> dict[str, frozenset[str]]:
    """job id -> union of positively-referenced marker names.

    Delegates to ``gc.parse_workflow``, which already expands
    ``strategy.matrix.include`` (``${{ matrix.X }}``) before extracting the
    ``-m`` expression — re-deriving that substitution here would duplicate a
    non-trivial, already-canonical mechanism and risks silently mis-modelling
    a matrix-parametrized marker (e.g. ``integration-tests-core-misc``'s
    ``${{ matrix.marker_extra }}``).
    """
    tokens_by_job: dict[str, set[str]] = {}
    for gate in gc.parse_workflow(path):
        tokens_by_job.setdefault(gate.job, set()).update(gc.positive_marker_tokens(gate.marker_expr))
    return {job_id: frozenset(tokens) for job_id, tokens in tokens_by_job.items()}


def load_ci_quality_jobs(path: Path = _WORKFLOW_PATH) -> dict[str, JobInfo]:
    """Every job in ``ci-quality.yml`` as a :class:`JobInfo`, keyed by job id."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    marker_tokens_by_id = _job_marker_tokens_by_id(path)
    jobs: dict[str, JobInfo] = {}
    for job_id, job in (data.get("jobs") or {}).items():
        jobs[job_id] = JobInfo(
            job_id=job_id,
            run_text=_job_run_text(job),
            pytest_commands=tuple(_job_pytest_commands(job)),
            marker_tokens=marker_tokens_by_id.get(job_id, frozenset()),
        )
    return jobs


def is_fast_tier(job: JobInfo) -> bool:
    """A job is fast-tier iff its id follows the ``fast-tests-*`` naming
    convention OR its pytest selection positively references the ``fast``
    marker. Either signal alone leaves a gap (see module docstring); the
    union is what actually can't be dodged by a differently-shaped new job.
    """
    return job.job_id.startswith(_FAST_JOB_ID_PREFIX) or _FAST_MARKER_TOKEN in job.marker_tokens


def timeout_violations(
    jobs: dict[str, JobInfo],
    exempt: frozenset[str] = _TIMEOUT_EXEMPT_JOBS,
) -> list[str]:
    """Every fast-tier, non-exempt job with no ``--timeout=<n>`` on any of
    its pytest command lines."""
    violations = [
        job.job_id
        for job in jobs.values()
        if is_fast_tier(job)
        and job.job_id not in exempt
        and not any(_TIMEOUT_FLAG_RE.search(cmd) for cmd in job.pytest_commands)
    ]
    return sorted(violations)


def missing_exemption_marker_violations(
    jobs: dict[str, JobInfo],
    exempt: frozenset[str] = _TIMEOUT_EXEMPT_JOBS,
    marker: str = _EXEMPTION_MARKER,
) -> list[str]:
    """Every allowlisted job that is missing (or no longer carries) the
    explanatory ``# WP12 --timeout exemption: ...`` comment."""
    return sorted(job_id for job_id in exempt if marker not in jobs.get(job_id, JobInfo(job_id, "")).run_text)


# ---------------------------------------------------------------------------
# Live gates — the real ci-quality.yml
# ---------------------------------------------------------------------------


def test_ci_quality_fast_jobs_carry_timeout() -> None:
    jobs = load_ci_quality_jobs()
    fast_ids = {job.job_id for job in jobs.values() if is_fast_tier(job)}
    assert fast_ids, "no fast-tier jobs discovered in ci-quality.yml — this gate would be vacuous"

    violations = timeout_violations(jobs)
    assert not violations, (
        f"fast-tier job(s) in ci-quality.yml with no --timeout=<n> on any pytest "
        f"invocation: {violations}. Either restore --timeout=240 "
        f"--timeout-method=signal, or (if the omission is deliberate) add the "
        f"job id to _TIMEOUT_EXEMPT_JOBS in this file AND a "
        f"'{_EXEMPTION_MARKER}: <reason>' comment next to its pytest invocation "
        f"in ci-quality.yml."
    )


def test_ci_quality_exempt_jobs_carry_marker_comment() -> None:
    jobs = load_ci_quality_jobs()
    violations = missing_exemption_marker_violations(jobs)
    assert not violations, (
        f"allowlisted _TIMEOUT_EXEMPT_JOBS entr(y/ies) missing the "
        f"'{_EXEMPTION_MARKER}' rationale comment in ci-quality.yml (or the job "
        f"no longer exists there): {violations}. The allowlist must not grow "
        f"without a recorded, legible reason."
    )


def test_exempt_allowlist_members_still_exist() -> None:
    jobs = load_ci_quality_jobs()
    missing = sorted(job_id for job_id in _TIMEOUT_EXEMPT_JOBS if job_id not in jobs)
    assert not missing, f"allowlisted job(s) no longer exist in ci-quality.yml: {missing}"


# ---------------------------------------------------------------------------
# Fault injection — pure functions over synthetic JobInfo data, no filesystem
# ---------------------------------------------------------------------------


def test_fault_injection_missing_timeout_on_covered_job_bites() -> None:
    jobs = {
        "fast-tests-widgets": JobInfo(
            job_id="fast-tests-widgets",
            run_text='uv run python -m pytest tests/widgets -m "fast and not windows_ci"',
            pytest_commands=('uv run python -m pytest tests/widgets -m "fast and not windows_ci"',),
            marker_tokens=frozenset({"fast"}),
        ),
    }
    assert timeout_violations(jobs) == ["fast-tests-widgets"]


def test_fault_injection_timeout_present_does_not_bite() -> None:
    jobs = {
        "fast-tests-widgets": JobInfo(
            job_id="fast-tests-widgets",
            run_text="...",
            pytest_commands=('pytest tests/widgets -m "fast" --timeout=240 --timeout-method=signal',),
            marker_tokens=frozenset({"fast"}),
        ),
    }
    assert not timeout_violations(jobs)


def test_fault_injection_new_fast_job_without_allowlisting_bites() -> None:
    """A brand-new fast-tier job with no --timeout and NOT in the exempt
    allowlist must be flagged — the allowlist is closed, never open-by-default."""
    jobs = {
        "fast-tests-newthing": JobInfo(
            job_id="fast-tests-newthing",
            run_text='pytest tests/newthing -m "fast"',
            pytest_commands=('pytest tests/newthing -m "fast"',),
            marker_tokens=frozenset({"fast"}),
        ),
    }
    assert timeout_violations(jobs, exempt=frozenset()) == ["fast-tests-newthing"]


def test_fault_injection_marker_only_job_is_still_classified_fast_tier() -> None:
    """A job not named fast-tests-* but selecting -m fast (e.g. kernel-tests)
    is still classified fast-tier via the marker-token union, not the
    naming convention alone."""
    job = JobInfo(job_id="kernel-tests", run_text="", pytest_commands=(), marker_tokens=frozenset({"fast"}))
    assert is_fast_tier(job)


def test_fault_injection_non_fast_job_is_not_classified_fast_tier() -> None:
    job = JobInfo(job_id="slow-tests", run_text="", pytest_commands=(), marker_tokens=frozenset({"slow"}))
    assert not is_fast_tier(job)


def test_fault_injection_exempt_job_without_marker_comment_bites() -> None:
    jobs = {
        "fast-tests-docs": JobInfo(job_id="fast-tests-docs", run_text="no rationale recorded here"),
        "fast-tests-sync-orphan-sweep": JobInfo(
            job_id="fast-tests-sync-orphan-sweep",
            run_text=f"# {_EXEMPTION_MARKER}: real-port daemon, SIGALRM unsafe mid-teardown",
        ),
    }
    assert missing_exemption_marker_violations(jobs) == ["fast-tests-docs"]


def test_fault_injection_both_exempt_jobs_with_comment_do_not_bite() -> None:
    jobs = {
        job_id: JobInfo(job_id=job_id, run_text=f"# {_EXEMPTION_MARKER}: stated reason")
        for job_id in _TIMEOUT_EXEMPT_JOBS
    }
    assert not missing_exemption_marker_violations(jobs)

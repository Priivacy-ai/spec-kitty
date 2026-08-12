"""Fast-tier CI pytest jobs carry bounded per-test timeouts.

Authority: open issue #3143.  The live workflow check and explicit exemption
rationale check remain; eight synthetic classifier/self-tests were retired.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.architectural import _gate_coverage as gc

pytestmark = pytest.mark.architectural

_WORKFLOW_PATH = gc.WORKFLOWS_DIR / "ci-quality.yml"
_TIMEOUT_EXEMPT_JOBS = frozenset(
    {"fast-tests-docs", "fast-tests-sync-orphan-sweep"}
)
_EXEMPTION_MARKER = "WP12 --timeout exemption"
_TIMEOUT_FLAG_RE = re.compile(r"--timeout=\d+")


@dataclass(frozen=True)
class JobInfo:
    job_id: str
    run_text: str
    pytest_commands: tuple[str, ...] = field(default_factory=tuple)
    marker_tokens: frozenset[str] = frozenset()


def _job_pytest_commands(job: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        logical
        for step in job.get("steps") or []
        if isinstance(step, dict) and "run" in step
        for logical in gc.join_continuations(str(step["run"]))
        if "pytest" in logical and not logical.lstrip().startswith("#")
    )


def _job_run_text(job: dict[str, Any]) -> str:
    return "\n".join(
        str(step["run"])
        for step in job.get("steps") or []
        if isinstance(step, dict) and "run" in step
    )


def _marker_tokens(path: Path) -> dict[str, frozenset[str]]:
    by_job: dict[str, set[str]] = {}
    for gate in gc.parse_workflow(path):
        by_job.setdefault(gate.job, set()).update(
            gc.positive_marker_tokens(gate.marker_expr)
        )
    return {job: frozenset(tokens) for job, tokens in by_job.items()}


def _jobs(path: Path = _WORKFLOW_PATH) -> dict[str, JobInfo]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    tokens = _marker_tokens(path)
    return {
        job_id: JobInfo(
            job_id=job_id,
            run_text=_job_run_text(job),
            pytest_commands=_job_pytest_commands(job),
            marker_tokens=tokens.get(job_id, frozenset()),
        )
        for job_id, job in (data.get("jobs") or {}).items()
    }


def _is_fast(job: JobInfo) -> bool:
    return job.job_id.startswith("fast-tests-") or "fast" in job.marker_tokens


def test_ci_quality_fast_jobs_carry_timeout() -> None:
    jobs = _jobs()
    fast = [job for job in jobs.values() if _is_fast(job)]
    assert fast, "no fast-tier jobs discovered"
    violations = sorted(
        job.job_id
        for job in fast
        if job.job_id not in _TIMEOUT_EXEMPT_JOBS
        and not any(_TIMEOUT_FLAG_RE.search(cmd) for cmd in job.pytest_commands)
    )
    assert not violations, f"fast-tier jobs missing --timeout=<n>: {violations}"


def test_timeout_exemptions_exist_and_record_a_reason() -> None:
    jobs = _jobs()
    invalid = sorted(
        job_id
        for job_id in _TIMEOUT_EXEMPT_JOBS
        if job_id not in jobs or _EXEMPTION_MARKER not in jobs[job_id].run_text
    )
    assert not invalid, f"missing or unexplained timeout exemptions: {invalid}"

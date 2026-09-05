"""By-construction guard that no wall-clock latency ceiling blocks a PR (#3787).

FR-004 / NFR-003 / SC-002 / C-001. The retired single-shot ``spec-kitty next``
latency gate (``scripts/check_nfr_003_latency.py``, run inside
``clean-install-verification``) false-redded on shared-runner variance. It has
been removed; the ``next`` cold-start signal now runs statistically and off the
PR-blocking path in ``performance.yml``. These static assertions over
``.github/workflows/ci-quality.yml`` prevent a silent re-introduction of a
blocking wall-clock ceiling while keeping the structural clean-wheel smoke
check that a broken ``next`` still fails on (C-001).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW_PATH = _REPO_ROOT / ".github" / "workflows" / "ci-quality.yml"
_RETIRED_SCRIPT = _REPO_ROOT / "scripts" / "check_nfr_003_latency.py"
_CLEAN_INSTALL_JOB = "clean-install-verification"
_SMOKE_STEP_NAME = "Run spec-kitty next against fixture mission"


def _workflow_text() -> str:
    return _WORKFLOW_PATH.read_text(encoding="utf-8")


def _workflow() -> dict[str, Any]:
    return cast("dict[str, Any]", yaml.safe_load(_workflow_text()))


def _clean_install_steps() -> list[dict[str, Any]]:
    jobs = _workflow()["jobs"]
    assert _CLEAN_INSTALL_JOB in jobs, f"{_CLEAN_INSTALL_JOB!r} job missing from ci-quality.yml"
    return cast("list[dict[str, Any]]", jobs[_CLEAN_INSTALL_JOB].get("steps", []))


def test_no_wall_clock_latency_ceiling_on_the_blocking_path() -> None:
    # FR-004/NFR-003: no ci-quality.yml step invokes the retired latency script
    # or any single-shot median/ceiling check. ci-quality.yml is the workflow
    # whose quality-gate aggregator blocks merge.
    text = _workflow_text()
    assert "check_nfr_003_latency" not in text, (
        "A wall-clock latency ceiling was re-introduced into the blocking ci-quality.yml — the next-latency signal must live off-PR in performance.yml (#3787)."
    )


def test_clean_wheel_structural_smoke_is_retained() -> None:
    # C-001: the structural "does `next` run at all from a clean wheel" step
    # must remain — only the wall-clock *latency* assertion was removed.
    names = {step.get("name") for step in _clean_install_steps()}
    assert _SMOKE_STEP_NAME in names, f"the {_SMOKE_STEP_NAME!r} structural smoke step must remain in {_CLEAN_INSTALL_JOB} (C-001)."


def test_no_clean_install_step_runs_the_retired_latency_script() -> None:
    for step in _clean_install_steps():
        assert "check_nfr_003_latency" not in step.get("run", ""), f"clean-install step {step.get('name')!r} still runs the retired latency script."


def test_the_sole_ceiling_reader_is_deleted() -> None:
    # FR-005: the only consumer of the absolute ceiling was the latency script;
    # deleting it removes the ceiling by construction.
    assert not _RETIRED_SCRIPT.exists(), "scripts/check_nfr_003_latency.py must be deleted (#3787); its ceiling read is what this mission retires."

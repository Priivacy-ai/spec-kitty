"""Architectural guards for CI path-filter ownership."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci-quality.yml"


def _path_filters() -> dict[str, list[str]]:
    data = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    filter_step = next(
        step for step in data["jobs"]["changes"]["steps"] if step.get("id") == "filter"
    )
    return yaml.safe_load(filter_step["with"]["filters"])


def _job_run_script(job_name: str, step_name: str) -> str:
    data = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    step = next(
        step
        for step in data["jobs"][job_name]["steps"]
        if step.get("name") == step_name
    )
    return str(step["run"])


def test_missions_filter_includes_missions_package_and_tests() -> None:
    """Mission package tests must both trigger and run the mission test slice."""
    missions_filter = set(_path_filters()["missions"])
    assert "src/specify_cli/missions/**" in missions_filter
    assert "tests/fixtures/missions/**" in missions_filter
    assert "tests/specify_cli/missions/**" in missions_filter

    fast_run = _job_run_script("fast-tests-missions", "Run fast tests — missions")
    integration_run = _job_run_script(
        "integration-tests-missions",
        "Run integration tests — missions",
    )
    assert "tests/specify_cli/missions/" in fast_run
    assert "tests/specify_cli/missions/" in integration_run


def test_lanes_filter_and_jobs_include_lanes_package_tests() -> None:
    """Lane package tests must both trigger and run the lane test slice."""
    lanes_filter = set(_path_filters()["lanes"])
    assert "tests/specify_cli/lanes/**" in lanes_filter

    fast_run = _job_run_script("fast-tests-lanes", "Run fast tests — lanes")
    integration_run = _job_run_script(
        "integration-tests-lanes",
        "Run integration tests — lanes",
    )
    assert "tests/specify_cli/lanes/" in fast_run
    assert "tests/specify_cli/lanes/" in integration_run


def test_next_filter_includes_canonical_runtime_packages() -> None:
    """The next trigger must watch the canonical runtime, not just the shim.

    src/specify_cli/next/ is a deprecation shim (removed in 3.3.0); the
    canonical runtime lives in src/runtime/next/ and depends on
    src/mission_runtime/. Both must trigger the next test suites.
    """
    next_filter = set(_path_filters()["next"])
    assert "src/runtime/next/**" in next_filter
    assert "src/mission_runtime/**" in next_filter


def test_next_jobs_measure_canonical_runtime_coverage() -> None:
    """Both next suites must measure src/runtime/next, not only the shim."""
    fast_run = _job_run_script("fast-tests-next", "Run fast tests — next")
    integration_run = _job_run_script(
        "integration-tests-next",
        "Run integration tests — next",
    )
    assert "--cov=src/runtime/next" in fast_run
    assert "--cov=src/runtime/next" in integration_run


def test_diff_coverage_critical_paths_include_canonical_runtime() -> None:
    """The enforced diff-coverage gate must include the canonical runtime."""
    run_script = _job_run_script(
        "diff-coverage",
        "diff-coverage (critical-path, enforced)",
    )
    assert "'src/runtime/next/*'" in run_script
    assert "'src/mission_runtime/*'" in run_script


def test_execution_context_only_core_misc_runs_focused_parity_gate() -> None:
    """Execution-context-only changes must still run the CWD parity ratchet."""
    run_script = _job_run_script(
        "integration-tests-core-misc",
        "Run integration tests — core misc",
    )

    assert 'needs.changes.outputs.core_misc }}" != "true"' in run_script
    assert 'needs.changes.outputs.execution_context }}" = "true"' in run_script
    assert "tests/architectural/test_execution_context_parity.py" in run_script
    assert "coverage-integration-core-misc.xml" in run_script

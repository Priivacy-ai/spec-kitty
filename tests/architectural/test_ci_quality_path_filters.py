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
    """Mission package edits must run the mission test slice."""
    missions_filter = set(_path_filters()["missions"])
    assert "src/specify_cli/missions/**" in missions_filter
    assert "tests/fixtures/missions/**" in missions_filter
    assert "tests/specify_cli/missions/**" in missions_filter


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

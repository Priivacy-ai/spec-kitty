"""Architectural guards for CI path-filter ownership."""

from __future__ import annotations

import subprocess
import sys
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


def _job(job_name: str) -> dict[str, object]:
    data = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    return dict(data["jobs"][job_name])


def _collect_nodes(args: list[str]) -> set[str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-qq", *args],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        line.strip()
        for line in result.stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    }


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
    assert "coverage-integration-core-misc-${{ matrix.shard }}.xml" in run_script


def test_core_misc_integration_is_sharded_and_parallelized() -> None:
    """The slow core-misc integration bucket must stay split and parallel."""
    job = _job("integration-tests-core-misc")
    matrix = job["strategy"]["matrix"]["include"]  # type: ignore[index]
    shard_names = {entry["shard"] for entry in matrix}

    assert shard_names == {
        "architectural",
        "integration",
        "specify-cli-heavy",
        "specify-cli-rest",
        "auth-audit-git",
        "misc",
    }

    run_script = _job_run_script(
        "integration-tests-core-misc",
        "Run integration tests — core misc",
    )
    assert "-n auto --dist loadfile" in run_script
    assert "--durations=50" in run_script


def test_ci_quality_guards_trigger_core_misc_validation() -> None:
    """CI workflow and architectural guard edits must run the validating shard."""
    core_misc_filter = set(_path_filters()["core_misc"])
    assert ".github/workflows/ci-quality.yml" in core_misc_filter
    assert "tests/architectural/**" in core_misc_filter


def test_core_misc_shards_plus_e2e_owner_cover_legacy_selection() -> None:
    """The shard split must not drop tests covered by the legacy catch-all job."""
    marker = "-m"
    marker_expr = "not windows_ci and (git_repo or integration or architectural)"
    legacy_nodes = _collect_nodes(
        [
            "--ignore=tests/doctrine",
            "--ignore=tests/kernel",
            "--ignore=tests/status",
            "--ignore=tests/specify_cli/status",
            "--ignore=tests/sync",
            "--ignore=tests/merge",
            "--ignore=tests/missions",
            "--ignore=tests/post_merge",
            "--ignore=tests/release",
            "--ignore=tests/review",
            "--ignore=tests/next",
            "--ignore=tests/specify_cli/next",
            "--ignore=tests/lanes",
            "--ignore=tests/test_dashboard",
            "--ignore=tests/upgrade",
            "--ignore=tests/cli",
            "--ignore=tests/runtime",
            "--ignore=tests/charter",
            "--ignore=tests/agent",
            marker,
            marker_expr,
        ]
    )

    shard_commands = [
        ["tests/adversarial", "tests/architectural", "tests/architecture", "tests/lint"],
        ["tests/integration"],
        [
            "tests/specify_cli/migration",
            "tests/specify_cli/invocation",
            "tests/specify_cli/test_charter_activate_cli.py",
        ],
        [
            "tests/specify_cli",
            "--ignore=tests/specify_cli/migration",
            "--ignore=tests/specify_cli/invocation",
            "--ignore=tests/specify_cli/test_charter_activate_cli.py",
            "--ignore=tests/specify_cli/status",
            "--ignore=tests/specify_cli/next",
        ],
        ["tests/auth", "tests/audit", "tests/git_ops", "tests/git", "tests/cli_gate"],
        [
            "tests/calibration",
            "tests/concurrency",
            "tests/contract",
            "tests/core",
            "tests/cross_branch",
            "tests/docs",
            "tests/doctor",
            "tests/init",
            "tests/migration",
            "tests/mission_runtime",
            "tests/packaging",
            "tests/policy",
            "tests/readiness",
            "tests/regression",
            "tests/regressions",
            "tests/research",
            "tests/retrospective",
            "tests/saas",
            "tests/stress",
            "tests/tasks",
            "tests/unit",
        ],
    ]
    new_nodes: set[str] = set()
    for command in shard_commands:
        new_nodes.update(_collect_nodes([*command, marker, marker_expr]))
    new_nodes.update(
        _collect_nodes(
            [
                "tests/e2e",
                "tests/cross_cutting",
                "-m",
                "not distribution and not windows_ci",
            ]
        )
    )

    missing = sorted(legacy_nodes - new_nodes)
    assert not missing, "Shard split dropped legacy core-misc tests:\n" + "\n".join(
        missing[:20]
    )


def test_core_misc_excludes_e2e_and_cross_cutting_suites() -> None:
    """E2E and cross-cutting suites belong to e2e-cross-cutting, not core-misc."""
    path_filters = _path_filters()
    assert "tests/e2e/**" not in path_filters["core_misc"]
    assert "tests/cross_cutting/**" not in path_filters["core_misc"]
    assert "tests/e2e/**" in path_filters["e2e"]
    assert "tests/cross_cutting/**" in path_filters["e2e"]

    fast_run = _job_run_script("fast-tests-core-misc", "Run fast tests — core misc")
    assert "--ignore=tests/e2e" in fast_run
    assert "--ignore=tests/cross_cutting" in fast_run

    job = _job("integration-tests-core-misc")
    matrix = job["strategy"]["matrix"]["include"]  # type: ignore[index]
    matrix_text = "\n".join(
        f"{entry.get('paths', '')}\n{entry.get('ignore_args', '')}" for entry in matrix
    )
    assert "tests/e2e" not in matrix_text
    assert "tests/cross_cutting" not in matrix_text


def test_e2e_cross_cutting_runs_independently_of_fast_fanout() -> None:
    """The dedicated e2e job should not wait on unrelated fast-test shards."""
    job = _job("e2e-cross-cutting")
    assert job["needs"] == ["changes"]

    condition = str(job["if"])
    assert "needs.changes.outputs.e2e == 'true'" in condition
    assert "needs.changes.outputs.core_misc == 'true'" in condition
    assert "needs.changes.outputs.execution_context == 'true'" in condition

    path_filters = _path_filters()
    assert ".github/workflows/ci-quality.yml" in path_filters["e2e"]

    run_script = _job_run_script(
        "e2e-cross-cutting",
        "[ENFORCED] Run e2e and cross_cutting tests with coverage",
    )
    assert "tests/e2e/ tests/cross_cutting/" in run_script
    assert "--durations=50" in run_script


def test_e2e_cross_cutting_failures_are_quality_gated() -> None:
    """The owner job for e2e/cross-cutting coverage must block merges on failure."""
    quality_gate = _job("quality-gate")
    assert "e2e-cross-cutting" in quality_gate["needs"]

    run_script = _job_run_script("quality-gate", "Check all required jobs")
    assert "needs.e2e-cross-cutting.result" in run_script

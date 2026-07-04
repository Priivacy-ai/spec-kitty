"""Architectural guards for CI path-filter ownership."""

from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci-quality.yml"
_COLLECT_TIMEOUT_SECONDS = 240


def _load_workflow() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    return data


def _path_filters(data: dict[str, Any]) -> dict[str, list[str]]:
    filter_step = next(
        step for step in data["jobs"]["changes"]["steps"] if step.get("id") == "filter"
    )
    parsed: dict[str, list[str]] = yaml.safe_load(filter_step["with"]["filters"])
    return parsed


def _job_run_script(data: dict[str, Any], job_name: str, step_name: str) -> str:
    step = next(
        step
        for step in data["jobs"][job_name]["steps"]
        if step.get("name") == step_name
    )
    return str(step["run"])


def _job(data: dict[str, Any], job_name: str) -> dict[str, object]:
    return dict(data["jobs"][job_name])


# Marker selector shared by the legacy catch-all universe and every shard
# collection in test_core_misc_shards_plus_e2e_owner_cover_legacy_selection.
_MARKER_EXPR = "not windows_ci and (git_repo or integration or architectural)"

# The legacy catch-all core-misc selection (the pre-shard universe): every
# ``--ignore`` it carried plus its marker selector. Hoisted to a module
# constant so the ~117-line test body reads as intent, not literal data.
_LEGACY_CORE_MISC_ARGS: list[str] = [
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
    "-m",
    _MARKER_EXPR,
]

# The per-shard path/ignore universes whose union must cover the legacy
# selection. Each entry is collected with the same marker selector appended.
_SHARD_COMMANDS: list[list[str]] = [
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


def _collect_nodes(args: list[str]) -> set[str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-qq", *args],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        # Generous wall-clock (_COLLECT_TIMEOUT_SECONDS): these `--collect-only`
        # subprocesses run several at a time (see the worker-capped
        # ThreadPoolExecutor below), so on a CPU-constrained CI runner a single
        # collection's wall-clock can stretch well past a tight cap even though
        # it is fast in isolation.
        timeout=_COLLECT_TIMEOUT_SECONDS,
    )
    return {
        line.strip()
        for line in result.stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    }


def test_missions_filter_includes_missions_package_and_tests() -> None:
    """Mission package tests must both trigger and run the mission test slice."""
    data = _load_workflow()
    missions_filter = set(_path_filters(data)["missions"])
    assert "src/specify_cli/missions/**" in missions_filter
    assert "tests/fixtures/missions/**" in missions_filter
    assert "tests/specify_cli/missions/**" in missions_filter

    fast_run = _job_run_script(data, "fast-tests-missions", "Run fast tests — missions")
    integration_run = _job_run_script(
        data,
        "integration-tests-missions",
        "Run integration tests — missions",
    )
    assert "tests/specify_cli/missions/" in fast_run
    assert "tests/specify_cli/missions/" in integration_run


def test_lanes_filter_and_jobs_include_lanes_package_tests() -> None:
    """Lane package tests must both trigger and run the lane test slice."""
    data = _load_workflow()
    lanes_filter = set(_path_filters(data)["lanes"])
    assert "tests/specify_cli/lanes/**" in lanes_filter

    fast_run = _job_run_script(data, "fast-tests-lanes", "Run fast tests — lanes")
    integration_run = _job_run_script(
        data,
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
    data = _load_workflow()
    next_filter = set(_path_filters(data)["next"])
    assert "src/runtime/next/**" in next_filter
    assert "src/mission_runtime/**" in next_filter


def test_next_jobs_measure_canonical_runtime_coverage() -> None:
    """Both next suites must measure src/runtime/next, not only the shim."""
    data = _load_workflow()
    fast_run = _job_run_script(data, "fast-tests-next", "Run fast tests — next")
    integration_run = _job_run_script(
        data,
        "integration-tests-next",
        "Run integration tests — next",
    )
    assert "--cov=src/runtime/next" in fast_run
    assert "--cov=src/runtime/next" in integration_run


def test_diff_coverage_critical_paths_include_canonical_runtime() -> None:
    """The enforced diff-coverage gate must include the canonical runtime."""
    run_script = _job_run_script(
        _load_workflow(),
        "diff-coverage",
        "diff-coverage (critical-path, enforced)",
    )
    assert "'src/runtime/next/*'" in run_script
    assert "'src/mission_runtime/*'" in run_script


def test_execution_context_only_core_misc_runs_focused_parity_gate() -> None:
    """Execution-context-only changes must still run the CWD parity ratchet."""
    run_script = _job_run_script(
        _load_workflow(),
        "integration-tests-core-misc",
        "Run integration tests — core misc",
    )

    assert 'needs.changes.outputs.core_misc }}" != "true"' in run_script
    assert 'needs.changes.outputs.execution_context }}" = "true"' in run_script
    assert "tests/architectural/test_execution_context_parity.py" in run_script
    assert "coverage-integration-core-misc-${{ matrix.shard }}.xml" in run_script


def test_core_misc_integration_is_sharded_and_parallelized() -> None:
    """The slow core-misc integration bucket must stay split and parallel."""
    data = _load_workflow()
    job = _job(data, "integration-tests-core-misc")
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
        data,
        "integration-tests-core-misc",
        "Run integration tests — core misc",
    )
    assert "-n auto --dist loadfile" in run_script
    assert "--durations=50" in run_script


def test_ci_quality_guards_trigger_core_misc_validation() -> None:
    """CI workflow and architectural guard edits must run the validating shard."""
    core_misc_filter = set(_path_filters(_load_workflow())["core_misc"])
    assert ".github/workflows/ci-quality.yml" in core_misc_filter
    assert "tests/architectural/**" in core_misc_filter


def test_core_misc_shards_plus_e2e_owner_cover_legacy_selection() -> None:
    """The shard split must not drop tests covered by the legacy catch-all job.

    This compares the legacy catch-all node universe against the union of the
    new shard universes; the invariant is ``legacy_nodes - new_nodes == {}``
    over IDENTICAL path/marker universes. The 8 distinct ``--collect-only``
    subprocesses are launched concurrently (each is I/O-bound, waiting on a
    child pytest process) instead of serially. De-duplicating/parallelizing the
    distinct collections this way leaves node→selector attribution unchanged:
    every collection runs with the exact same args it ran with serially, and is
    bucketed back to ``legacy`` vs ``new`` by an explicit key — concurrency only
    overlaps the waits, it never merges or reattributes node sets.
    """
    marker_args = ["-m", _MARKER_EXPR]
    e2e_args = [
        "tests/e2e",
        "tests/cross_cutting",
        "-m",
        "not distribution and not windows_ci",
    ]

    # (bucket, args) for each distinct collection. "legacy" feeds the catch-all
    # universe; "new" feeds the union of shard universes. Attribution is fixed
    # here, before any concurrency, so parallel execution cannot change it.
    collections: list[tuple[str, list[str]]] = [("legacy", _LEGACY_CORE_MISC_ARGS)]
    collections.extend(
        ("new", [*command, *marker_args]) for command in _SHARD_COMMANDS
    )
    collections.append(("new", e2e_args))

    # Each _collect_nodes call spawns a child pytest process and blocks on it;
    # run them concurrently so the wall-clock is bounded by the slowest single
    # collection instead of their serial sum. Cap concurrency at the CPU count
    # (min 2): launching all of them at once oversubscribes a 2-core CI runner,
    # which inflates each child's wall-clock and made a single collection blow
    # its per-subprocess timeout. Pacing to the available cores keeps each
    # collection fast without serialising the whole set.
    max_workers = min(len(collections), max(2, os.cpu_count() or 2))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(
            executor.map(lambda item: (item[0], _collect_nodes(item[1])), collections),
        )

    legacy_nodes: set[str] = set()
    new_nodes: set[str] = set()
    for bucket, nodes in results:
        (legacy_nodes if bucket == "legacy" else new_nodes).update(nodes)

    missing = sorted(legacy_nodes - new_nodes)
    assert not missing, "Shard split dropped legacy core-misc tests:\n" + "\n".join(
        missing[:20],
    )


def test_core_misc_excludes_e2e_and_cross_cutting_suites() -> None:
    """E2E and cross-cutting suites belong to e2e-cross-cutting, not core-misc."""
    data = _load_workflow()
    path_filters = _path_filters(data)
    assert "tests/e2e/**" not in path_filters["core_misc"]
    assert "tests/cross_cutting/**" not in path_filters["core_misc"]
    assert "tests/e2e/**" in path_filters["e2e"]
    assert "tests/cross_cutting/**" in path_filters["e2e"]

    fast_run = _job_run_script(data, "fast-tests-core-misc", "Run fast tests — core misc")
    assert "--ignore=tests/e2e" in fast_run
    assert "--ignore=tests/cross_cutting" in fast_run

    job = _job(data, "integration-tests-core-misc")
    matrix = job["strategy"]["matrix"]["include"]  # type: ignore[index]
    matrix_text = "\n".join(
        f"{entry.get('paths', '')}\n{entry.get('ignore_args', '')}" for entry in matrix
    )
    assert "tests/e2e" not in matrix_text
    assert "tests/cross_cutting" not in matrix_text


def test_e2e_cross_cutting_runs_independently_of_fast_fanout() -> None:
    """The dedicated e2e job should not wait on unrelated fast-test shards."""
    data = _load_workflow()
    job = _job(data, "e2e-cross-cutting")
    assert job["needs"] == ["changes"]

    condition = str(job["if"])
    assert "needs.changes.outputs.e2e == 'true'" in condition
    assert "needs.changes.outputs.core_misc == 'true'" in condition
    assert "needs.changes.outputs.execution_context == 'true'" in condition

    path_filters = _path_filters(data)
    assert ".github/workflows/ci-quality.yml" in path_filters["e2e"]

    run_script = _job_run_script(
        data,
        "e2e-cross-cutting",
        "[ENFORCED] Run e2e and cross_cutting tests with coverage",
    )
    assert "tests/e2e/ tests/cross_cutting/" in run_script
    assert "--durations=50" in run_script


def test_e2e_cross_cutting_failures_are_quality_gated() -> None:
    """The owner job for e2e/cross-cutting coverage must block merges on failure.

    Post-FR-011 (mission ci-suite-map-bind WP03) the quality-gate verdict is
    computed by ``scripts/ci/quality_gate_decision.py`` over the FULL needs
    context (``toJSON(needs)``): membership in ``needs:`` IS the blocking
    relation (a failed/cancelled needs job always fails the gate), so the old
    literal per-job ``needs.<job>.result`` read this test used to pin cannot
    silently omit a job anymore.
    """
    quality_gate = _job(_load_workflow(), "quality-gate")
    assert "e2e-cross-cutting" in quality_gate["needs"]

    decision_step = next(
        step
        for step in quality_gate["steps"]
        if step.get("name") == "Evaluate quality-gate decision"
    )
    assert decision_step["env"]["NEEDS_JSON"] == "${{ toJSON(needs) }}"
    assert "scripts/ci/quality_gate_decision.py" in decision_step["run"]
    # The decision script pipes into ``tee -a "$GITHUB_STEP_SUMMARY"``. Under
    # GitHub's default ``bash -e {0}`` (no pipefail) the pipe returns tee's
    # always-zero exit, SWALLOWING the script's blocking (exit 1) / contract
    # (exit 2) verdict — the gate would be vacuous. ``shell: bash`` makes
    # GitHub run ``bash --noprofile --norc -eo pipefail {0}`` so the script's
    # non-zero propagates through the pipe. Pin it so the mask cannot return.
    assert decision_step.get("shell") == "bash", (
        "quality-gate decision step must set ``shell: bash`` so pipefail is "
        "enabled and the script's non-zero exit is not swallowed by ``| tee``"
    )

"""Fail closed when CI path filters create a test-coverage hole."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from tests.architectural import _gate_coverage as gc

pytestmark = pytest.mark.architectural

_CI_QUALITY = gc.WORKFLOWS_DIR / "ci-quality.yml"
_ANY_SRC = "any_src"
_FILTER_OUTPUT_RE = re.compile(r"steps\.filter\.outputs\.(\w+)")


def unmatched_group_refs(workflow_path: Path) -> set[str]:
    data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = (data.get("jobs") or {}).get("changes", {}).get("steps") or []
    unmatched: dict[str, object] = next(
        (step for step in steps if step.get("id") == "unmatched"), {}
    )
    text = str(unmatched.get("run", "")) + " " + str(unmatched.get("env", ""))
    return set(_FILTER_OUTPUT_RE.findall(text)) - {_ANY_SRC}


def src_backed_groups(model: gc.WorkflowModel) -> set[str]:
    return {
        name
        for name, globs in model.filter_groups.items()
        if name != _ANY_SRC and any(glob.startswith("src/") for glob in globs)
    }


def _is_whole_tree(gate: gc.Gate) -> bool:
    return not gate.paths or all(path.rstrip("/") == "tests" for path in gate.paths)


def _is_dir_root(path: str) -> bool:
    return "::" not in path and not path.endswith(".py")


def catch_all_ignore_violations(gates: list[gc.Gate]) -> list[str]:
    violations: list[str] = []
    catch_alls = [gate for gate in gates if _is_whole_tree(gate) and len(gate.ignores) >= 2]
    for catch_all in catch_alls:
        ignored = {path.rstrip("/") for path in catch_all.ignores if _is_dir_root(path)}
        owned = {
            path.rstrip("/")
            for gate in gates
            if gate.job != catch_all.job and not _is_whole_tree(gate)
            for path in gate.paths
            if _is_dir_root(path)
        }
        if spurious := ignored - owned:
            violations.append(
                f"{catch_all.label()} ignores roots owned by no shard: {sorted(spurious)}"
            )
    return violations


def _ci_quality_model() -> gc.WorkflowModel:
    return gc.load_workflow_model(_CI_QUALITY)


def _ci_quality_gates() -> list[gc.Gate]:
    return [gate for gate in gc.load_gates() if gate.workflow == "ci-quality.yml"]


def test_unmatched_refs_equal_parsed_filter_groups_live() -> None:
    """Every src filter participates in the fail-closed unmatched route."""
    model = _ci_quality_model()
    expected = src_backed_groups(model)
    refs = unmatched_group_refs(_CI_QUALITY)
    assert refs == expected, (
        f"only-in-catchall={sorted(refs - expected)}, "
        f"only-in-src-backed={sorted(expected - refs)}"
    )


def test_every_named_group_gates_a_test_running_job_live() -> None:
    """Reject filter groups that can suppress all test-running jobs."""
    model = _ci_quality_model()
    test_jobs = {gate.job for gate in _ci_quality_gates()}
    ungated = [
        group
        for group in sorted(set(model.filter_groups) - {_ANY_SRC})
        if not any(
            group in model.job_gating_groups.get(job, frozenset()) for job in test_jobs
        )
    ]
    assert not ungated, f"filter groups gating no test-running job: {ungated}"


def test_catch_all_ignore_lists_mirror_owned_roots_live() -> None:
    """Reject catch-all ignores that no dedicated test shard owns."""
    violations = catch_all_ignore_violations(_ci_quality_gates())
    assert not violations, "\n".join(violations)

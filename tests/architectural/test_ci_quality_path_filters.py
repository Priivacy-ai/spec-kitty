"""Architectural guards for CI path-filter ownership.

The restored interim ``ci-quality.yml`` deliberately has no path filter: the
five-job producer is small enough to run on every pull request and main push.
The live checks below bind that trigger shape and stock-runner contract; the
old full-matrix path-filter relations remain retired with the deferred module
workflows.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CI_QUALITY = _REPO_ROOT / ".github" / "workflows" / "ci-quality.yml"


def _load_workflow() -> dict[str, Any]:
    return yaml.safe_load(_CI_QUALITY.read_text(encoding="utf-8"))


def test_reduced_ci_quality_runs_without_path_filters_live() -> None:
    workflow = _load_workflow()
    on_section = workflow.get("on") or workflow[True]

    for event in ("pull_request", "push"):
        assert "paths" not in on_section[event]


def test_reduced_ci_quality_uses_stock_runners_live() -> None:
    workflow = _load_workflow()
    text = _CI_QUALITY.read_text(encoding="utf-8")

    assert {job["runs-on"] for job in workflow["jobs"].values()} == {"ubuntu-latest"}
    assert "blacksmith" not in text.lower()
    assert "runner-group" not in text.lower()


def _is_direct_pytest_quarantine_marker(node: ast.AST) -> bool:
    """Return whether *node* is the canonical ``pytest.mark.quarantine`` chain."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "quarantine"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "pytest"
    )


def _discover_quarantine_owner_paths(tests_root: Path) -> tuple[str, ...]:
    """Find test files that directly use the canonical quarantine marker."""
    repository_root = tests_root.parent
    owners: list[str] = []
    for test_path in sorted(tests_root.rglob("*.py")):
        tree = ast.parse(test_path.read_text(encoding="utf-8"), filename=str(test_path))
        if any(_is_direct_pytest_quarantine_marker(node) for node in ast.walk(tree)):
            owners.append(test_path.relative_to(repository_root).as_posix())
    return tuple(owners)


def test_quarantine_marker_discovery_finds_module_and_function_markers(
    tmp_path: Path,
) -> None:
    """The owner-manifest guard must discover every direct quarantine marker."""
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_module_marker.py").write_text(
        "import pytest\n\npytestmark = [pytest.mark.quarantine]\n",
        encoding="utf-8",
    )
    (tests_root / "test_function_marker.py").write_text(
        "import pytest\n\n@pytest.mark.quarantine\ndef test_flake():\n    pass\n",
        encoding="utf-8",
    )
    (tests_root / "test_unmarked.py").write_text(
        "def test_stable():\n    pass\n",
        encoding="utf-8",
    )

    assert _discover_quarantine_owner_paths(tests_root) == (
        "tests/test_function_marker.py",
        "tests/test_module_marker.py",
    )


# T021 (mission review-cycle-verdict-seam-rebuild-01KZ2W7W, WP05): a shard job
# must not condition its own execution on a predecessor's `.result` — it
# should still run and report its own outcome regardless of whether the
# predecessor passed or failed. This regex catches both classes of gate this
# WP removed: `needs.<job>.result != 'failure'` (Class 1, e.g. a coverage
# shard gated on kernel-tests/fast-tests-status) and `needs.<job>.result ==
# 'success'` (Class 2, an integration-tests-* job gated on its fast-tests-*
# counterpart).
_RESULT_GATE_PATTERN = re.compile(r"needs\.[\w-]+\.result\s*(?:!=\s*'failure'|==\s*'success')")

# Single named, justified exception (see the DoD in
# kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/tasks/WP05-ci-shard-independence.md):
# ``consumer-compatibility``'s ``needs.build-wheel.result == 'success'`` gate
# is a release-packaging aggregator dependency (a wheel it consumes), not a
# coverage-shard result-gate the way the removed edges were — build-wheel
# produces the artifact consumer-compatibility installs, so gating on its
# result is a genuine "don't bother installing a wheel that was never built"
# check, not the redundant "predecessor's test outcome shouldn't block my own
# report" coupling this test exists to forbid. This is a single named
# constant, not a general allowlist: any job matching the pattern that is NOT
# named here fails the test below, and adding a name here requires the same
# explicit justification as this comment.
_NON_SHARD_AGGREGATOR_EXCEPTIONS = frozenset({"consumer-compatibility"})


def _find_result_gated_jobs(jobs: dict[str, Any]) -> dict[str, str]:
    """Return ``{job_name: if_expr}`` for jobs gating on a predecessor's ``.result``.

    A job's ``if:`` arrives here, post-PyYAML-parse, as one of three shapes: a
    plain string, a folded ``>-`` block scalar (also just a ``str`` once
    parsed), or absent (key missing, defaults to always-run) — all three are
    handled uniformly by coercing to ``str`` and skipping ``None``.
    """
    offending: dict[str, str] = {}
    for job_name, job in jobs.items():
        if job_name in _NON_SHARD_AGGREGATOR_EXCEPTIONS:
            continue
        if_expr = job.get("if") if isinstance(job, dict) else None
        if if_expr is None:
            continue
        if _RESULT_GATE_PATTERN.search(str(if_expr)):
            offending[job_name] = str(if_expr)
    return offending


def test_result_gate_checker_catches_a_reintroduced_gate() -> None:
    """Synthetic-poison proof that ``_find_result_gated_jobs`` reds on a new gate.

    Permanent regression proof for T021: constructs a minimal synthetic
    ``jobs`` mapping containing a deliberately (re)introduced Class 1 style
    gate (``!= 'failure'``, folded ``if: >-`` block shape) and a Class 2 style
    gate (``== 'success'``), alongside an ungated job and a job with no ``if:``
    key at all, and confirms the checker flags exactly the two poisoned jobs.
    This is what proves the checker actually catches the regression it exists
    to prevent — not merely that it currently passes against an
    already-fixed workflow.
    """
    poisoned_jobs = {
        "fast-tests-example": {
            "if": (
                "always()\n"
                "&& (needs.changes.outputs.example == 'true' || github.event_name == 'push')\n"
                "&& needs.fast-tests-status.result != 'failure'\n"
            ),
        },
        "integration-tests-example": {
            "if": (
                "always()\n"
                "&& (needs.changes.outputs.example == 'true' || github.event_name == 'push')\n"
                "&& needs.fast-tests-example.result == 'success'\n"
            ),
        },
        "clean-job": {
            "if": "always() && (needs.changes.outputs.example == 'true' || github.event_name == 'push')",
        },
        "no-if-job": {},
        "consumer-compatibility": {
            "if": "always() && needs.changes.outputs.release == 'true' && needs.build-wheel.result == 'success'",
        },
    }
    offending = _find_result_gated_jobs(poisoned_jobs)
    assert set(offending) == {"fast-tests-example", "integration-tests-example"}

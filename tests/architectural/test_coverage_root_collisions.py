"""Coverage targets resolve and cannot silently overwrite each other.

Authority: open CI-integrity epic #1931.  The two live workflow/filesystem
oracles remain; three synthetic checker tests from closed issue #2975 do not.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.architectural import _gate_coverage as gc

if TYPE_CHECKING:
    from collections.abc import Mapping

pytestmark = pytest.mark.architectural


def _targets_by_job(
    models: Mapping[str, gc.WorkflowModel],
) -> dict[str, frozenset[str]]:
    return {
        f"{workflow}:{job}": targets
        for workflow, model in models.items()
        for job, targets in model.cov_targets.items()
        if targets and job not in gc.NON_EMITTER_JOBS
    }


def _target_resolves(target: str, repo_root: Path) -> bool:
    if "/" in target:
        return (repo_root / target).is_dir()
    rel = target.replace(".", "/")
    return (repo_root / "src" / rel).is_dir() or (
        repo_root / "src" / f"{rel}.py"
    ).is_file()


def _collisions(
    targets_by_job: Mapping[str, frozenset[str]],
    repo_root: Path,
) -> dict[tuple[str, str], tuple[str, str]]:
    collisions: dict[tuple[str, str], tuple[str, str]] = {}
    for job, targets in targets_by_job.items():
        roots = sorted(
            target
            for target in targets
            if "/" in target and (repo_root / target).is_dir()
        )
        seen: dict[str, str] = {}
        for root in roots:
            for source in (repo_root / root).rglob("*.py"):
                rel = source.relative_to(repo_root / root).as_posix()
                prior = seen.setdefault(rel, root)
                if prior != root:
                    collisions[(job, rel)] = (prior, root)
    return collisions


def test_every_coverage_target_resolves() -> None:
    targets = _targets_by_job(gc.load_workflow_models())
    assert targets, "no coverage-emitting jobs parsed"
    unresolved = sorted(
        target
        for job_targets in targets.values()
        for target in job_targets
        if not _target_resolves(target, gc.REPO_ROOT)
    )
    assert not unresolved, f"unresolvable --cov targets: {unresolved}"


def test_path_form_coverage_roots_do_not_collide() -> None:
    targets = _targets_by_job(gc.load_workflow_models())
    assert targets, "no coverage-emitting jobs parsed"
    collisions = _collisions(targets, gc.REPO_ROOT)
    assert not collisions, f"colliding coverage roots: {collisions}"

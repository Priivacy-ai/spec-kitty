"""Coverage-root reality + collision guard (#2975).

Two independent defect classes were found in ``ci-quality.yml``'s ``--cov``
invocations, both traced to the same upstream mechanism
(``coverage.py``'s ``XmlReporter.source_paths``, populated only from
``--cov`` targets that are *existing directories* -- ``xmlreport.py`` L67-74):

* **Collision.** Once >=2 such directories are co-instrumented in one pytest
  invocation, coverage.py's dict-overwrite (``report_core.py:96``, iterating
  ``sorted(fr_morfs)``) keeps only the alphabetically-last root's data for
  every relative path both roots contain (e.g. ``__init__.py``) and silently
  drops the rest. Measured on a real invocation of this repo's
  ``specify_cli + charter + doctrine`` job: header ``lines-valid=108519`` vs
  summed ``<class>`` statements ``108349`` -- 170 statements / 6 files
  silently absent, with no error anywhere in the pipeline.
* **Dead root.** A ``--cov`` target that names a directory that does not
  exist (e.g. ``src/specify_cli/mission`` when the real surface is
  ``src/specify_cli/mission.py``) never reaches ``source_paths`` either, so
  it produces ZERO collisions -- but also measures NOTHING. A collision-only
  guard would have passed those jobs while they silently measured zero
  coverage for their primary target.

The fix (this PR) converts every multi-root invocation's ``--cov`` targets to
dotted importable-module form (``--cov=specify_cli`` instead of
``--cov=src/specify_cli``), which keeps ``source_paths`` empty and makes the
collision structurally impossible. This module guards BOTH defect classes
against regression, over the SAME canonical parser the rest of the CI
architectural suite uses (DIRECTIVE_044): ``_gate_coverage.load_workflow_models``
/ ``WorkflowModel.cov_targets`` -- no second workflow parser is written here.

Both invariants are asserted as SET equality (never ``len(x) == N`` --
``test_golden_count_ban.py``), and both carry a red-negative fault-injection
proof (``_workflow_fixtures.write_workflow``) showing the guard can actually
fail, not just pass vacuously.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.architectural import _gate_coverage as gc
from tests.architectural._workflow_fixtures import write_workflow

if TYPE_CHECKING:
    from collections.abc import Mapping

pytestmark = [pytest.mark.architectural]


# ---------------------------------------------------------------------------
# Pure relation primitives (fault-injection substrate).
# ---------------------------------------------------------------------------


def _flat_cov_targets_by_job(
    models: Mapping[str, gc.WorkflowModel],
) -> dict[str, frozenset[str]]:
    """``"<workflow>:<job>" -> cov targets`` across every parsed workflow.

    Jobs with no ``--cov`` targets (lint/build/consumer jobs) are dropped --
    they carry nothing for either invariant to check. ``gc.NON_EMITTER_JOBS``
    (``sonarcloud`` et al.) is also dropped: those jobs' scripts carry prose
    ``--cov=...`` *examples* in comments/heredoc documentation, which
    ``_COV_TARGET_RE`` cannot distinguish from a real flag -- the same reason
    ``test_coverage_consumer_needs.py`` excludes them from its emitter set.
    """
    flat: dict[str, frozenset[str]] = {}
    for wf_name, model in models.items():
        for job, targets in model.cov_targets.items():
            if targets and job not in gc.NON_EMITTER_JOBS:
                flat[f"{wf_name}:{job}"] = targets
    return flat


def _target_resolves(target: str, repo_root: Path) -> bool:
    """Whether a single ``--cov`` target names something coverage.py can measure.

    Path-form (contains ``/``): must be an existing directory relative to
    ``repo_root`` -- the same existence check ``XmlReporter.source_paths``
    performs.

    Dotted/bare module form (no ``/``): must resolve under ``src/`` to either
    a subpackage directory (``specify_cli.charter_runtime`` ->
    ``src/specify_cli/charter_runtime/``) or a bare ``.py`` module
    (``specify_cli.mission`` -> ``src/specify_cli/mission.py``). Both shapes
    are empirically proven measurable (#2975 research); the ``.py``-module
    case specifically was NOT proven before this PR (only the subpackage case
    was) and was verified directly before this guard was written.
    """
    if "/" in target:
        return (repo_root / target).is_dir()
    rel = target.replace(".", "/")
    return (repo_root / "src" / rel).is_dir() or (repo_root / "src" / f"{rel}.py").is_file()


def unresolvable_cov_targets(
    cov_targets_by_job: Mapping[str, frozenset[str]], repo_root: Path
) -> frozenset[str]:
    """Every ``--cov`` target, across all jobs, that resolves to nothing real.

    Deliberately broader than a collision check: a dead root (e.g.
    ``--cov=src/specify_cli/mission`` before this PR) produces ZERO
    collisions -- coverage.py drops it before ``source_paths`` is even built
    -- while measuring NOTHING for its job. A collision-only guard would have
    reported those jobs clean.
    """
    return frozenset(
        target
        for targets in cov_targets_by_job.values()
        for target in targets
        if not _target_resolves(target, repo_root)
    )


def _path_form_existing_roots(targets: frozenset[str], repo_root: Path) -> list[str]:
    """A job's ``--cov`` targets that are path-form AND resolve to a real dir.

    This is exactly the set coverage.py's ``XmlReporter.source_paths`` would
    populate for the invocation -- the collision precondition.
    """
    return sorted(t for t in targets if "/" in t and (repo_root / t).is_dir())


def real_tree_collisions(
    cov_targets_by_job: Mapping[str, frozenset[str]], repo_root: Path
) -> dict[tuple[str, str], tuple[str, str]]:
    """Emulate coverage.py's cross-root basename collision over the real tree.

    For every job with >=2 path-form existing-directory roots, walk each
    root's ``*.py`` files and record the FIRST root claiming each relative
    path; a second root claiming the same relative path is a collision --
    exactly the condition under which coverage.py's dict-overwrite
    (``report_core.py:96``) silently keeps one root's data and drops the
    other's.

    Returns ``(job, relpath) -> (root_a, root_b)`` (both sides named, per the
    task) for every colliding relative path found.
    """
    collisions: dict[tuple[str, str], tuple[str, str]] = {}
    for job, targets in cov_targets_by_job.items():
        roots = _path_form_existing_roots(targets, repo_root)
        if len(roots) < 2:
            continue
        seen: dict[str, str] = {}
        for root in roots:
            root_path = repo_root / root
            for f in root_path.rglob("*.py"):
                rel = str(f.relative_to(root_path))
                owner = seen.get(rel)
                if owner is not None and owner != root:
                    collisions[(job, rel)] = (owner, root)
                else:
                    seen.setdefault(rel, root)
    return collisions


# ---------------------------------------------------------------------------
# Live invariants over the real workflow files.
# ---------------------------------------------------------------------------


def test_every_cov_target_resolves_to_something_real() -> None:
    """Every ``--cov`` root, across all 5 modeled workflows, measures something.

    Catches the dead-root defect class (#2975 commit 2:
    ``--cov=src/specify_cli/mission`` / ``mission_metadata`` pointed at
    directories that never existed) that a collision-only check would miss
    entirely -- a dead root never reaches ``source_paths``, so it never
    collides, it just silently measures zero.
    """
    cov_targets_by_job = _flat_cov_targets_by_job(gc.load_workflow_models())
    unresolvable = unresolvable_cov_targets(cov_targets_by_job, gc.REPO_ROOT)
    assert unresolvable == set(), (
        "--cov targets that resolve to no real directory or importable "
        f"module: {sorted(unresolvable)}"
    )


def test_no_multi_root_invocation_collides_on_the_real_tree() -> None:
    """No job's path-form ``--cov`` roots share a same-relative-path file.

    Emulates coverage.py's prefix-strip collision directly against the
    filesystem: for every job with >=2 existing path-form roots, walk both
    trees and check whether any relative path (e.g. ``__init__.py``) exists
    under more than one root. A real hit is silent data loss -- only one
    root's version of that file ever reaches Sonar / diff-cover. #2975
    commit 1 converted every such invocation to dotted module form, which
    keeps ``source_paths`` empty and makes this structurally impossible; this
    is the regression guard against a future job reintroducing >=2 path-form
    roots.
    """
    cov_targets_by_job = _flat_cov_targets_by_job(gc.load_workflow_models())
    collisions = real_tree_collisions(cov_targets_by_job, gc.REPO_ROOT)
    assert collisions == {}, (
        "path-form --cov roots collide on a real relative path -- "
        f"(job, relpath) -> (root_a, root_b): {collisions}"
    )


# ---------------------------------------------------------------------------
# Red-negatives: prove both guards can actually fail (fault injection).
# ---------------------------------------------------------------------------


def test_reality_guard_reds_on_a_synthetic_dead_root(tmp_path: Path) -> None:
    """A --cov target with no real directory/module must be caught.

    Mirrors the exact pre-fix defect (``--cov=src/specify_cli/mission``): a
    guard that only checked for collisions would pass this workflow, because
    a dead root never collides. Proves the reality invariant, not just the
    collision invariant, is load-bearing.
    """
    path = write_workflow(
        tmp_path,
        """\
        name: fixture
        on: push
        jobs:
          fixture-job:
            runs-on: ubuntu-latest
            steps:
              - run: |
                  uv run pytest tests/ \\
                    --cov=src/this_package_does_not_exist \\
                    --cov-report=xml
        """,
    )
    model = gc.load_workflow_model(path)
    unresolvable = unresolvable_cov_targets(
        {"fixture.yml:fixture-job": model.cov_targets["fixture-job"]},
        gc.REPO_ROOT,
    )
    assert unresolvable == {"src/this_package_does_not_exist"}, (
        "the reality guard failed to flag an injected dead --cov root -- "
        "a guard that cannot fail is worthless"
    )


def test_collision_guard_reds_on_a_synthetic_colliding_invocation(
    tmp_path: Path,
) -> None:
    """A two-existing-root invocation that shares a relative path must be caught.

    Uses two REAL existing directories (``src/charter``, ``src/doctrine``)
    that both contain ``__init__.py``, so the emulated prefix-strip walk hits
    a genuine same-relative-path collision on the real tree -- the exact
    defect class commit 1 removed from the live workflow (that job now uses
    ``--cov=charter --cov=doctrine``, the dotted form asserted safe below).
    """
    path = write_workflow(
        tmp_path,
        """\
        name: fixture
        on: push
        jobs:
          fixture-job:
            runs-on: ubuntu-latest
            steps:
              - run: |
                  uv run pytest tests/ \\
                    --cov=src/charter --cov=src/doctrine \\
                    --cov-report=xml
        """,
    )
    model = gc.load_workflow_model(path)
    collisions = real_tree_collisions(
        {"fixture.yml:fixture-job": model.cov_targets["fixture-job"]},
        gc.REPO_ROOT,
    )
    assert ("fixture.yml:fixture-job", "__init__.py") in collisions, (
        "the collision guard failed to flag an injected src/charter + "
        "src/doctrine collision -- a guard that cannot fail is worthless"
    )


def test_collision_guard_is_clean_on_the_dotted_remediation(tmp_path: Path) -> None:
    """Benign twin: the same job converted to dotted form has zero collisions.

    Proves the collision check is not a false-positive trap that would red
    the exact remediation #2975 applied to the live workflow.
    """
    path = write_workflow(
        tmp_path,
        """\
        name: fixture
        on: push
        jobs:
          fixture-job:
            runs-on: ubuntu-latest
            steps:
              - run: |
                  uv run pytest tests/ \\
                    --cov=charter --cov=doctrine \\
                    --cov-report=xml
        """,
    )
    model = gc.load_workflow_model(path)
    collisions = real_tree_collisions(
        {"fixture.yml:fixture-job": model.cov_targets["fixture-job"]},
        gc.REPO_ROOT,
    )
    assert collisions == {}

"""Workflow-coherence relation primitives (FR-003/FR-005/FR-008/FR-011, WP04).

These bound the delivery-topology relations this mission owns, over the SAME
parsed model as the marker invariant (``_gate_coverage.WorkflowModel``):

  FR-003a  every ``needs.<job>.result`` read is declared in that job's ``needs:``
  FR-003b  every dorny filter output (except the ``any_src`` probe) is consumed
           by >=1 job ``if:``
  FR-003c  every filter glob matches >=1 tracked path
  FR-003d  the quality-gate verdict consumes ``toJSON(needs)`` and reads ZERO
           literal ``needs.<job>.result`` — membership in ``needs:`` IS the
           blocking authority (WP03 reshape; a literal read reappearing = drift)
  FR-005   every diff-cover critical-path entry is backed by >=1 ``--cov`` emitter
  FR-008   the pytest-invoking-workflow set == the parse model's allowlist
           (a fifth suite-running workflow fails closed)
  FR-011   the quality-gate JOB_GROUPS table == the parsed job-``if:`` gating map
           (Decision 8 two-authority rule; ``quarantine-visibility`` stays out of
           the blocking set, C-005)

The interim convergence topology restores ``ci-windows.yml`` and a reduced
``ci-quality.yml``. The live checks below re-open the subset of the former
relations that those two files can support; the old five-workflow suite-model
relations remain retired until the deferred topology workflows are restored.

WHAT REMAINS: the pure relation primitives below (``needs_declaration_violations``,
``unconsumed_filter_groups``, ``glob_is_live``, ``critical_path_backed_by``,
``parse_job_groups``) never read a real workflow file — each is exercised only
against a ``WorkflowModel`` built from FIXTURE YAML (``_workflow_fixtures``) or
literal data constructed in-line by the ``test_faultinjection_*`` tests, so
they keep proving each relation actually reds on a planted violation
regardless of whether any workflow YAML exists on disk.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from typing import TYPE_CHECKING

import pytest

from tests.architectural import _gate_coverage as gc
from tests.architectural._workflow_fixtures import filter_workflow, write_workflow

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

# ``"job-name": [ "grp", ... ]`` rows of the JOB_GROUPS heredoc (FR-011).
_JOB_GROUPS_ROW_RE = re.compile(r'"([\w-]+)":\s*\[([^\]]*)\]')
_QUOTED_RE = re.compile(r'"([\w-]+)"')


# ---------------------------------------------------------------------------
# Pure relation primitives (fault-injection substrate).
# ---------------------------------------------------------------------------


def _tracked_paths() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=gc.REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return set(result.stdout.splitlines())


def test_needs_result_reads_are_declared_live() -> None:
    """FR-003a: no phantom ``needs.<job>.result`` read in a restored workflow."""
    for name in gc.WORKFLOW_FILES:
        model = gc.load_workflow_model(gc.WORKFLOWS_DIR / name)
        violations = needs_declaration_violations(model)
        assert not violations, f"{name}:\n" + "\n".join(violations)


def test_every_restored_filter_group_is_consumed_live() -> None:
    """FR-003b: every named filter group gates at least one job."""
    for name in gc.WORKFLOW_FILES:
        model = gc.load_workflow_model(gc.WORKFLOWS_DIR / name)
        unconsumed = unconsumed_filter_groups(model)
        assert not unconsumed, f"{name}: unconsumed filter groups {sorted(unconsumed)}"


def test_every_restored_filter_glob_is_live() -> None:
    """FR-003c: no restored filter glob names a nonexistent tracked path."""
    tracked = _tracked_paths()
    for name in gc.WORKFLOW_FILES:
        model = gc.load_workflow_model(gc.WORKFLOWS_DIR / name)
        dead = [
            (group, glob)
            for group, globs in model.filter_groups.items()
            for glob in globs
            if not glob_is_live(glob, tracked)
        ]
        assert not dead, f"{name}: dead filter globs {dead}"


def test_pytest_workflow_set_equals_model_allowlist_live() -> None:
    """FR-008: every discovered pytest workflow is intentionally modeled."""
    assert gc.discover_pytest_workflows() == frozenset(gc.WORKFLOW_FILES)


def test_reduced_quality_gate_has_no_literal_result_reads_live() -> None:
    """FR-003d: the reduced gate consumes the complete needs context as JSON."""
    model = gc.load_workflow_model(gc.WORKFLOWS_DIR / "ci-quality.yml")
    text = (gc.WORKFLOWS_DIR / "ci-quality.yml").read_text(encoding="utf-8")

    assert model.needs_result_reads["quality-gate"] == frozenset()
    assert "NEEDS_JSON: ${{ toJSON(needs) }}" in text


def needs_declaration_violations(model: gc.WorkflowModel) -> list[str]:
    """FR-003a: every ``needs.<job>.result`` read declared in that job's needs."""
    out: list[str] = []
    for job, reads in model.needs_result_reads.items():
        undeclared = reads - set(model.job_needs.get(job, ()))
        if undeclared:
            out.append(f"job {job!r} reads needs.<x>.result for undeclared job(s) {sorted(undeclared)} (declared needs: {sorted(model.job_needs.get(job, ()))})")
    return out


def unconsumed_filter_groups(model: gc.WorkflowModel) -> set[str]:
    """FR-003b: filter groups (minus the ``any_src`` probe) with no job ``if:`` consumer."""
    consumed: set[str] = set()
    for groups in model.job_gating_groups.values():
        consumed |= set(groups)
    return (set(model.filter_groups) - {"any_src"}) - consumed


def glob_is_live(glob: str, tracked: set[str]) -> bool:
    """FR-003c: does ``glob`` match >=1 tracked path?

    The trailing-``/**`` fast path below is a literal prefix check, which is
    only valid when nothing EARLIER in the glob is itself a wildcard (e.g.
    ``docs/**``). A glob with a wildcard segment before the trailing ``/**``
    (e.g. ``kitty-specs/**/tasks/**``, mission ci-scoping-gate-reliability
    #3008) would make that prefix contain a literal ``*`` character, which
    can never match a real tracked path -- a false "dead glob" negative, not
    a real one. Route those through the general ``fnmatch`` branch instead,
    which correctly treats every ``*``/``**`` as a wildcard throughout.
    """
    normalized = glob.rstrip("/")
    if normalized.endswith("/**") and "*" not in normalized[:-3]:
        prefix = normalized[:-3].rstrip("/") + "/"
        return any(path.startswith(prefix) for path in tracked)
    if "*" in normalized:
        return any(fnmatch.fnmatch(path, normalized) for path in tracked)
    return normalized in tracked or any(path.startswith(normalized + "/") for path in tracked)


def critical_path_backed_by(entry: str, cov_targets: set[str]) -> str | None:
    """FR-005: a ``--cov`` target that is an ancestor-or-equal of ``entry``, if any.

    ``cov_targets`` may hold either shape a ``--cov`` flag takes since #2975
    (a ``src/``-relative path or a dotted module, e.g.
    ``specify_cli.charter_runtime``); both are normalized to the same
    ``src/``-relative form via ``gc.cov_target_repo_path`` before comparing,
    so a dotted emitter still backs its critical-path entry.
    """
    package = entry[:-2] if entry.endswith("/*") else entry
    package = package.rstrip("/")
    for cov in cov_targets:
        target = gc.cov_target_repo_path(cov)
        if package == target or package.startswith(target + "/"):
            return cov
    return None


def parse_job_groups(quality_gate_run_text: str) -> dict[str, set[str]]:
    """Parse the ``JOB_GROUPS = { ... }`` heredoc dict into ``job -> {groups}``."""
    match = re.search(r"JOB_GROUPS\s*=\s*\{(.*?)\}\s*\n", quality_gate_run_text, re.DOTALL)
    assert match, "JOB_GROUPS table not found in the quality-gate decision step"
    return {row.group(1): set(_QUOTED_RE.findall(row.group(2))) for row in _JOB_GROUPS_ROW_RE.finditer(match.group(1))}



# ---------------------------------------------------------------------------
# Fault-injection (per relation, fixture YAML / fixture data).
# ---------------------------------------------------------------------------


def test_faultinjection_undeclared_needs_read_reds(tmp_path: Path) -> None:
    """FR-003a: a ``needs.ghost.result`` read without a declaration reds."""
    wf = write_workflow(
        tmp_path,
        """\
        name: fixture
        on: push
        jobs:
          agg:
            needs: [a]
            runs-on: ubuntu-latest
            steps:
              - run: echo "${{ needs.ghost.result }}"
          a:
            runs-on: ubuntu-latest
            steps:
              - run: echo hi
        """,
    )
    violations = needs_declaration_violations(gc.load_workflow_model(wf))
    assert any("ghost" in v for v in violations), violations


def test_faultinjection_unconsumed_filter_group_reds(tmp_path: Path) -> None:
    """FR-003b: a filter group gated by no job ``if:`` reds."""
    wf = write_workflow(
        tmp_path,
        filter_workflow(
            {"used": ["src/a/**"], "orphan_group": ["src/b/**"]},
            unmatched_refs=None,
            gated_jobs={"job-a": ["used"]},
        ),
    )
    assert unconsumed_filter_groups(gc.load_workflow_model(wf)) == {"orphan_group"}


def test_faultinjection_dead_glob_reds() -> None:
    """FR-003c: a glob matching no tracked path reds (pure helper)."""
    tracked = {"src/real/module.py", "tests/real/test_it.py"}
    assert glob_is_live("src/real/**", tracked)
    assert not glob_is_live("src/deleted_package/**", tracked)


def test_faultinjection_unbacked_critical_path_reds() -> None:
    """FR-005: a critical path with no ``--cov`` ancestor reds (pure helper)."""
    cov = {"src/specify_cli/status", "src/kernel"}
    assert critical_path_backed_by("src/kernel/*", cov) == "src/kernel"
    assert critical_path_backed_by("src/orphaned_pkg/*", cov) is None


def test_faultinjection_extra_pytest_workflow_reds(tmp_path: Path) -> None:
    """FR-008: a pytest-invoking workflow outside the allowlist is discovered."""
    write_workflow(
        tmp_path,
        """\
        name: sneaky
        on: push
        jobs:
          hidden:
            runs-on: ubuntu-latest
            steps:
              - run: uv run pytest tests/hidden -m fast
        """,
        name="sneaky.yml",
    )
    discovered = gc.discover_pytest_workflows(tmp_path)
    assert discovered == frozenset({"sneaky.yml"})
    assert discovered != frozenset(gc.WORKFLOW_FILES)


def test_faultinjection_job_groups_mapping_drift_reds() -> None:
    """FR-011: a JOB_GROUPS row disagreeing with the parsed gating reds."""
    run_text = 'JOB_GROUPS = {\n    "fast-tests-sync": ["sync", "drifted_extra"],\n}\n'
    table = parse_job_groups(run_text)
    assert table == {"fast-tests-sync": {"sync", "drifted_extra"}}
    # A parsed gating that lacks ``drifted_extra`` would make table != parsed.
    parsed = {"fast-tests-sync": {"sync"}}
    assert table != parsed

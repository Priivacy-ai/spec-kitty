"""Workflow-coherence invariants (FR-003/FR-005/FR-008/FR-011, WP04).

These bind the delivery-topology relations this mission owns, over the SAME
parsed model as the marker invariant (``_gate_coverage.WorkflowModel``), so the
worst failure mode of the whole CI topology — a red suite coexisting with a
green aggregator (the phantom-``needs:`` class) — cannot silently return:

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

Every relation is a PARSED relation (C-002): job renames / YAML reordering that
preserve behaviour never red. Each has a fixture fault-injection proof.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from typing import TYPE_CHECKING

import pytest
import yaml

from tests.architectural import _gate_coverage as gc
from tests.architectural._workflow_fixtures import filter_workflow, write_workflow

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

_CI_QUALITY = gc.WORKFLOWS_DIR / "ci-quality.yml"
_TOJSON_NEEDS = "${{ toJSON(needs) }}"
_DECISION_STEP = "Evaluate quality-gate decision"
# ``"job-name": [ "grp", ... ]`` rows of the JOB_GROUPS heredoc (FR-011).
_JOB_GROUPS_ROW_RE = re.compile(r'"([\w-]+)":\s*\[([^\]]*)\]')
_QUOTED_RE = re.compile(r'"([\w-]+)"')


# ---------------------------------------------------------------------------
# Pure relation primitives (fault-injection substrate).
# ---------------------------------------------------------------------------


def needs_declaration_violations(model: gc.WorkflowModel) -> list[str]:
    """FR-003a: every ``needs.<job>.result`` read declared in that job's needs."""
    out: list[str] = []
    for job, reads in model.needs_result_reads.items():
        undeclared = reads - set(model.job_needs.get(job, ()))
        if undeclared:
            out.append(
                f"job {job!r} reads needs.<x>.result for undeclared job(s) "
                f"{sorted(undeclared)} (declared needs: {sorted(model.job_needs.get(job, ()))})"
            )
    return out


def unconsumed_filter_groups(model: gc.WorkflowModel) -> set[str]:
    """FR-003b: filter groups (minus the ``any_src`` probe) with no job ``if:`` consumer."""
    consumed: set[str] = set()
    for groups in model.job_gating_groups.values():
        consumed |= set(groups)
    return (set(model.filter_groups) - {"any_src"}) - consumed


def glob_is_live(glob: str, tracked: set[str]) -> bool:
    """FR-003c: does ``glob`` match >=1 tracked path?"""
    normalized = glob.rstrip("/")
    if normalized.endswith("/**"):
        prefix = normalized[:-3].rstrip("/") + "/"
        return any(path.startswith(prefix) for path in tracked)
    if "*" in normalized:
        return any(fnmatch.fnmatch(path, normalized) for path in tracked)
    return normalized in tracked or any(path.startswith(normalized + "/") for path in tracked)


def critical_path_backed_by(entry: str, cov_targets: set[str]) -> str | None:
    """FR-005: a ``--cov`` target that is an ancestor-or-equal of ``entry``, if any."""
    package = entry[:-2] if entry.endswith("/*") else entry
    package = package.rstrip("/")
    for cov in cov_targets:
        target = cov.rstrip("/")
        if package == target or package.startswith(target + "/"):
            return cov
    return None


def parse_job_groups(quality_gate_run_text: str) -> dict[str, set[str]]:
    """Parse the ``JOB_GROUPS = { ... }`` heredoc dict into ``job -> {groups}``."""
    match = re.search(r"JOB_GROUPS\s*=\s*\{(.*?)\}\s*\n", quality_gate_run_text, re.DOTALL)
    assert match, "JOB_GROUPS table not found in the quality-gate decision step"
    return {
        row.group(1): set(_QUOTED_RE.findall(row.group(2)))
        for row in _JOB_GROUPS_ROW_RE.finditer(match.group(1))
    }


def parsed_blocking_gating(model: gc.WorkflowModel) -> dict[str, set[str]]:
    """Job -> the dorny filter groups its ``if:`` gates on, for BLOCKING jobs only."""
    filter_names = set(model.filter_groups) - {"any_src"}
    blocking = set(model.job_needs["quality-gate"])
    mapping = {
        job: set(model.job_gating_groups.get(job, frozenset())) & filter_names
        for job in blocking
    }
    return {job: groups for job, groups in mapping.items() if groups}


# ---------------------------------------------------------------------------
# Live fixtures.
# ---------------------------------------------------------------------------


def _ci_quality_model() -> gc.WorkflowModel:
    return gc.load_workflow_model(_CI_QUALITY)


def _quality_gate_run_text() -> str:
    data = yaml.safe_load(_CI_QUALITY.read_text(encoding="utf-8"))
    steps = data["jobs"]["quality-gate"]["steps"]
    return "\n".join(str(step["run"]) for step in steps if "run" in step)


def _decision_step() -> dict[str, object]:
    data = yaml.safe_load(_CI_QUALITY.read_text(encoding="utf-8"))
    return next(
        step
        for step in data["jobs"]["quality-gate"]["steps"]
        if step.get("name") == _DECISION_STEP
    )


def _tracked_paths() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=gc.REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return set(result.stdout.splitlines())


# ---------------------------------------------------------------------------
# FR-003a / FR-003b / FR-003c live (all four suite-running workflows).
# ---------------------------------------------------------------------------


def test_needs_result_reads_are_declared_live() -> None:
    """FR-003a: no phantom ``needs.<job>.result`` read in any suite workflow."""
    for name in gc.WORKFLOW_FILES:
        model = gc.load_workflow_model(gc.WORKFLOWS_DIR / name)
        violations = needs_declaration_violations(model)
        assert not violations, f"{name}:\n" + "\n".join(violations)


def test_every_filter_group_is_consumed_live() -> None:
    """FR-003b: every named filter group gates >=1 job (the ``any_src`` probe excepted)."""
    for name in gc.WORKFLOW_FILES:
        model = gc.load_workflow_model(gc.WORKFLOWS_DIR / name)
        unconsumed = unconsumed_filter_groups(model)
        assert not unconsumed, f"{name}: unconsumed filter groups {sorted(unconsumed)}"


def test_every_filter_glob_is_live() -> None:
    """FR-003c: no dead filter glob (KNOWN FLOOR: WP03 FR-004(e) removed the stale ones)."""
    tracked = _tracked_paths()
    for name in gc.WORKFLOW_FILES:
        model = gc.load_workflow_model(gc.WORKFLOWS_DIR / name)
        dead = [
            (group, glob)
            for group, globs in model.filter_groups.items()
            for glob in globs
            if not glob_is_live(glob, tracked)
        ]
        assert not dead, f"{name}: dead filter globs (WP03-feedback if live) {dead}"


# ---------------------------------------------------------------------------
# FR-003d live: quality-gate consumes toJSON(needs), zero literal result reads.
# ---------------------------------------------------------------------------


def test_quality_gate_consumes_tojson_needs_not_literal_reads() -> None:
    """FR-003d: the aggregator's blocking authority is ``needs:`` via ``toJSON``.

    A literal ``needs.<job>.result`` read reappearing for quality-gate is the
    re-enumeration drift WP03's rewrite removed — model the toJSON form directly.
    """
    model = _ci_quality_model()
    assert model.needs_result_reads["quality-gate"] == frozenset(), (
        "quality-gate must read ZERO literal needs.<job>.result — membership in "
        f"needs: is the sole blocking authority; found: "
        f"{sorted(model.needs_result_reads['quality-gate'])}"
    )
    step = _decision_step()
    env = step.get("env")
    assert isinstance(env, dict) and env.get("NEEDS_JSON") == _TOJSON_NEEDS, (
        "the decision step must consume the full needs context via "
        "NEEDS_JSON: ${{ toJSON(needs) }}"
    )


def test_quality_gate_decision_step_pins_shell_bash() -> None:
    """FR-011 wiring (belt-and-suspenders): pipefail must be on, or the gate is vacuous.

    Without ``shell: bash`` the decision script's ``| tee`` swallows its non-zero
    exit (the blocker WP03 caught and fixed). Pin it here too so the mission's
    core guarantee has a second guard beyond the path-filters / release suites.
    """
    assert _decision_step().get("shell") == "bash"


# ---------------------------------------------------------------------------
# FR-005 live: diff-cover critical paths backed by a --cov emitter.
# ---------------------------------------------------------------------------


def test_diff_cover_critical_paths_are_cov_backed_live() -> None:
    """FR-005: every critical-path entry has a ``--cov`` ancestor-or-equal target."""
    model = _ci_quality_model()
    cov_targets: set[str] = set()
    for targets in model.cov_targets.values():
        cov_targets |= targets
    unbacked = [
        entry
        for entry in model.diff_cover_critical_paths
        if critical_path_backed_by(entry, cov_targets) is None
    ]
    assert not unbacked, f"unbacked critical-path entries (vacuous gate): {unbacked}"


# ---------------------------------------------------------------------------
# FR-008 live: workflow-set completeness.
# ---------------------------------------------------------------------------


def test_pytest_workflow_set_equals_model_allowlist() -> None:
    """FR-008: a fifth suite-running workflow must enter the model (fail-closed)."""
    assert gc.discover_pytest_workflows() == frozenset(gc.WORKFLOW_FILES)


# ---------------------------------------------------------------------------
# FR-011 live: JOB_GROUPS table == parsed job-if gating + C-005 pin.
# ---------------------------------------------------------------------------


def test_job_groups_table_equals_parsed_if_gating_live() -> None:
    """FR-011 (Decision 8): the aggregator's job->group table == the parsed if-gates."""
    model = _ci_quality_model()
    table = parse_job_groups(_quality_gate_run_text())
    parsed = parsed_blocking_gating(model)
    assert table == parsed, (
        "quality-gate JOB_GROUPS drifted from the parsed job-`if:` gating "
        f"(Decision 8). only-in-table={set(table) - set(parsed)}, "
        f"only-in-parsed={set(parsed) - set(table)}, "
        f"value-diffs={{j: (table[j], parsed[j]) for j in set(table) & set(parsed) if table[j] != parsed[j]}}"
    )


def test_quarantine_visibility_is_not_blocking_live() -> None:
    """C-005 pin: the quarantine job must never enter the blocking aggregator set."""
    model = _ci_quality_model()
    assert "quarantine-visibility" not in model.job_needs["quality-gate"]


def test_quality_gate_decision_data_blocks_present_live() -> None:
    """The greppable data anchors WP03 left stay present (they feed the decision script)."""
    run_text = _quality_gate_run_text()
    assert "DRAFT_GATED_JOBS" in run_text
    assert "RELEASE_REQUIRED_JOBS" in run_text


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
    run_text = (
        'JOB_GROUPS = {\n'
        '    "fast-tests-sync": ["sync", "drifted_extra"],\n'
        '}\n'
    )
    table = parse_job_groups(run_text)
    assert table == {"fast-tests-sync": {"sync", "drifted_extra"}}
    # A parsed gating that lacks ``drifted_extra`` would make table != parsed.
    parsed = {"fast-tests-sync": {"sync"}}
    assert table != parsed

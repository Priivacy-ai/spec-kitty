"""Factor-(a) residual-gate regression pin (FR-004, mission
ci-local-preflight-parity-01KWXWY0, #2283 Phase 3).

Factor (a)'s CI marker gate is ALREADY landed (mission ci-suite-map-bind,
closes #2034, commit ``6e5453e6d``): ``ci-quality.yml`` defines the
``unit-contract-residual`` job (``:2407-2421``) selecting ``(unit or
contract)``, and it is a named member of the blocking ``quality-gate.needs``
list (``:3437``). ``test_marker_job_completeness.py:288``
(``_residual_gate()``) ALREADY asserts the complementary fact — that
*exactly one* gate positively selects both ``unit`` and ``contract`` — and
``:223`` (``test_unit_and_contract_are_routed_by_marker_live``) asserts
``unit``/``contract`` are ROUTED-BY-MARKER. This module does **not** re-pin
either of those; duplicating a single invariant across two suites lets them
drift independently and trips Sonar's duplicate-logic check.

What is NOT yet pinned anywhere, and is genuinely at risk of silent
regression (a maintainer adding an ``if:`` to "speed up drafts", or dropping
the job from ``quality-gate.needs`` while refactoring the aggregator), is:

  1. The job is **always-on** — it carries NO ``if:`` key, so it cannot be
     skipped on a draft PR or a path-filtered run (the mission's own rationale
     comment at ``ci-quality.yml:2398-2399``: "NOT draft-gated and NOT
     path-gated by design").
  2. The job is a **named member** of ``quality-gate.needs`` — membership in
     ``needs:`` IS the blocking authority (see
     ``test_workflow_coherence.py::test_quality_gate_consumes_tojson_needs_not_literal_reads``,
     FR-003d); a job that quietly falls out of that list stops blocking merges
     even though its steps still run green.

Both facts are asserted read-only over ``ci-quality.yml`` — **no workflow
edit** ships with this pin.

Fault-injection (DIR-041): the naive implementation of "does job X have an
``if:``" is ``jobs.get(job_name, {}).get("if")`` — if ``job_name`` is ever
mis-keyed (a typo, or the job renamed), ``.get(job_name, {})`` silently
returns ``{}`` and ``{}.get("if")`` is ``None``, so the always-on assertion
would PASS VACUOUSLY for a job that does not even exist. The helpers below
guard against that (an absent job is a violation, not a pass), and the
fault-injection tests prove the two real regressions this module exists to
catch actually turn the assertions red: an ``if:`` added to the residual job,
and the residual job dropped from ``quality-gate.needs``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml

from tests.architectural import _gate_coverage as gc
from tests.architectural._workflow_fixtures import write_workflow

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.architectural

_CI_QUALITY = gc.WORKFLOWS_DIR / "ci-quality.yml"
_RESIDUAL_JOB = "unit-contract-residual"
_AGGREGATOR_JOB = "quality-gate"


# ---------------------------------------------------------------------------
# Pure classifier primitives (collection-free; the fault-injection substrate).
# ---------------------------------------------------------------------------


def _load_jobs(path: Path) -> dict[str, Any]:
    """Parse a workflow file's ``jobs:`` mapping (read-only)."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(data.get("jobs") or {})


def residual_job_is_always_on(jobs: dict[str, Any], job_name: str) -> bool:
    """``True`` iff ``job_name`` EXISTS and carries no ``if:`` key.

    An absent job is explicitly a violation (``False``), never a vacuous pass
    — guards the ``.get(key, empty)`` mis-key trap called out in the module
    docstring.
    """
    if job_name not in jobs:
        return False
    job = jobs[job_name]
    return isinstance(job, dict) and job.get("if") is None


def residual_job_is_gate_member(
    jobs: dict[str, Any], aggregator: str, job_name: str
) -> bool:
    """``True`` iff ``job_name`` is a named entry of ``aggregator``'s ``needs:``.

    Same mis-key discipline: an absent aggregator job is a violation, not a
    vacuous pass.
    """
    if aggregator not in jobs:
        return False
    needs = jobs[aggregator].get("needs")
    if needs is None:
        return False
    if isinstance(needs, str):
        needs = [needs]
    return job_name in needs


# ---------------------------------------------------------------------------
# Live checks (the 2 genuinely-uncovered facts, FR-004 / SC-004).
# ---------------------------------------------------------------------------


def test_unit_contract_residual_is_always_on_live() -> None:
    """Fact 1: ``unit-contract-residual`` carries NO ``if:`` gate.

    Not draft-gated, not path-gated — a draft PR cannot merge-queue with the
    residual unrun (the job's own rationale comment, ``ci-quality.yml:2398``).
    """
    jobs = _load_jobs(_CI_QUALITY)
    assert residual_job_is_always_on(jobs, _RESIDUAL_JOB), (
        f"{_RESIDUAL_JOB!r} must carry NO `if:` key (always-on); found "
        f"if={jobs.get(_RESIDUAL_JOB, {}).get('if')!r}"
    )


def test_unit_contract_residual_is_named_quality_gate_dependency_live() -> None:
    """Fact 2: ``unit-contract-residual`` is a named member of ``quality-gate.needs``.

    Membership in ``needs:`` is the sole blocking authority (FR-003d,
    ``test_workflow_coherence.py::test_quality_gate_consumes_tojson_needs_not_literal_reads``) —
    this is what makes the job's result actually gate merges.
    """
    jobs = _load_jobs(_CI_QUALITY)
    assert residual_job_is_gate_member(jobs, _AGGREGATOR_JOB, _RESIDUAL_JOB), (
        f"{_RESIDUAL_JOB!r} must be a named entry of "
        f"{_AGGREGATOR_JOB!r}.needs; found needs="
        f"{jobs.get(_AGGREGATOR_JOB, {}).get('needs')!r}"
    )


# ---------------------------------------------------------------------------
# MANDATORY fault-injection (DIR-041 red-first proof; cf.
# test_workflow_coherence.py::test_faultinjection_*_reds).
# ---------------------------------------------------------------------------


def test_faultinjection_residual_with_if_gate_reds(tmp_path: Path) -> None:
    """An ``if:`` added to the residual job turns the always-on assertion red."""
    wf = write_workflow(
        tmp_path,
        """\
        name: fixture
        on: pull_request
        jobs:
          unit-contract-residual:
            if: github.event.pull_request.draft == false
            runs-on: ubuntu-latest
            steps:
              - run: uv run pytest tests/ -m "(unit or contract)"
        """,
    )
    jobs = _load_jobs(wf)
    assert not residual_job_is_always_on(jobs, _RESIDUAL_JOB), (
        "fault-injection failed to red: an `if:`-gated residual job must NOT "
        "be reported always-on"
    )


def test_faultinjection_residual_dropped_from_needs_reds(tmp_path: Path) -> None:
    """The residual job missing from ``quality-gate.needs`` turns the membership assertion red."""
    wf = write_workflow(
        tmp_path,
        """\
        name: fixture
        on: pull_request
        jobs:
          unit-contract-residual:
            runs-on: ubuntu-latest
            steps:
              - run: uv run pytest tests/ -m "(unit or contract)"
          quality-gate:
            needs:
              - lint
              - kernel-tests
            runs-on: ubuntu-latest
            steps:
              - run: echo done
        """,
    )
    jobs = _load_jobs(wf)
    assert not residual_job_is_gate_member(jobs, _AGGREGATOR_JOB, _RESIDUAL_JOB), (
        "fault-injection failed to red: a residual job dropped from "
        "quality-gate.needs must NOT be reported a gate member"
    )


def test_faultinjection_miskeyed_job_name_does_not_vacuously_pass(
    tmp_path: Path,
) -> None:
    """A mis-keyed/absent job name is a violation, never a `.get(key, {})` vacuous pass."""
    wf = write_workflow(
        tmp_path,
        """\
        name: fixture
        on: pull_request
        jobs:
          some-other-job:
            runs-on: ubuntu-latest
            steps:
              - run: echo hi
        """,
    )
    jobs = _load_jobs(wf)
    assert not residual_job_is_always_on(jobs, _RESIDUAL_JOB)
    assert not residual_job_is_gate_member(jobs, _AGGREGATOR_JOB, _RESIDUAL_JOB)


def test_env_check_marker_parser_agrees_with_gate_coverage_live() -> None:
    """Drift guard: ``_test_env_check`` and ``_gate_coverage`` must agree on the
    live ``unit-contract-residual`` ``-m`` marker expression.

    Two independent parsers read the same CI job's selection:
    ``read_ci_residual_marker_expr`` (the narrow single-line regex behind
    ``spec-kitty review --check-residual``) and ``_gate_coverage.load_gates``
    (the doctrine-blessed workflow parser). If either drifts, the local
    residual selection silently diverges from what CI actually runs. Pin them
    to one value so a ``run:`` reformat that only one parser survives fails
    here instead of shipping a wrong local selection.
    """
    from specify_cli.cli.commands._test_env_check import (
        CI_RESIDUAL_JOB_NAME,
        read_ci_residual_marker_expr,
    )

    assert CI_RESIDUAL_JOB_NAME == _RESIDUAL_JOB  # both modules name the same job
    env_check_expr = read_ci_residual_marker_expr(_CI_QUALITY)
    gate_markers = {
        gate.marker_expr
        for gate in gc.load_gates()
        if gate.job == _RESIDUAL_JOB and gate.marker_expr is not None
    }
    assert env_check_expr in gate_markers, (
        f"{_RESIDUAL_JOB} marker-expr drift: _test_env_check parsed "
        f"{env_check_expr!r}, but _gate_coverage sees {gate_markers!r}"
    )

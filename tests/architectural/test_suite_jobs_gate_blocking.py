"""``quality-gate.needs`` ⊇ pytest-jobs containment guard (FR-012, IC-11, #2622).

Mission ``test-suite-friction-remediation-01KXDKBX`` WP17. Contract:
``contracts/quality-gate-needs-containment.md`` (kitty-specs). Single-file
ownership: this module is the SOLE new invariant suite over
``.github/workflows/ci-quality.yml`` for FR-012 (the sibling
``test_ui_e2e_coverage_discovered.py`` owns FR-013 on the same file, serialized
after this one per the plan).

Every ``pytest``-invoking job in ``ci-quality.yml`` must be a member of
``quality-gate.needs`` — the single blocking-verdict authority
(``test_workflow_coherence.py``'s FR-003d pin) — minus a reasoned
:data:`NON_BLOCKING_ALLOWLIST`. Two jobs were un-gated **by convention only**
before this WP (``slow-tests``, ``mutation-testing``); T082 forces both to an
explicit state:

* ``slow-tests`` — group-less/always-on (no dorny filter-group ``if:`` gate,
  like ``lint``/``kernel-tests``/``unit-contract-residual`` already in
  ``needs:``), so it is added to ``quality-gate.needs`` directly
  (``.github/workflows/ci-quality.yml``'s own comment at that ``needs:`` entry
  explains why this is safe: ``scripts/ci/quality_gate_decision.py``'s
  ``filter_true`` is vacuously ``False`` for a job with no filter groups, so
  its ``skipped`` result on every non-push event is legitimately OK, while a
  real ``failure`` on the push runs it DOES execute on now blocks the gate).
* ``mutation-testing`` — ``if: false``-disabled (an ``echo``-only step); it
  invokes no real pytest command today, so the anchored derivation below never
  actually catches it, but it is still listed in the allowlist (with
  rationale) so the "never left silently absent" requirement is satisfied by
  construction rather than by the guard's incidental blind spot.

Anti-goals (contract): do NOT hard-code the current job list (derive
``pytest_jobs`` from the parsed workflow model so a FUTURE job is covered
automatically); do NOT match ``pytest`` inside a comment or a string literal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architectural import _gate_coverage as gc
from tests.architectural._workflow_fixtures import write_workflow

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

_CI_QUALITY_NAME = "ci-quality.yml"
_QUALITY_GATE_JOB = "quality-gate"

# Reasoned allowlist (contracts/quality-gate-needs-containment.md): a
# pytest-invoking job that is deliberately NOT gate-blocking. Each entry
# carries a why-non-blocking rationale (mirrors the ``CI_INVISIBLE`` ledger
# pattern in ``test_marker_job_completeness.py``). Additions are LOUD — this
# guard subtracts the allowlist from ``pytest_jobs`` before checking
# containment, so a bare, reason-less addition would silently widen the
# non-blocking surface; :func:`test_allowlist_entries_carry_rationale` closes
# that gap. Removals are always safe (shrink-only).
NON_BLOCKING_ALLOWLIST: dict[str, str] = {
    "quarantine-visibility": (
        "Non-blocking BY DESIGN (visible-but-never-gating quarantine surface, "
        "mission ci-suite-map-bind, C-005). "
        "scripts/ci/quality_gate_decision.py's _assert_no_quarantine_job "
        "hard-fails (exit 2) if this job ever enters quality-gate's "
        "needs/job_groups/draft_gated_jobs/release_required_jobs sets, so it "
        "can never legitimately be promoted to gate-blocking — a quarantined "
        "flake must never be able to block a merge."
    ),
    "mutation-testing": (
        "Disabled placeholder (`if: false`, an echo-only step: "
        '`echo "Mutation testing is disabled."`) pending future '
        "mutation-testing tooling. It invokes no real pytest command today "
        "(so the anchored pytest_jobs derivation below never actually flags "
        "it), but is listed here so FR-012's 'never left silently absent' is "
        "satisfied by an explicit declaration rather than by the guard's "
        "incidental blind spot. Re-enabling it MUST be paired with either a "
        "`quality-gate.needs` edge or an updated rationale here."
    ),
}

# Jobs T082 requires an EXPLICIT state for (gate-blocking OR allowlisted),
# independent of whether the anchored pytest-command parser actually detects
# them as pytest-invoking (mutation-testing's `if: false` echo does not).
_EXPLICITLY_RESOLVED_JOBS: tuple[str, ...] = ("slow-tests", "mutation-testing")


def pytest_jobs_of(workflow_name: str) -> frozenset[str]:
    """FR-012: jobs in ``workflow_name`` with >=1 real pytest-invoking step.

    Reuses ``_gate_coverage``'s existing anchored run-command parser
    (:func:`_gate_coverage.parse_workflow` / ``parse_pytest_invocation``) — a
    :class:`_gate_coverage.Gate` is only emitted for a job whose *real
    command* (after stripping env-assignments and runner prefixes, and never
    matching inside a comment or a quoted string) begins with the literal
    ``pytest`` token. Do NOT hard-code the job list here (contract anti-goal).
    """
    return frozenset(
        gate.job for gate in gc.load_gates() if gate.workflow == workflow_name
    )


def blocking_violations(
    pytest_jobs: frozenset[str],
    quality_gate_needs: frozenset[str],
    allowlist: dict[str, str],
) -> frozenset[str]:
    """Pure IC-11 relation: ``pytest_jobs - allowlist - needs`` (empty == healthy)."""
    return pytest_jobs - frozenset(allowlist) - quality_gate_needs


def _ci_quality_needs() -> frozenset[str]:
    model = gc.load_workflow_model(gc.WORKFLOWS_DIR / _CI_QUALITY_NAME)
    return frozenset(model.job_needs[_QUALITY_GATE_JOB])


# ---------------------------------------------------------------------------
# Live assertions (ci-quality.yml).
# ---------------------------------------------------------------------------


def test_pytest_jobs_is_non_vacuous_live() -> None:
    """Guard against a vacuous relation: real pytest jobs are actually parsed."""
    assert pytest_jobs_of(_CI_QUALITY_NAME), (
        "no pytest-invoking job was parsed from ci-quality.yml — the relation "
        "would pass vacuously"
    )


def test_pytest_jobs_minus_allowlist_are_gate_blocking_live() -> None:
    """FR-012: every pytest job, minus the reasoned allowlist, blocks the gate."""
    violations = blocking_violations(
        pytest_jobs_of(_CI_QUALITY_NAME),
        _ci_quality_needs(),
        NON_BLOCKING_ALLOWLIST,
    )
    assert not violations, (
        f"pytest-invoking job(s) absent from both `quality-gate.needs` and "
        f"`NON_BLOCKING_ALLOWLIST` (un-gated suite job(s)): {sorted(violations)}"
    )


def test_allowlist_entries_carry_rationale() -> None:
    """Contract: every ``NON_BLOCKING_ALLOWLIST`` entry has a non-empty reason."""
    empty = [job for job, reason in NON_BLOCKING_ALLOWLIST.items() if not reason.strip()]
    assert not empty, f"NON_BLOCKING_ALLOWLIST entries with an empty rationale: {empty}"


def test_slow_tests_and_mutation_testing_are_explicitly_resolved_live() -> None:
    """T082: both jobs are EITHER gate-blocking OR allowlisted-with-rationale.

    Asserted directly (not merely relying on ``pytest_jobs`` incidentally
    catching them) because ``mutation-testing`` is ``if: false``-disabled and
    invokes no pytest command today — it would never be flagged by the
    anchored derivation above, yet FR-012 still requires it resolved to an
    explicit, non-silent state.
    """
    needs = _ci_quality_needs()
    unresolved = [
        job
        for job in _EXPLICITLY_RESOLVED_JOBS
        if job not in needs and job not in NON_BLOCKING_ALLOWLIST
    ]
    assert not unresolved, (
        f"job(s) left in the silently-absent state (neither gate-blocking nor "
        f"allowlisted-with-rationale): {unresolved}"
    )


def test_quarantine_visibility_stays_allowlisted_not_gated_live() -> None:
    """C-005 corollary: quarantine-visibility is allowlisted, never in needs."""
    assert "quarantine-visibility" in NON_BLOCKING_ALLOWLIST
    assert "quarantine-visibility" not in _ci_quality_needs()


# ---------------------------------------------------------------------------
# Fault-injection (T083 — non-fakeable evidence).
# ---------------------------------------------------------------------------

_FIXTURE_WORKFLOW = """\
name: fixture
on: push
jobs:
  quality-gate:
    needs: [existing-suite]
    runs-on: ubuntu-latest
    steps:
      - run: echo gate
  existing-suite:
    runs-on: ubuntu-latest
    steps:
      - run: uv run pytest tests/ -m fast
  sneaky-new-suite:
    runs-on: ubuntu-latest
    steps:
      - run: uv run pytest tests/sneaky -m fast
"""


def test_faultinjection_new_pytest_job_without_gate_edge_reds(tmp_path: Path) -> None:
    """FR-012 regression: a NEW pytest job absent from needs/allowlist reds.

    Non-fakeable evidence required by the contract: adds a fake pytest job
    (``sneaky-new-suite``) to a synthetic workflow that is NOT wired into
    ``quality-gate.needs`` and is NOT allowlisted, then asserts the guard
    catches exactly it.
    """
    wf = write_workflow(tmp_path, _FIXTURE_WORKFLOW, name="wf.yml")
    # `pytest_jobs_of` filters via `gc.load_gates()`, which only ever parses
    # the 5 real `WORKFLOW_FILES` under `WORKFLOWS_DIR` — the fixture lives
    # outside that dir, so parse it directly with the same underlying parser.
    gates = gc.parse_workflow(wf)
    pytest_jobs = frozenset(gate.job for gate in gates)
    assert pytest_jobs == frozenset({"existing-suite", "sneaky-new-suite"})

    model = gc.load_workflow_model(wf)
    needs = frozenset(model.job_needs[_QUALITY_GATE_JOB])
    violations = blocking_violations(pytest_jobs, needs, {})
    assert violations == frozenset({"sneaky-new-suite"}), (
        f"expected exactly the un-gated fake pytest job to be caught, got {sorted(violations)}"
    )


def test_faultinjection_gated_or_allowlisted_job_does_not_red(tmp_path: Path) -> None:
    """Green control: the SAME fake job wired into needs (or allowlisted) passes.

    Proves the guard does not false-positive once the job is legitimately
    resolved — the negative-control twin of the regression above.
    """
    wf = write_workflow(
        tmp_path,
        _FIXTURE_WORKFLOW.replace(
            "needs: [existing-suite]",
            "needs: [existing-suite, sneaky-new-suite]",
        ),
        name="wf.yml",
    )
    gates = gc.parse_workflow(wf)
    pytest_jobs = frozenset(gate.job for gate in gates)
    model = gc.load_workflow_model(wf)
    needs = frozenset(model.job_needs[_QUALITY_GATE_JOB])
    assert not blocking_violations(pytest_jobs, needs, {})

    # Allowlisting instead of gating is an equally valid resolution.
    wf_allowlisted = write_workflow(tmp_path, _FIXTURE_WORKFLOW, name="wf2.yml")
    gates2 = gc.parse_workflow(wf_allowlisted)
    pytest_jobs2 = frozenset(gate.job for gate in gates2)
    model2 = gc.load_workflow_model(wf_allowlisted)
    needs2 = frozenset(model2.job_needs[_QUALITY_GATE_JOB])
    allowlist = {"sneaky-new-suite": "fixture-only rationale for the negative control"}
    assert not blocking_violations(pytest_jobs2, needs2, allowlist)

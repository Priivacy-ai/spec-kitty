"""Draft/ready CI contract (mission ci-flake-report-workflow WP04, T017).

Static assertions over ``.github/workflows/ci-quality.yml`` and
``scripts/ci/quality_gate_decision.py`` pinning the WP04 shape:

- FR-009: a draft PR fail-fast canceller (`draft-fail-fast-cancel`) exists,
  is draft-conditioned (`if: failure() && ... draft == true`, never a literal
  `.result` comparison), carries `permissions: {actions: write}`, and is
  declared non-blocking in
  ``tests/architectural/test_suite_jobs_gate_blocking.py``'s
  ``NON_BLOCKING_ALLOWLIST``.
- FR-011/C-003 (T015 audit, encoded as a regression pin): the quality-gate
  decision STEP — never a job-level `if:` — is the one place that reads each
  job's `.result` (`toJSON(needs)` piped into
  ``scripts/ci/quality_gate_decision.py``, whose `_coerce_result` reads
  `.get("result")`). No job's own `if:` gates its execution on a literal
  `needs.<job>.result` comparison (that invariant is also guarded, more
  broadly, by
  ``tests/architectural/test_ci_quality_path_filters.py::test_no_shard_gates_execution_on_a_predecessor_result``).
- No gate-blocking job carries a job-level `continue-on-error` (that would
  silently make its own failure non-blocking to `needs:`/quality-gate;
  advisory step-level `continue-on-error` on e.g. the `lint` job's
  ruff/mypy report steps is a separate, already-aggregated pattern this test
  does not touch).
- FR-012: `ready_for_review` is a `pull_request` trigger type, so a
  draft->ready flip re-runs the suites the canceller/DRAFT_GATED_JOBS
  exemption skipped while the PR was in draft.

Mirrors the existing ``tests/scripts/test_quality_gate_decision.py`` /
``tests/architectural/test_ci_quality_path_filters.py`` pattern: ``scripts/ci``
is not an importable package, and the workflow YAML is parsed directly rather
than re-derived.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.architectural.test_suite_jobs_gate_blocking import NON_BLOCKING_ALLOWLIST

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW_PATH = _REPO_ROOT / ".github" / "workflows" / "ci-quality.yml"
_DECISION_SCRIPT_PATH = _REPO_ROOT / "scripts" / "ci" / "quality_gate_decision.py"

_CANCELLER_JOB = "draft-fail-fast-cancel"
_QUALITY_GATE_JOB = "quality-gate"

# Same class of literal `.result` comparison
# tests/architectural/test_ci_quality_path_filters.py's
# `_find_result_gated_jobs` forbids in a job-level `if:` — reused here (not
# re-derived) to assert the canceller's `if: failure()` does not smuggle one
# in under a different spelling.
_LITERAL_RESULT_COMPARISON = re.compile(r"needs\.[\w-]+\.result\b")


def _load_workflow() -> dict[str, Any]:
    return yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))


def _job(data: dict[str, Any], job_name: str) -> dict[str, Any]:
    return dict(data["jobs"][job_name])


# ---------------------------------------------------------------------------
# FR-009: the draft canceller.
# ---------------------------------------------------------------------------


def test_draft_canceller_job_exists_with_actions_write_permission() -> None:
    data = _load_workflow()
    assert _CANCELLER_JOB in data["jobs"], (
        f"{_CANCELLER_JOB!r} is missing from ci-quality.yml — FR-009's draft "
        "fail-fast canceller was not wired"
    )
    canceller = _job(data, _CANCELLER_JOB)
    assert canceller.get("permissions") == {"actions": "write"}, (
        f"{_CANCELLER_JOB!r} must declare `permissions: {{actions: write}}` "
        f"(minimal scope for the cancel-run API call), got "
        f"{canceller.get('permissions')!r}"
    )


def test_draft_canceller_is_draft_conditioned_on_failure_not_result() -> None:
    """`if:` must be `failure()` gated on the draft flag, never a `.result` read."""
    canceller = _job(_load_workflow(), _CANCELLER_JOB)
    if_expr = str(canceller["if"])

    assert "failure()" in if_expr, (
        f"{_CANCELLER_JOB!r}.if must use the `failure()` context function "
        f"over its `needs:`, got {if_expr!r}"
    )
    assert "github.event.pull_request.draft == true" in if_expr, (
        f"{_CANCELLER_JOB!r}.if must be conditioned on the PR being a draft, "
        f"got {if_expr!r}"
    )
    assert not _LITERAL_RESULT_COMPARISON.search(if_expr), (
        f"{_CANCELLER_JOB!r}.if must not gate on a literal `needs.<job>.result` "
        f"comparison (that pattern is reserved for the decision STEP's "
        f"toJSON(needs) payload, never a job-level `if:`), got {if_expr!r}"
    )


def test_draft_canceller_needs_the_early_suites() -> None:
    """The canceller must depend on the earliest, unconditional gates.

    `lint` and `kernel-tests` are the two jobs almost the entire fan-out is
    chained behind (directly or transitively) and neither is path-filtered —
    both run on every PR — so they are the fastest available fail-fast signal.
    """
    canceller = _job(_load_workflow(), _CANCELLER_JOB)
    needs = canceller.get("needs")
    if isinstance(needs, str):
        needs = [needs]
    assert needs, f"{_CANCELLER_JOB!r} must declare `needs:` (got none)"
    assert set(needs) <= {"lint", "kernel-tests"} and needs, (
        f"{_CANCELLER_JOB!r}.needs should be the small, cheap early-suite set "
        f"({{'lint', 'kernel-tests'}}), got {sorted(needs)}"
    )


def test_draft_canceller_single_cancel_step() -> None:
    """A single step, hitting the run-cancel REST endpoint via GH_TOKEN."""
    canceller = _job(_load_workflow(), _CANCELLER_JOB)
    steps = canceller["steps"]
    assert len(steps) == 1, (
        f"{_CANCELLER_JOB!r} should be a single-step job (minimal blast "
        f"radius), got {len(steps)} steps"
    )
    step = steps[0]
    run_script = str(step["run"])
    assert "gh api -X POST" in run_script
    assert "actions/runs/${{ github.run_id }}/cancel" in run_script
    assert step.get("env", {}).get("GH_TOKEN") == "${{ github.token }}"


def test_draft_canceller_is_allowlisted_non_blocking() -> None:
    assert _CANCELLER_JOB in NON_BLOCKING_ALLOWLIST, (
        f"{_CANCELLER_JOB!r} must be declared in NON_BLOCKING_ALLOWLIST "
        "(tests/architectural/test_suite_jobs_gate_blocking.py) — it invokes "
        "no pytest and must never enter quality-gate.needs"
    )
    assert NON_BLOCKING_ALLOWLIST[_CANCELLER_JOB].strip(), (
        f"{_CANCELLER_JOB!r}'s NON_BLOCKING_ALLOWLIST entry must carry a "
        "non-empty rationale"
    )
    quality_gate = _job(_load_workflow(), _QUALITY_GATE_JOB)
    assert _CANCELLER_JOB not in quality_gate["needs"], (
        f"{_CANCELLER_JOB!r} must stay OUT of quality-gate.needs — it is "
        "non-blocking by design (mirrors the quarantine-visibility C-005 shape)"
    )


# ---------------------------------------------------------------------------
# FR-011/C-003 (T015 audit) — regression pin.
# ---------------------------------------------------------------------------


def test_no_job_level_if_gates_on_a_literal_result_comparison() -> None:
    """No job's own `if:` may read a literal `needs.<job>.result`.

    The ONLY sanctioned place a `.result` field is consulted is inside the
    quality-gate decision STEP's `toJSON(needs)` payload, consumed by
    `scripts/ci/quality_gate_decision.py`. A job-level `if:` doing the same
    thing directly would create a second, un-audited blocking authority.
    `consumer-compatibility` is a named, justified exception (release-wheel
    availability check, not a shard result-gate) — see
    tests/architectural/test_ci_quality_path_filters.py's
    `_NON_SHARD_AGGREGATOR_EXCEPTIONS`.
    """
    data = _load_workflow()
    offending = {
        name: str(job["if"])
        for name, job in data["jobs"].items()
        if name != "consumer-compatibility"
        and isinstance(job, dict)
        and job.get("if") is not None
        and _LITERAL_RESULT_COMPARISON.search(str(job["if"]))
    }
    assert not offending, (
        "job(s) gate their own execution on a literal `needs.<job>.result` "
        f"read in a job-level `if:` (reserved for the decision step): {offending}"
    )


def test_quality_gate_decision_step_is_the_result_reading_authority() -> None:
    """The decision STEP (not the `quality-gate` job's own `if:`) reads `.result`."""
    data = _load_workflow()
    quality_gate = _job(data, _QUALITY_GATE_JOB)

    # The job's own `if:` never reads `.result` — only the always()/label guard.
    assert not _LITERAL_RESULT_COMPARISON.search(str(quality_gate["if"])), (
        f"{_QUALITY_GATE_JOB!r}'s own job-level `if:` must not read a "
        f"`.result` field, got {quality_gate['if']!r}"
    )

    decision_step = next(
        step
        for step in quality_gate["steps"]
        if step.get("name") == "Evaluate quality-gate decision"
    )
    assert decision_step["env"]["NEEDS_JSON"] == "${{ toJSON(needs) }}", (
        "the decision step must consume the FULL needs context (every job's "
        "`result` + `outputs`) via toJSON(needs), never a re-enumerated "
        "literal per-job `.result` read"
    )
    assert "scripts/ci/quality_gate_decision.py" in decision_step["run"]


def test_quality_gate_decision_script_reads_result_not_conclusion() -> None:
    """T015 audit pin: `_coerce_result` reads `.get("result")`, never `conclusion`."""
    source = _DECISION_SCRIPT_PATH.read_text(encoding="utf-8")
    assert 'result = value.get("result")' in source, (
        "scripts/ci/quality_gate_decision.py's _coerce_result must read the "
        "'result' field off each needs-context job mapping (T015 audit — this "
        "is the single sanctioned place a job's .result is consumed)"
    )
    assert '"conclusion"' not in source and "'conclusion'" not in source, (
        "scripts/ci/quality_gate_decision.py must not read a job's "
        "'conclusion' field — GitHub's needs-context result value (skipped/"
        "success/failure/cancelled) already IS the blocking-relevant field; "
        "the workflow's steps.<id>.conclusion is a distinct, unrelated field "
        "no needs-context consumer should conflate with it"
    )


# ---------------------------------------------------------------------------
# No gate-blocking job masks its own failure via job-level continue-on-error.
# ---------------------------------------------------------------------------


def test_no_gating_job_has_job_level_continue_on_error() -> None:
    """A job-level `continue-on-error: true` would defeat `needs:` blocking.

    Step-level `continue-on-error` (e.g. the `lint` job's advisory
    ruff/mypy report steps, or `diff-coverage`'s optional steps) is a
    separate, already-aggregated pattern — those jobs explicitly check
    `steps.<id>.outcome` before deciding their own final exit code. What must
    never happen is the JOB itself opting out of propagating its result to
    whatever depends on it (`quality-gate.needs` or a downstream `needs:`
    chain), which is exactly what a job-level `continue-on-error` would do.
    """
    data = _load_workflow()
    offending = [
        name
        for name, job in data["jobs"].items()
        if isinstance(job, dict) and job.get("continue-on-error")
    ]
    assert not offending, (
        f"job(s) declare a job-level `continue-on-error` (silently makes "
        f"their own failure non-blocking): {offending}"
    )


def _fast_cli_steps() -> list[dict[str, Any]]:
    data = _load_workflow()
    job = data["jobs"]["fast-tests-cli"]
    return [s for s in job["steps"] if isinstance(s, dict)]


def test_red_first_primary_pytest_step_is_not_continue_on_error() -> None:
    """FR-011/FR-018 false-green guard: the red-first optimization must never
    let the *primary* pytest step mask a real failure. Only the red-first
    HELPER steps (restore/seed/collect) may be `continue-on-error`; the actual
    test-run step must not be, so a genuine failure still fails the gating
    `fast-tests-cli` job.
    """
    steps = _fast_cli_steps()
    primary = [s for s in steps if s.get("name") == "Run fast tests — cli"]
    assert len(primary) == 1, "expected exactly one primary fast-cli pytest step"
    assert not primary[0].get("continue-on-error"), (
        "the primary 'Run fast tests — cli' step must NOT be continue-on-error "
        "— that would green the gating job on a real failure (FR-011)"
    )


def test_red_first_helper_steps_are_continue_on_error() -> None:
    """The three red-first helper steps (restore/seed/collect) MUST be
    continue-on-error so the ergonomics optimization can never gate or error
    the run (FR-018 defensive contract)."""
    helpers = [s for s in _fast_cli_steps() if "[FR-018]" in str(s.get("name", ""))]
    assert len(helpers) == 3, f"expected 3 FR-018 red-first helper steps, found {len(helpers)}"
    not_guarded = [s["name"] for s in helpers if not s.get("continue-on-error")]
    assert not not_guarded, (
        f"red-first helper step(s) missing `continue-on-error: true` (could gate "
        f"the run on a cache/parse hiccup, violating FR-018): {not_guarded}"
    )


# ---------------------------------------------------------------------------
# FR-012/FR-013: draft->ready re-run trigger.
# ---------------------------------------------------------------------------


def test_ready_for_review_is_a_pull_request_trigger_type() -> None:
    data = _load_workflow()
    # PyYAML's default (YAML 1.1) resolver parses the bare `on:` trigger key
    # as the boolean `True`, not the string `"on"` -- `data[True][...]` is the
    # correct access (see tests/architectural/test_ci_corpus_trigger_completeness.py).
    pr_trigger = data[True]["pull_request"]
    assert "ready_for_review" in pr_trigger["types"], (
        "`ready_for_review` must be a pull_request trigger type (FR-012) so "
        "a draft->ready flip re-runs the suites the draft-gated jobs and "
        f"{_CANCELLER_JOB!r} skipped while the PR was still a draft"
    )

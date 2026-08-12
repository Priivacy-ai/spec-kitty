"""Red-first reproduction of #3307 — the CLI emits ``force=False`` for
review-rejection rollbacks that the vendored ``spec-kitty-events`` contract
declares invalid without ``force=True``.

Open P0: https://github.com/Priivacy-ai/spec-kitty/issues/3307

Root cause: two independently-authored ``validate_transition`` functions with the
same name and opposite answers.

* ``build_transition_plan`` (``src/specify_cli/cli/commands/agent/tasks_transition_core.py``)
  asks the CLI-LOCAL FSM (``specify_cli.status``) whether a backward review-rejection
  edge is legal force-free given the evidence carried at the plan layer, and emits
  ``emit_force=False`` when it is.
* The SHARED, vendored ``spec_kitty_events.validate_transition`` — the contract
  package both this repo and ``spec-kitty-saas`` pin (``spec-kitty-events==6.1.0``)
  — declares exactly these "review-rejection family" backward edges invalid unless
  ``force=True``. The CLI emit path never calls the shared validator, so
  contract-invalid events are produced and queued silently and are only rejected
  later at sync time (10 real ``in_review -> planned`` events were rejected by the
  SaaS ingestion endpoint in the reported case).

This drives the REAL emit-decision function (``build_transition_plan``) and then
validates the wire payload it would emit against the REAL shared contract
validator — proving the CLI emits events its own vendored dependency rejects.

Desired post-fix outcome (either maintainer resolution turns this green): every
event ``build_transition_plan`` emits for these edges must be accepted by the
shared ``spec_kitty_events`` contract — whether by emitting ``force=True`` (make
the CLI conform) or by amending the shared contract to carry a wire-representable
evidence exemption and having the CLI emit that evidence (issue #3307 options a/b).
This test pins the conformance contract, not the chosen mechanism.
"""

from __future__ import annotations

import pytest

from specify_cli.cli.commands.agent.tasks_transition_core import build_transition_plan
from specify_cli.status import ReviewResult
from spec_kitty_events import validate_transition as shared_validate_transition
from spec_kitty_events.status import StatusTransitionPayload

pytestmark = pytest.mark.regression

_REVIEW_RESULT = ReviewResult(
    reviewer="claude",
    verdict="rejected",
    reference="review-cycle-1.md",
    feedback_path="review-cycle-1.md",
)

# The four "review-rejection family" backward edges that spec-kitty-events==6.1.0
# declares force-required, each with the plan-layer evidence that makes the
# CLI-local FSM resolve them force-free today.
_REVIEW_REJECTION_EDGES = [
    (
        "in_review",
        "planned",
        {"review_feedback_pointer": "review-cycle-1.md", "review_result": _REVIEW_RESULT},
    ),
    (
        "in_progress",
        "planned",
        {"note_text": "rework needed"},
    ),
    (
        "approved",
        "planned",
        {"review_feedback_pointer": "review-cycle-1.md", "arb_review_ref": "review-cycle-1.md"},
    ),
    (
        "in_review",
        "in_progress",
        {"review_result": _REVIEW_RESULT},
    ),
]


@pytest.mark.parametrize(
    ("old_lane", "target_lane", "evidence"),
    _REVIEW_REJECTION_EDGES,
    ids=[f"{o}->{n}" for o, n, _ in _REVIEW_REJECTION_EDGES],
)
def test_cli_emit_conforms_to_shared_events_contract(
    old_lane: str, target_lane: str, evidence: dict[str, object]
) -> None:
    kwargs: dict[str, object] = {
        "review_feedback_pointer": None,
        "arb_review_ref": None,
        "note_text": None,
        "review_result": None,
    }
    kwargs.update(evidence)

    plan = build_transition_plan(
        old_lane=old_lane, target_lane=target_lane, force=False, **kwargs
    )

    payload = StatusTransitionPayload(
        mission_slug="example-mission",
        wp_id="WP01",
        from_lane=old_lane,
        to_lane=target_lane,
        actor="claude",
        force=plan.emit_force,
        reason=plan.emit_reason,
        execution_mode="worktree",
        review_ref=plan.emit_review_ref,
        evidence=None,
    )
    result = shared_validate_transition(payload)

    # RED today: the CLI emits force=False and the shared contract rejects it.
    assert result.valid, (
        f"CLI's build_transition_plan emitted force={plan.emit_force} for "
        f"{old_lane} -> {target_lane}, which the vendored spec-kitty-events "
        f"contract rejects: {result.violations}"
    )

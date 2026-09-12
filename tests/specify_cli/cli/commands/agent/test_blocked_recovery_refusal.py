"""F-51 ATDD (#3937): honest single-stage refusal out of ``blocked``.

Red-first (charter C-011). These pin OBSERVABLE STATE / refusal IDENTITY, never
message substrings alone (research Decision 3 / NFR-001):

* ``blocked -> planned`` with NO feedback is refused as an ILLEGAL TRANSITION
  whose refusal enumerates the legal targets ``{in_progress, canceled}`` — it is
  NOT gated behind a demand for ``--review-feedback-file`` (C3 part 1).
* ``blocked -> planned`` WITH a ``--review-feedback-file`` keeps the SAME verdict
  (still illegal, same enumerated targets) — a review artifact cannot launder a
  structurally illegal transition (C3 part 2).
* A review-family rollback (``in_review -> planned``) with NO feedback STILL
  demands review feedback — the requirement is unchanged for the lanes that
  legitimately roll back to ``planned`` (C4 regression).
* Starting implementation on a genuinely ``blocked`` WP names the legal recovery
  command for the current state (FR-007 / C5).

The pure guard early-return (C-002) is asserted directly on
``_guard_planned_rollback`` so the source-lane scoping is proven without the
emit round-trip.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app
from specify_cli.cli.commands.agent.tasks_move_task import _invalid_transition_diagnostic
from specify_cli.cli.commands.agent.tasks_transition_core import (
    RefuseExit1,
    _guard_planned_rollback,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from specify_cli.status.work_package_lifecycle import (
    WorkPackageStartRejected,
    start_implementation_status,
)
from tests.mocked_env import setup_mocked_env

from .test_tasks_transition_core import _base_request

pytestmark = [pytest.mark.integration, pytest.mark.fast]

runner = CliRunner()


# ---------------------------------------------------------------------------
# Harness: seed a WP at a lane and drive the REAL move-task entry point.
# ---------------------------------------------------------------------------


def _seed_wp_in_lane(tmp_path: Path, *, mission_slug: str, wp_id: str, lane: str) -> Path:
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    (feature_dir / "tasks").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".kittify").mkdir(exist_ok=True)
    (feature_dir / "tasks" / f"{wp_id}-test.md").write_text(
        f"---\nwork_package_id: {wp_id}\ntitle: Test {wp_id}\n"
        f"execution_mode: code_change\nagent: testbot\n"
        f"subtasks: []\n"
        f"owned_files:\n  - src/{wp_id.lower()}/**\n"
        f"authoritative_surface: src/{wp_id.lower()}/\n---\n\n# {wp_id}\n\n## Activity Log\n",
        encoding="utf-8",
    )
    append_event(
        feature_dir,
        StatusEvent(
            event_id=f"seed-{wp_id}-{lane}",
            mission_slug=mission_slug,
            wp_id=wp_id,
            from_lane=Lane.PLANNED,
            to_lane=Lane(lane),
            at="2026-01-01T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
            reason=f"seed to {lane}",
        ),
    )
    return feature_dir


def _json_envelope(output: str) -> dict[str, object]:
    """Return the first line of ``output`` that parses as a JSON object.

    ``move-task`` prints incidental warnings (e.g. orphaned-event meta notices)
    as plain text; only the ``--json`` error envelope is a JSON object.
    """
    for line in output.strip().splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise AssertionError(f"no JSON envelope found in output:\n{output}")


def _move_to_planned(tmp_path: Path, mission_slug: str, wp_id: str, *, feedback: Path | None = None) -> tuple[int, dict[str, object], str]:
    args = [
        "move-task",
        wp_id,
        "--to",
        "planned",
        "--mission",
        mission_slug,
        "--no-auto-commit",
        "--json",
    ]
    if feedback is not None:
        args += ["--review-feedback-file", str(feedback)]
    with setup_mocked_env(tmp_path, mission_slug=mission_slug, workspace_resolution=FileNotFoundError):
        result = runner.invoke(app, args, catch_exceptions=False)
    return result.exit_code, _json_envelope(result.output), result.output


# ---------------------------------------------------------------------------
# C3 part 1 — blocked -> planned, NO feedback: honest illegal-transition refusal
# ---------------------------------------------------------------------------


def test_blocked_to_planned_without_feedback_is_illegal_and_enumerates_targets(
    tmp_path: Path,
) -> None:
    slug = "f51-blocked-nofeedback"
    _seed_wp_in_lane(tmp_path, mission_slug=slug, wp_id="WP05", lane="blocked")

    exit_code, envelope, output = _move_to_planned(tmp_path, slug, "WP05")

    assert exit_code == 1
    # Refusal IDENTITY: an illegal transition, NOT a feedback demand.
    assert envelope.get("code") == "invalid_transition"
    # Enumerates the legal targets, sourced from the authoritative per-state object.
    assert set(envelope.get("allowed_targets", [])) == {"in_progress", "canceled"}
    # NOT coerced toward a fabricated review artifact.
    assert "--review-feedback-file" not in output
    assert "requires review feedback" not in output


@pytest.mark.parametrize("source_lane", ["for_review", "claimed"])
def test_run_affecting_rollback_to_planned_still_demands_feedback(tmp_path: Path, source_lane: str) -> None:
    """A `-> planned` rollback from a RUN-AFFECTING lane whose forward
    `allowed_targets()` happens to lack `planned` (`for_review`, `claimed`) is
    still a genuine rework rollback that the move-task APPLIES (via its rollback
    path), so the feedback demand must STILL fire — it must NOT be silently
    applied, nor refused as an illegal transition. Regression guard for the
    `allowed_targets()`-proxy hole (#3937 F-51): the predicate keys on
    `is_run_affecting`, not `planned in allowed_targets()`."""
    slug = f"f51-{source_lane}-nofeedback"
    _seed_wp_in_lane(tmp_path, mission_slug=slug, wp_id="WP05", lane=source_lane)

    exit_code, envelope, output = _move_to_planned(tmp_path, slug, "WP05")

    # Refused, and specifically as a FEEDBACK DEMAND (not applied, not illegal).
    assert exit_code == 1
    assert envelope.get("code") != "invalid_transition"
    assert "--review-feedback-file" in output
    assert "requires review feedback" in output


# ---------------------------------------------------------------------------
# C3 part 2 — a review artifact cannot launder an illegal transition
# ---------------------------------------------------------------------------


def test_blocked_to_planned_with_feedback_is_still_illegal(tmp_path: Path) -> None:
    slug = "f51-blocked-withfeedback"
    _seed_wp_in_lane(tmp_path, mission_slug=slug, wp_id="WP05", lane="blocked")
    feedback = tmp_path / "feedback.md"
    feedback.write_text("**Issue**: cannot launder an illegal edge.\n", encoding="utf-8")

    exit_code, envelope, _ = _move_to_planned(tmp_path, slug, "WP05", feedback=feedback)

    # Verdict UNCHANGED versus the no-feedback case: still an illegal transition
    # with the same enumerated targets — the review artifact does not flip it.
    assert exit_code == 1
    assert envelope.get("code") == "invalid_transition"
    assert set(envelope.get("allowed_targets", [])) == {"in_progress", "canceled"}


# ---------------------------------------------------------------------------
# C4 regression — a review-family rollback still demands feedback
# ---------------------------------------------------------------------------


def test_in_review_to_planned_without_feedback_still_demands_feedback(
    tmp_path: Path,
) -> None:
    slug = "f51-inreview-regression"
    _seed_wp_in_lane(tmp_path, mission_slug=slug, wp_id="WP05", lane="in_review")

    exit_code, envelope, output = _move_to_planned(tmp_path, slug, "WP05")

    assert exit_code == 1
    # The review-feedback requirement is unchanged for a legitimate rollback:
    # it is NOT downgraded to an illegal-transition verdict.
    assert envelope.get("code") != "invalid_transition"
    assert "--review-feedback-file" in output
    assert "requires review feedback" in output


# ---------------------------------------------------------------------------
# C-002 — the guard early-returns for a non-review-family source (pure)
# ---------------------------------------------------------------------------


def test_guard_planned_rollback_early_returns_for_blocked_source() -> None:
    """``blocked`` is not a review-family source, so the review-feedback guard
    does not fire — the move falls through to FSM legality instead of demanding
    ``--review-feedback-file`` before legality is even checked."""
    outcome = _guard_planned_rollback(_base_request(target_lane="planned", old_lane="blocked", feedback_provided=False))
    assert outcome is None


def test_guard_planned_rollback_still_fires_for_review_family_source() -> None:
    """Regression: a review-family source (``in_review``) with no feedback still
    trips the review-feedback demand (C4 at the pure-guard layer)."""
    outcome = _guard_planned_rollback(_base_request(target_lane="planned", old_lane="in_review", feedback_provided=False))
    assert isinstance(outcome, RefuseExit1)
    assert "requires review feedback" in outcome.error


# ---------------------------------------------------------------------------
# FR-007 / C5 — start-implementation reject names the legal recovery command
# ---------------------------------------------------------------------------


def test_start_implementation_on_blocked_names_legal_recovery(tmp_path: Path) -> None:
    slug = "099-lifecycle-test"
    # Seed the blocked WP through the shared helper so the hard-coded ``at=``
    # literal stays out of this function — this test also calls
    # ``start_implementation_status`` (a now()-producing entry point), and
    # colocating both would trip the absolute-event-timestamp-mixture gate
    # (``tests/architectural/test_no_absolute_event_timestamp_mixture.py``)
    # even though the reject raises before any now() event is emitted.
    feature_dir = _seed_wp_in_lane(tmp_path, mission_slug=slug, wp_id="WP01", lane="blocked")

    with pytest.raises(WorkPackageStartRejected) as exc_info:
        start_implementation_status(
            feature_dir=feature_dir,
            mission_slug=slug,
            wp_id="WP01",
            actor="claude",
            workspace_context="worktree:/nonexistent/wp01",
            execution_mode="worktree",
            repo_root=tmp_path,
        )

    message = str(exc_info.value)
    # The existing contract phrase is preserved …
    assert "cannot start implementation" in message
    # … and the reject now NAMES the legal recovery command + target for a
    # blocked WP (allowed_targets = {in_progress, canceled}).
    assert "move-task" in message
    assert "in_progress" in message


# ---------------------------------------------------------------------------
# The extracted invalid-transition diagnostic helper (branch coverage)
# ---------------------------------------------------------------------------


def test_invalid_transition_diagnostic_enumerates_for_illegal_edge() -> None:
    diagnostic, error_text = _invalid_transition_diagnostic(Lane.BLOCKED, "planned", "Illegal transition: blocked -> planned")
    assert diagnostic["code"] == "invalid_transition"
    targets = diagnostic["allowed_targets"]
    assert isinstance(targets, list)
    assert set(targets) == {"in_progress", "canceled"}
    assert "Legal transitions from 'blocked'" in error_text
    assert diagnostic["error"] == error_text


def test_invalid_transition_diagnostic_terminal_source_has_empty_targets() -> None:
    diagnostic, error_text = _invalid_transition_diagnostic(Lane.DONE, "planned", "Illegal transition: done -> planned")
    # Terminal source: no legal forward targets to enumerate, no message append.
    assert diagnostic["allowed_targets"] == []
    assert error_text == "Illegal transition: done -> planned"


def test_invalid_transition_diagnostic_legal_edge_is_not_enriched() -> None:
    # A guard failure on a structurally-legal edge (in_progress -> planned is a
    # legal edge): no "where it can go" enumeration is added.
    diagnostic, error_text = _invalid_transition_diagnostic(Lane.IN_PROGRESS, "planned", "Transition in_progress -> planned requires reason")
    assert "allowed_targets" not in diagnostic
    assert error_text == "Transition in_progress -> planned requires reason"

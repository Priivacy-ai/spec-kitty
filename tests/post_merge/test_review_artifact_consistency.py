"""WP06 review artifact consistency gate tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from specify_cli.cli.commands.merge import _enforce_review_artifact_consistency
from specify_cli.post_merge.review_artifact_consistency import (
    REVIEW_ARTIFACT_SCHEMA_INVALID,
    find_rejected_review_artifact_conflicts,
    format_review_artifact_conflict,
    format_review_artifact_finding,
    review_artifact_conflict_diagnostic,
    review_artifact_finding_diagnostic,
)
from specify_cli.review.artifacts import ReviewCycleArtifact
from specify_cli.status.models import Lane, ReviewResult, StatusEvent
from specify_cli.status.store import append_event
from tests.reliability.fixtures import (
    WorkPackageSpec,
    append_status_event,
    create_mission_fixture,
    write_work_package,
)

pytestmark = pytest.mark.fast


def _write_review_artifact(
    artifact_dir: Path,
    *,
    cycle_number: int,
    verdict: str,
) -> Path:
    artifact = ReviewCycleArtifact(
        cycle_number=cycle_number,
        wp_id="WP01",
        mission_slug="release-320-workflow-reliability-01KQKV85",
        reviewer_agent="reviewer-renata",
        verdict=verdict,
        reviewed_at="2026-05-03T12:00:00+00:00",
        body=f"# Review\n\nVerdict: {verdict}\n",
    )
    path = artifact_dir / f"review-cycle-{cycle_number}.md"
    artifact.write(path)
    return path


def _write_malformed_review_artifact(
    artifact_dir: Path,
    *,
    cycle_number: int = 1,
) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"review-cycle-{cycle_number}.md"
    path.write_text(
        "---\n"
        "affected_files:\n"
        "  - src/foo.py\n"
        "cycle_number: 1\n"
        "mission_slug: release-320-workflow-reliability-01KQKV85\n"
        "reviewed_at: '2026-05-03T12:00:00+00:00'\n"
        "reviewer_agent: reviewer-renata\n"
        "verdict: approved\n"
        "wp_id: WP01\n"
        "---\n"
        "\n"
        "# Review\n",
        encoding="utf-8",
    )
    return path


def _write_review_artifact_with_invalid_verdict(artifact_dir: Path) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / "review-cycle-1.md"
    path.write_text(
        "---\n"
        "affected_files: []\n"
        "cycle_number: 1\n"
        "mission_slug: release-320-workflow-reliability-01KQKV85\n"
        "reviewed_at: '2026-05-03T12:00:00+00:00'\n"
        "reviewer_agent: reviewer-renata\n"
        "verdict: changes_requested\n"
        "wp_id: WP01\n"
        "---\n"
        "\n"
        "# Review\n",
        encoding="utf-8",
    )
    return path


def test_latest_rejected_review_artifact_conflicts_with_approved_wp(
    tmp_path: Path,
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KQKV85APPROVED000000001",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    rejected = _write_review_artifact(artifact_dir, cycle_number=2, verdict="rejected")

    findings = find_rejected_review_artifact_conflicts(mission.mission_dir)

    assert len(findings) == 1
    assert findings[0].wp_id == "WP01"
    assert findings[0].lane == "approved"
    assert findings[0].artifact_path == rejected
    assert "review-cycle-2.md has verdict 'rejected'" in format_review_artifact_conflict(
        findings[0],
        repo_root=mission.repo_root,
    )
    diagnostic = review_artifact_conflict_diagnostic(
        findings[0],
        repo_root=mission.repo_root,
    )
    assert diagnostic["diagnostic_code"] == "REJECTED_REVIEW_ARTIFACT_CONFLICT"
    assert diagnostic["branch_or_work_package"] == "WP01"
    assert (
        diagnostic["violated_invariant"]
        == "terminal_wp_latest_review_artifact_must_not_be_rejected"
    )
    assert diagnostic["latest_review_cycle_path"] == str(
        rejected.relative_to(mission.repo_root)
    )
    assert diagnostic["latest_review_cycle_verdict"] == "rejected"
    assert diagnostic["remediation"]


def test_find_conflicts_does_not_materialize_status_json(
    tmp_path: Path,
) -> None:
    """#2934: the merge-readiness check must not write ``status.json``.

    ``find_rejected_review_artifact_conflicts`` is a gate — it reads state to
    decide whether a rejected review blocks merge; it must not persist anything.
    It previously reduced via ``materialize`` (which writes ``status.json`` as a
    side effect). On a mission whose event log is empty/absent that orphaned a
    derived ``status.json`` with no backing ``status.events.jsonl`` — the invalid
    state ``validate`` flags — which the merge then committed alone. Reducing via
    the read-only ``materialize_snapshot`` removes the write while returning the
    identical snapshot.
    """
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KQKV85APPROVED000000001",
    )
    # Precondition: the fixture wrote only the event log, never status.json.
    assert not mission.status_snapshot_path.exists()

    findings = find_rejected_review_artifact_conflicts(mission.mission_dir)

    # Correctness preserved: no rejected review artifact → no findings.
    assert findings == []
    # The gate reads; it does not persist. No orphan status.json.
    assert not mission.status_snapshot_path.exists(), (
        "find_rejected_review_artifact_conflicts must not materialize "
        "status.json — a merge-readiness check reads, it does not persist (#2934)."
    )


def test_find_conflicts_does_not_orphan_snapshot_when_event_log_absent(
    tmp_path: Path,
) -> None:
    """#2934: an absent event log must remain absent without an orphan snapshot."""
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="planned"))

    assert not mission.status_events_path.exists()
    assert not mission.status_snapshot_path.exists()

    findings = find_rejected_review_artifact_conflicts(mission.mission_dir)

    assert findings == []
    assert not mission.status_events_path.exists()
    assert not mission.status_snapshot_path.exists(), (
        "an absent event log must not gain an orphan status.json during readiness checks"
    )


def test_latest_rejected_review_artifact_conflicts_with_done_wp(
    tmp_path: Path,
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="done"))
    append_status_event(
        mission,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        event_id="01KQKV85DONE00000000001",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_review_artifact(artifact_dir, cycle_number=1, verdict="approved")
    _write_review_artifact(artifact_dir, cycle_number=2, verdict="rejected")

    findings = find_rejected_review_artifact_conflicts(mission.mission_dir)

    assert len(findings) == 1
    assert findings[0].lane == "done"
    assert findings[0].cycle_number == 2


def test_later_approved_review_artifact_clears_rejected_conflict(
    tmp_path: Path,
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="done"))
    append_status_event(
        mission,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        event_id="01KQKV85DONE00000000001",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_review_artifact(artifact_dir, cycle_number=1, verdict="rejected")
    _write_review_artifact(artifact_dir, cycle_number=2, verdict="approved")

    assert find_rejected_review_artifact_conflicts(mission.mission_dir) == []


def test_shipped_writer_approval_after_rejection_clears_merge_gate(
    tmp_path: Path,
) -> None:
    """WP01 T007: integration test through the REAL shipped writer.

    Reject a WP (cycle 1) then approve it (cycle 2, ``verdict: approved``)
    using ``create_rejected_review_cycle`` itself — not the ``_write_review_artifact``
    test helper — then confirm the merge gate reports no conflict for that WP.
    Closes the loop from writer (WP01) to gate (this WP06 module), per
    spec.md User Story 1 Acceptance Scenario 2.
    """
    from specify_cli.review.cycle import create_rejected_review_cycle

    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="done"))
    append_status_event(
        mission,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        event_id="01KQKV85DONE00000000001",
    )

    rejection_feedback = tmp_path / "rejection-feedback.md"
    rejection_feedback.write_text("**Issue**: Missing regression test.\n", encoding="utf-8")
    rejected = create_rejected_review_cycle(
        main_repo_root=mission.repo_root,
        mission_slug=mission.mission_slug,
        wp_id="WP01",
        wp_slug="WP01-regression-harness",
        feedback_source=rejection_feedback,
        reviewer_agent="reviewer-renata",
    )
    assert rejected.artifact.verdict == "rejected"

    approval_feedback = tmp_path / "approval-feedback.md"
    approval_feedback.write_text(
        "Approved by reviewer-renata: the missing test was added.\n", encoding="utf-8"
    )
    approved = create_rejected_review_cycle(
        main_repo_root=mission.repo_root,
        mission_slug=mission.mission_slug,
        wp_id="WP01",
        wp_slug="WP01-regression-harness",
        feedback_source=approval_feedback,
        reviewer_agent="reviewer-renata",
        verdict="approved",
    )
    assert approved.artifact.verdict == "approved"
    assert approved.artifact.cycle_number == 2

    assert find_rejected_review_artifact_conflicts(mission.mission_dir) == []


def test_shipped_writer_genuine_rejection_still_blocks_merge_gate(
    tmp_path: Path,
) -> None:
    """Negative control for the test above: no regression to the existing,
    correct blocking behavior when the latest artifact genuinely IS rejected
    (only one cycle written through the real writer, never approved)."""
    from specify_cli.review.cycle import create_rejected_review_cycle

    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="done"))
    append_status_event(
        mission,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        event_id="01KQKV85DONE00000000001",
    )

    rejection_feedback = tmp_path / "rejection-feedback.md"
    rejection_feedback.write_text("**Issue**: Missing regression test.\n", encoding="utf-8")
    create_rejected_review_cycle(
        main_repo_root=mission.repo_root,
        mission_slug=mission.mission_slug,
        wp_id="WP01",
        wp_slug="WP01-regression-harness",
        feedback_source=rejection_feedback,
        reviewer_agent="reviewer-renata",
    )

    findings = find_rejected_review_artifact_conflicts(mission.mission_dir)

    assert len(findings) == 1
    assert findings[0].wp_id == "WP01"
    assert findings[0].verdict == "rejected"


def test_merge_review_artifact_consistency_gate_blocks_done_signoff(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="done"))
    append_status_event(
        mission,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        event_id="01KQKV85DONE00000000001",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_review_artifact(artifact_dir, cycle_number=1, verdict="rejected")

    with pytest.raises(typer.Exit) as exc_info:
        _enforce_review_artifact_consistency(
            repo_root=mission.repo_root,
            feature_dir=mission.mission_dir,
            mission_slug=mission.mission_slug,
            wp_ids=["WP01"],
        )

    assert exc_info.value.exit_code == 1
    output = capsys.readouterr().out
    assert "diagnostic_code: REJECTED_REVIEW_ARTIFACT_CONFLICT" in output
    assert "branch_or_work_package: WP01" in output
    assert (
        "violated_invariant: "
        "terminal_wp_latest_review_artifact_must_not_be_rejected"
    ) in output
    assert "latest_review_cycle_verdict: rejected" in output
    assert "remediation:" in output


def test_malformed_review_artifact_frontmatter_becomes_schema_diagnostic(
    tmp_path: Path,
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KQKV85APPROVED000000002",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    malformed = _write_malformed_review_artifact(artifact_dir)

    findings = find_rejected_review_artifact_conflicts(
        mission.mission_dir,
        wp_ids=["WP01"],
    )

    assert len(findings) == 1
    diagnostic = review_artifact_finding_diagnostic(
        findings[0],
        repo_root=mission.repo_root,
    )
    assert diagnostic["diagnostic_code"] == REVIEW_ARTIFACT_SCHEMA_INVALID
    assert diagnostic["branch_or_work_package"] == "WP01"
    assert (
        diagnostic["violated_invariant"]
        == "review_cycle_frontmatter_must_match_schema"
    )
    assert diagnostic["latest_review_cycle_path"] == str(
        malformed.relative_to(mission.repo_root)
    )
    assert "affected_files entries must be mappings" in diagnostic["schema_error"]
    assert "affected_files entries must be mappings" in format_review_artifact_finding(
        findings[0],
        repo_root=mission.repo_root,
    )


def test_invalid_top_level_review_artifact_field_becomes_schema_diagnostic(
    tmp_path: Path,
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KQKV85APPROVED000000003",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    malformed = _write_review_artifact_with_invalid_verdict(artifact_dir)

    findings = find_rejected_review_artifact_conflicts(
        mission.mission_dir,
        wp_ids=["WP01"],
    )

    assert len(findings) == 1
    diagnostic = review_artifact_finding_diagnostic(
        findings[0],
        repo_root=mission.repo_root,
    )
    assert diagnostic["diagnostic_code"] == REVIEW_ARTIFACT_SCHEMA_INVALID
    assert diagnostic["latest_review_cycle_path"] == str(
        malformed.relative_to(mission.repo_root)
    )
    assert diagnostic["schema_error"] == "verdict must be one of: approved, rejected"


def test_merge_review_artifact_consistency_gate_blocks_malformed_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="done"))
    append_status_event(
        mission,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        event_id="01KQKV85DONE00000000002",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_malformed_review_artifact(artifact_dir)

    with pytest.raises(typer.Exit) as exc_info:
        _enforce_review_artifact_consistency(
            repo_root=mission.repo_root,
            feature_dir=mission.mission_dir,
            mission_slug=mission.mission_slug,
            wp_ids=["WP01"],
        )

    assert exc_info.value.exit_code == 1
    output = capsys.readouterr().out
    assert "diagnostic_code: REVIEW_ARTIFACT_SCHEMA_INVALID" in output
    assert "branch_or_work_package: WP01" in output
    assert "violated_invariant: review_cycle_frontmatter_must_match_schema" in output
    assert "schema_error:" in output
    assert "Traceback" not in output


def test_terminal_wp_event_sourced_changes_requested_blocks_without_artifact(
    tmp_path: Path,
) -> None:
    """Fail-open gap: a terminal WP with NO on-disk review artifact at all must
    still be blocked when the event-sourced ``review_result`` verdict is
    ``changes_requested``.

    Before the fix, ``find_rejected_review_artifact_conflicts`` returned early
    (``if latest_path is None: continue``) the moment no ``review-cycle-*.md``
    file existed for a WP — never consulting ``_event_sourced_gate_verdict`` at
    all. A terminal-lane WP whose event log records a rejection (e.g. a
    ``--force`` exit from ``in_review`` that never wrote frontmatter) therefore
    passed the merge gate for free. This reproduces exactly that shape: WP01 is
    in the terminal ``approved`` lane, no ``review-cycle-*.md`` file exists
    anywhere under its tasks dir, and the reduced snapshot's ``review_result``
    slot carries ``verdict="changes_requested"``.
    """
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_event(
        mission.mission_dir,
        StatusEvent(
            event_id="01KQKV85APPROVEDNOARTIFACT1",
            mission_slug=mission.mission_slug,
            mission_id=mission.mission_id,
            wp_id="WP01",
            from_lane=Lane.IN_REVIEW,
            to_lane=Lane.APPROVED,
            at="2026-05-03T12:00:00+00:00",
            actor="operator",
            force=True,
            execution_mode="worktree",
            reason="force-approved despite rejection",
            review_result=ReviewResult(
                reviewer="reviewer-renata",
                verdict="changes_requested",
                reference="feedback://release-320-workflow-reliability-01KQKV85/WP01/1",
            ),
        ),
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    assert not artifact_dir.exists() or not list(
        artifact_dir.glob("review-cycle-*.md")
    ), "precondition: no on-disk review artifact must exist for this WP"

    findings = find_rejected_review_artifact_conflicts(mission.mission_dir)

    assert len(findings) == 1, (
        "a terminal WP with an event-sourced changes_requested verdict must "
        f"block merge even with no on-disk artifact, got: {findings}"
    )
    assert findings[0].wp_id == "WP01"
    assert findings[0].lane == "approved"
    assert findings[0].verdict == "changes_requested"
    assert findings[0].artifact_path is None

    message = format_review_artifact_conflict(findings[0], repo_root=mission.repo_root)
    assert "WP01" in message
    assert "changes_requested" in message

    diagnostic = review_artifact_conflict_diagnostic(
        findings[0], repo_root=mission.repo_root
    )
    assert diagnostic["diagnostic_code"] == "REJECTED_REVIEW_ARTIFACT_CONFLICT"
    assert diagnostic["latest_review_cycle_verdict"] == "changes_requested"
    assert diagnostic["latest_review_cycle_path"] is None


def test_terminal_wp_no_artifact_no_event_opinion_is_not_blocked(
    tmp_path: Path,
) -> None:
    """Guard against over-blocking: a terminal WP with NO on-disk artifact and
    NO event-sourced ``review_result`` opinion must NOT be flagged.

    This is the pre-existing, correct behaviour (an un-migrated mission, or a
    WP that never exited ``in_review``) — the fix above must not regress it.
    """
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KQKV85APPROVEDNOOPINION01",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    assert not artifact_dir.exists() or not list(
        artifact_dir.glob("review-cycle-*.md")
    ), "precondition: no on-disk review artifact must exist for this WP"

    findings = find_rejected_review_artifact_conflicts(mission.mission_dir)

    assert findings == [], (
        "no on-disk artifact and no event-sourced opinion must not block merge, "
        f"got: {findings}"
    )

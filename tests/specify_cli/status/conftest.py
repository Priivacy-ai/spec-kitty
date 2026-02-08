"""Shared fixtures for status model and transition tests."""

from __future__ import annotations

import pytest

from specify_cli.status.models import (
    DoneEvidence,
    Lane,
    RepoEvidence,
    ReviewApproval,
    StatusEvent,
    StatusSnapshot,
    VerificationResult,
)


@pytest.fixture
def sample_review_approval() -> ReviewApproval:
    return ReviewApproval(
        reviewer="reviewer-1",
        verdict="approved",
        reference="review-ref-001",
    )


@pytest.fixture
def sample_repo_evidence() -> RepoEvidence:
    return RepoEvidence(
        repo="my-org/my-repo",
        branch="034-feature-WP01",
        commit="abc1234",
        files_touched=["src/models.py", "tests/test_models.py"],
    )


@pytest.fixture
def sample_verification_result() -> VerificationResult:
    return VerificationResult(
        command="pytest tests/ -x -q",
        result="pass",
        summary="42 tests passed",
    )


@pytest.fixture
def sample_done_evidence(
    sample_review_approval: ReviewApproval,
    sample_repo_evidence: RepoEvidence,
    sample_verification_result: VerificationResult,
) -> DoneEvidence:
    return DoneEvidence(
        review=sample_review_approval,
        repos=[sample_repo_evidence],
        verification=[sample_verification_result],
    )


@pytest.fixture
def sample_status_event() -> StatusEvent:
    return StatusEvent(
        event_id="01HXYZ0123456789ABCDEFGHJK",
        feature_slug="034-feature-name",
        wp_id="WP01",
        from_lane=Lane.PLANNED,
        to_lane=Lane.CLAIMED,
        at="2026-02-08T12:00:00Z",
        actor="claude-opus",
        force=False,
        execution_mode="worktree",
    )


@pytest.fixture
def sample_status_event_with_evidence(
    sample_done_evidence: DoneEvidence,
) -> StatusEvent:
    return StatusEvent(
        event_id="01HXYZ0123456789ABCDEFGHJL",
        feature_slug="034-feature-name",
        wp_id="WP01",
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.DONE,
        at="2026-02-08T14:00:00Z",
        actor="reviewer-1",
        force=False,
        execution_mode="worktree",
        evidence=sample_done_evidence,
    )


@pytest.fixture
def sample_status_snapshot() -> StatusSnapshot:
    return StatusSnapshot(
        feature_slug="034-feature-name",
        materialized_at="2026-02-08T15:00:00Z",
        event_count=5,
        last_event_id="01HXYZ0123456789ABCDEFGHJM",
        work_packages={
            "WP01": {
                "lane": "done",
                "actor": "reviewer-1",
                "last_transition_at": "2026-02-08T14:00:00Z",
                "last_event_id": "01HXYZ0123456789ABCDEFGHJL",
                "force_count": 0,
            },
            "WP02": {
                "lane": "in_progress",
                "actor": "claude-opus",
                "last_transition_at": "2026-02-08T13:00:00Z",
                "last_event_id": "01HXYZ0123456789ABCDEFGHJK",
                "force_count": 0,
            },
        },
        summary={
            "planned": 0,
            "claimed": 0,
            "in_progress": 1,
            "for_review": 0,
            "done": 1,
            "blocked": 0,
            "canceled": 0,
        },
    )

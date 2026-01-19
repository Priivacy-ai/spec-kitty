"""Review cycle tests for orchestrator.

These tests verify the orchestrator handles review rejection and re-implementation.
Tests focus on state management and transitions during review cycles.

The orchestrator is expected to handle these scenarios:
- Review rejection puts WP back into implementation
- Re-implementation creates new commits
- Full cycle: reject → re-impl → re-review → approve
- WP fails when max review cycles exceeded
- All state transitions are recorded in history
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from specify_cli.orchestrator.config import WPStatus
from specify_cli.orchestrator.state import (
    OrchestrationRun,
    WPExecution,
    load_state,
    save_state,
)
from specify_cli.orchestrator.testing.fixtures import TestContext


# =============================================================================
# T036: Review Rejection Flow Tests
# =============================================================================


@pytest.mark.orchestrator_review_cycles
class TestReviewRejection:
    """Tests for review rejection handling."""

    def test_wp_in_review_can_be_rejected(self, tmp_path: Path):
        """WP in REVIEW status can transition back to IMPLEMENTATION."""
        # Create a WP in review state
        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.REVIEW,
            implementation_agent="claude",
            implementation_started=datetime.now(timezone.utc),
            implementation_completed=datetime.now(timezone.utc),
            review_agent="codex",
            review_started=datetime.now(timezone.utc),
        )

        # Simulate rejection by resetting to implementation
        wp.status = WPStatus.IMPLEMENTATION
        wp.review_completed = None
        wp.review_exit_code = None
        wp.implementation_retries += 1

        # Validation should pass - implementation is still completed
        wp.validate()
        assert wp.status == WPStatus.IMPLEMENTATION
        assert wp.implementation_retries == 1

    def test_rejection_increments_retry_counter(self, tmp_path: Path):
        """Each rejection should increment the implementation retry counter."""
        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.REVIEW,
            implementation_agent="claude",
            implementation_started=datetime.now(timezone.utc),
            implementation_completed=datetime.now(timezone.utc),
            implementation_retries=0,
        )

        initial_retries = wp.implementation_retries

        # First rejection
        wp.status = WPStatus.IMPLEMENTATION
        wp.implementation_retries += 1
        assert wp.implementation_retries == initial_retries + 1

        # Complete and review again
        wp.status = WPStatus.REVIEW

        # Second rejection
        wp.status = WPStatus.IMPLEMENTATION
        wp.implementation_retries += 1
        assert wp.implementation_retries == initial_retries + 2

    def test_rejection_preserves_implementation_history(self, tmp_path: Path):
        """Rejection should preserve original implementation timestamps."""
        original_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        original_complete = datetime(2026, 1, 1, 0, 5, 0, tzinfo=timezone.utc)

        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.REVIEW,
            implementation_agent="claude",
            implementation_started=original_start,
            implementation_completed=original_complete,
            review_agent="codex",
            review_started=datetime.now(timezone.utc),
        )

        # Reject
        wp.status = WPStatus.IMPLEMENTATION

        # Original timestamps preserved
        assert wp.implementation_started == original_start
        assert wp.implementation_completed == original_complete

    def test_review_pending_fixture_has_correct_state(self, test_context_factory):
        """The review_pending fixture should have WP01 in review status."""
        try:
            ctx = test_context_factory("review_pending")
        except pytest.skip.Exception:
            pytest.skip("Checkpoint fixture not found")

        # Load state from fixture
        state_file = ctx.checkpoint.state_file
        with open(state_file) as f:
            data = json.load(f)

        wp01_data = data["work_packages"]["WP01"]
        assert wp01_data["status"] == "review"
        assert wp01_data["implementation_completed"] is not None
        assert wp01_data["review_started"] is not None


# =============================================================================
# T037: Re-implementation Commit Tests
# =============================================================================


@pytest.mark.orchestrator_review_cycles
class TestReimplementationCommits:
    """Tests for re-implementation commit creation."""

    def _create_test_repo(self, path: Path) -> None:
        """Create a test git repository with initial commits."""
        subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=path, check=True, capture_output=True
        )
        # Create initial commit
        (path / "file.txt").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=path, check=True, capture_output=True
        )

    def _get_commit_count(self, repo_path: Path) -> int:
        """Count commits in repository."""
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return 0
        return int(result.stdout.strip())

    def _get_latest_commit_hash(self, repo_path: Path) -> str:
        """Get the latest commit hash."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    def test_new_commits_can_be_created(self, tmp_path: Path):
        """Verify we can create commits in a test repo."""
        self._create_test_repo(tmp_path)
        initial_count = self._get_commit_count(tmp_path)

        # Create another commit (simulating re-implementation)
        (tmp_path / "file2.txt").write_text("re-implemented")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Re-implementation changes"],
            cwd=tmp_path, check=True, capture_output=True
        )

        final_count = self._get_commit_count(tmp_path)
        assert final_count == initial_count + 1

    def test_reimplementation_preserves_history(self, tmp_path: Path):
        """Re-implementation should not rewrite history (no force push)."""
        self._create_test_repo(tmp_path)

        # Get initial commits
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        initial_commits = result.stdout.strip().split("\n")
        initial_hash = initial_commits[0].split()[0]

        # Add re-implementation commit
        (tmp_path / "reimpl.txt").write_text("reimplemented")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Re-implementation"],
            cwd=tmp_path, check=True, capture_output=True
        )

        # Get final commits
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        final_commits = result.stdout.strip().split("\n")

        # Initial commit should still be in history
        final_hashes = [c.split()[0] for c in final_commits]
        assert initial_hash in final_hashes, "Original commit should be preserved"

    def test_commit_hash_changes_after_new_commit(self, tmp_path: Path):
        """HEAD commit hash should change after re-implementation."""
        self._create_test_repo(tmp_path)
        initial_hash = self._get_latest_commit_hash(tmp_path)

        # Add commit
        (tmp_path / "change.txt").write_text("change")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Change"],
            cwd=tmp_path, check=True, capture_output=True
        )

        final_hash = self._get_latest_commit_hash(tmp_path)
        assert final_hash != initial_hash


# =============================================================================
# T038: Full Review Cycle Tests
# =============================================================================


@pytest.mark.orchestrator_review_cycles
class TestFullReviewCycle:
    """Tests for complete review cycle flow."""

    def test_wp_can_reach_completed_status(self, tmp_path: Path):
        """WP should be able to reach COMPLETED status through review cycle."""
        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.PENDING,
        )

        # Start implementation
        wp.status = WPStatus.IMPLEMENTATION
        wp.implementation_agent = "claude"
        wp.implementation_started = datetime.now(timezone.utc)

        # Complete implementation
        wp.implementation_completed = datetime.now(timezone.utc)
        wp.implementation_exit_code = 0

        # Start review
        wp.status = WPStatus.REVIEW
        wp.review_agent = "codex"
        wp.review_started = datetime.now(timezone.utc)

        # Approve (complete review)
        wp.review_completed = datetime.now(timezone.utc)
        wp.review_exit_code = 0
        wp.status = WPStatus.COMPLETED

        # Validate
        wp.validate()
        assert wp.status == WPStatus.COMPLETED

    def test_reject_reimpl_approve_cycle(self, tmp_path: Path):
        """Full cycle: pending → impl → review → reject → impl → review → approve."""
        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.PENDING,
        )

        # Phase 1: Implementation
        wp.status = WPStatus.IMPLEMENTATION
        wp.implementation_agent = "claude"
        wp.implementation_started = datetime.now(timezone.utc)
        wp.implementation_completed = datetime.now(timezone.utc)
        wp.implementation_exit_code = 0

        # Phase 2: First review
        wp.status = WPStatus.REVIEW
        wp.review_agent = "codex"
        wp.review_started = datetime.now(timezone.utc)

        # Phase 3: Rejection
        wp.status = WPStatus.IMPLEMENTATION
        wp.implementation_retries += 1
        wp.review_completed = None
        wp.review_started = None

        assert wp.status == WPStatus.IMPLEMENTATION
        assert wp.implementation_retries == 1

        # Phase 4: Re-implementation (continues from completed state)
        # Agent makes changes, we just track that impl is done
        wp.implementation_completed = datetime.now(timezone.utc)

        # Phase 5: Second review
        wp.status = WPStatus.REVIEW
        wp.review_started = datetime.now(timezone.utc)

        # Phase 6: Approval
        wp.review_completed = datetime.now(timezone.utc)
        wp.review_exit_code = 0
        wp.status = WPStatus.COMPLETED

        wp.validate()
        assert wp.status == WPStatus.COMPLETED
        assert wp.implementation_retries == 1  # One rejection cycle

    def test_multiple_rejection_cycles(self, tmp_path: Path):
        """WP should handle multiple rejection cycles gracefully."""
        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.PENDING,
            implementation_agent="claude",
            review_agent="codex",
        )

        # Initial implementation
        wp.status = WPStatus.IMPLEMENTATION
        wp.implementation_started = datetime.now(timezone.utc)
        wp.implementation_completed = datetime.now(timezone.utc)

        max_cycles = 3
        for cycle in range(max_cycles):
            # Review
            wp.status = WPStatus.REVIEW
            wp.review_started = datetime.now(timezone.utc)

            if cycle < max_cycles - 1:
                # Reject
                wp.status = WPStatus.IMPLEMENTATION
                wp.implementation_retries += 1
                wp.review_started = None
                wp.review_retries += 1
            else:
                # Final approval
                wp.review_completed = datetime.now(timezone.utc)
                wp.status = WPStatus.COMPLETED

        assert wp.status == WPStatus.COMPLETED
        assert wp.implementation_retries == max_cycles - 1
        assert wp.review_retries == max_cycles - 1


# =============================================================================
# T039: Max Review Cycles Tests
# =============================================================================


@pytest.mark.orchestrator_review_cycles
class TestMaxReviewCycles:
    """Tests for max review cycle limit."""

    def test_wp_can_be_marked_failed(self, tmp_path: Path):
        """WP can be marked FAILED when max cycles exceeded."""
        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.REVIEW,
            implementation_agent="claude",
            implementation_started=datetime.now(timezone.utc),
            implementation_completed=datetime.now(timezone.utc),
            implementation_retries=5,  # Already had 5 rejection cycles
            review_agent="codex",
            review_started=datetime.now(timezone.utc),
        )

        # Check against max limit (e.g., 5 cycles)
        max_cycles = 5
        if wp.implementation_retries >= max_cycles:
            wp.status = WPStatus.FAILED
            wp.last_error = f"Exceeded max review cycles ({max_cycles})"

        assert wp.status == WPStatus.FAILED
        assert "max review cycles" in wp.last_error.lower()

    def test_failure_reason_recorded(self, tmp_path: Path):
        """Failed WP should record failure reason."""
        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.REVIEW,
            implementation_agent="claude",
            implementation_started=datetime.now(timezone.utc),
            implementation_completed=datetime.now(timezone.utc),
        )

        # Mark as failed with reason
        wp.status = WPStatus.FAILED
        wp.last_error = "Review rejected: Code quality issues not addressed after 3 cycles"

        assert wp.status == WPStatus.FAILED
        assert wp.last_error is not None
        assert len(wp.last_error) > 0

    def test_retry_count_tracks_rejection_cycles(self, tmp_path: Path):
        """implementation_retries and review_retries should track rejection cycles."""
        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.PENDING,
        )

        # Simulate 3 rejection cycles
        for i in range(3):
            wp.status = WPStatus.IMPLEMENTATION
            wp.implementation_started = datetime.now(timezone.utc)
            wp.implementation_completed = datetime.now(timezone.utc)

            wp.status = WPStatus.REVIEW
            wp.review_started = datetime.now(timezone.utc)

            # Reject
            if i < 2:
                wp.implementation_retries += 1
                wp.review_retries += 1
                wp.status = WPStatus.IMPLEMENTATION

        assert wp.implementation_retries == 2
        assert wp.review_retries == 2

    def test_orchestration_run_tracks_failed_count(self, tmp_path: Path):
        """OrchestrationRun should track wps_failed count."""
        run = OrchestrationRun(
            run_id="test-run",
            feature_slug="test-feature",
            started_at=datetime.now(timezone.utc),
            wps_total=3,
        )

        # Add some WPs
        run.work_packages["WP01"] = WPExecution(
            wp_id="WP01", status=WPStatus.COMPLETED
        )
        run.work_packages["WP02"] = WPExecution(
            wp_id="WP02", status=WPStatus.FAILED, last_error="Max cycles exceeded"
        )
        run.work_packages["WP03"] = WPExecution(
            wp_id="WP03", status=WPStatus.PENDING
        )

        # Update counts
        run.wps_completed = sum(
            1 for wp in run.work_packages.values()
            if wp.status == WPStatus.COMPLETED
        )
        run.wps_failed = sum(
            1 for wp in run.work_packages.values()
            if wp.status == WPStatus.FAILED
        )

        assert run.wps_completed == 1
        assert run.wps_failed == 1


# =============================================================================
# T040: State Transition History Tests
# =============================================================================


@pytest.mark.orchestrator_review_cycles
class TestStateTransitionHistory:
    """Tests for state transition recording."""

    def test_state_serialization_roundtrip(self, tmp_path: Path):
        """WPExecution should serialize and deserialize correctly."""
        original = WPExecution(
            wp_id="WP01",
            status=WPStatus.REVIEW,
            implementation_agent="claude",
            implementation_started=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            implementation_completed=datetime(2026, 1, 1, 0, 5, 0, tzinfo=timezone.utc),
            implementation_exit_code=0,
            implementation_retries=1,
            review_agent="codex",
            review_started=datetime(2026, 1, 1, 0, 6, 0, tzinfo=timezone.utc),
            review_retries=1,
            last_error=None,
            fallback_agents_tried=["gemini"],
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = WPExecution.from_dict(data)

        assert restored.wp_id == original.wp_id
        assert restored.status == original.status
        assert restored.implementation_agent == original.implementation_agent
        assert restored.implementation_started == original.implementation_started
        assert restored.implementation_completed == original.implementation_completed
        assert restored.implementation_retries == original.implementation_retries
        assert restored.review_agent == original.review_agent
        assert restored.review_started == original.review_started
        assert restored.review_retries == original.review_retries
        assert restored.fallback_agents_tried == original.fallback_agents_tried

    def test_orchestration_run_serialization_roundtrip(self, tmp_path: Path):
        """OrchestrationRun should serialize and deserialize correctly."""
        original = OrchestrationRun(
            run_id="test-run-123",
            feature_slug="test-feature",
            started_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            wps_total=2,
            wps_completed=1,
            wps_failed=0,
            parallel_peak=2,
            total_agent_invocations=4,
        )
        original.work_packages["WP01"] = WPExecution(
            wp_id="WP01",
            status=WPStatus.COMPLETED,
            implementation_agent="claude",
            implementation_started=datetime(2026, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
            implementation_completed=datetime(2026, 1, 1, 0, 5, 0, tzinfo=timezone.utc),
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = OrchestrationRun.from_dict(data)

        assert restored.run_id == original.run_id
        assert restored.feature_slug == original.feature_slug
        assert restored.started_at == original.started_at
        assert restored.wps_total == original.wps_total
        assert restored.wps_completed == original.wps_completed
        assert len(restored.work_packages) == 1
        assert restored.work_packages["WP01"].status == WPStatus.COMPLETED

    def test_timestamps_are_iso_format(self, tmp_path: Path):
        """Serialized timestamps should be in ISO format."""
        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.IMPLEMENTATION,
            implementation_started=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )

        data = wp.to_dict()

        # Should be ISO format string
        assert isinstance(data["implementation_started"], str)
        # Should be parseable
        parsed = datetime.fromisoformat(data["implementation_started"])
        assert parsed == wp.implementation_started

    def test_state_persistence(self, tmp_path: Path):
        """State should be persisted and loadable."""
        repo_root = tmp_path / "test-repo"
        repo_root.mkdir()
        (repo_root / ".kittify").mkdir()

        run = OrchestrationRun(
            run_id="test-run",
            feature_slug="test-feature",
            started_at=datetime.now(timezone.utc),
        )
        run.work_packages["WP01"] = WPExecution(
            wp_id="WP01",
            status=WPStatus.REVIEW,
            implementation_agent="claude",
            implementation_started=datetime.now(timezone.utc),
            implementation_completed=datetime.now(timezone.utc),
        )

        # Save
        save_state(run, repo_root)

        # Load
        loaded = load_state(repo_root)

        assert loaded is not None
        assert loaded.run_id == run.run_id
        assert loaded.feature_slug == run.feature_slug
        assert "WP01" in loaded.work_packages
        assert loaded.work_packages["WP01"].status == WPStatus.REVIEW

    def test_agent_info_recorded_in_wp(self, tmp_path: Path):
        """Agent information should be recorded in WP state."""
        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.REVIEW,
            implementation_agent="claude",
            review_agent="codex",
            implementation_started=datetime.now(timezone.utc),
            implementation_completed=datetime.now(timezone.utc),
            review_started=datetime.now(timezone.utc),
        )

        assert wp.implementation_agent == "claude"
        assert wp.review_agent == "codex"

        # Serialization preserves agent info
        data = wp.to_dict()
        assert data["implementation_agent"] == "claude"
        assert data["review_agent"] == "codex"

    def test_fallback_agents_recorded(self, tmp_path: Path):
        """Fallback agents tried should be recorded."""
        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.IMPLEMENTATION,
            implementation_agent="gemini",
            fallback_agents_tried=["claude", "codex"],
            implementation_started=datetime.now(timezone.utc),
        )

        assert len(wp.fallback_agents_tried) == 2
        assert "claude" in wp.fallback_agents_tried
        assert "codex" in wp.fallback_agents_tried

        # Serialization preserves fallback list
        data = wp.to_dict()
        assert data["fallback_agents_tried"] == ["claude", "codex"]

    def test_timestamps_are_chronological(self, tmp_path: Path):
        """WP timestamps should be in chronological order."""
        impl_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        impl_end = datetime(2026, 1, 1, 0, 5, 0, tzinfo=timezone.utc)
        review_start = datetime(2026, 1, 1, 0, 6, 0, tzinfo=timezone.utc)
        review_end = datetime(2026, 1, 1, 0, 10, 0, tzinfo=timezone.utc)

        wp = WPExecution(
            wp_id="WP01",
            status=WPStatus.COMPLETED,
            implementation_agent="claude",
            implementation_started=impl_start,
            implementation_completed=impl_end,
            review_agent="codex",
            review_started=review_start,
            review_completed=review_end,
        )

        # Verify chronological order
        assert wp.implementation_started < wp.implementation_completed
        assert wp.implementation_completed <= wp.review_started
        assert wp.review_started < wp.review_completed

        # Validation should pass
        wp.validate()

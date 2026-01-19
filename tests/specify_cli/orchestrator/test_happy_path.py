"""Happy path end-to-end tests for orchestrator.

These tests verify the orchestrator completes successfully under normal conditions.

Tests implemented:
- T031: Single WP orchestration test
- T032: Multiple parallel WPs test
- T033: State validation test
- T034: Lane status consistency test
- T035: Commit verification test

Markers:
    @pytest.mark.slow - Expected to take >30 seconds
    @pytest.mark.orchestrator_happy_path - Happy path e2e tests
    @pytest.mark.core_agent - Requires core tier agent

Note:
    Tests in T033-T035 (state validation, lane consistency, commit verification)
    only test checkpoint fixtures and don't require agents.
    Tests in T031-T032 (e2e orchestration) require real agents and are skipped by default.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from specify_cli.orchestrator.testing.fixtures import TestContext
    from specify_cli.orchestrator.testing.paths import TestPath

# Direct path to fixtures (for tests that don't need agent detection)
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "orchestrator"


# =============================================================================
# Helper Functions
# =============================================================================


def setup_test_repo(ctx: TestContext) -> None:
    """Initialize a test git repository from checkpoint.

    Creates:
    - Git repo at ctx.repo_root
    - Feature directory with checkpoint files
    - .kittify directory for state
    """
    repo_root = ctx.repo_root
    checkpoint = ctx.checkpoint

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )

    # Copy feature directory from checkpoint
    if checkpoint and checkpoint.feature_dir.exists():
        feature_dest = ctx.feature_dir
        shutil.copytree(checkpoint.feature_dir, feature_dest)

    # Create .kittify directory
    kittify_dir = repo_root / ".kittify"
    kittify_dir.mkdir(exist_ok=True)

    # Create initial commit
    subprocess.run(
        ["git", "add", "."],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )


def read_wp_frontmatter(wp_file: Path) -> dict:
    """Extract YAML frontmatter from WP file."""
    import yaml

    content = wp_file.read_text()
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        raise ValueError(f"No frontmatter in {wp_file}")
    return yaml.safe_load(match.group(1))


def get_git_log(repo_path: Path, count: int = 5) -> list[str]:
    """Get recent commit messages from git log."""
    result = subprocess.run(
        ["git", "log", f"-{count}", "--oneline"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return result.stdout.strip().split("\n") if result.stdout.strip() else []


def get_commit_count(repo_path: Path) -> int:
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


async def run_test_orchestration(
    feature_dir: Path,
    repo_root: Path,
    test_path: TestPath,
    wp_ids: list[str] | None = None,
) -> dict:
    """Run orchestration for testing.

    This is a simplified orchestration runner for tests that:
    - Creates minimal config from test_path
    - Runs the orchestration loop
    - Returns the final state

    Args:
        feature_dir: Feature directory path
        repo_root: Repository root
        test_path: Test path with agent assignments
        wp_ids: Optional list of WP IDs to run (None = all)

    Returns:
        Dict with 'success', 'state', 'error' keys
    """
    from rich.console import Console

    from specify_cli.orchestrator.config import (
        AgentConfig,
        OrchestratorConfig,
    )
    from specify_cli.orchestrator.integration import run_orchestration_loop
    from specify_cli.orchestrator.state import OrchestrationRun, load_state

    # Build minimal config
    agents = {}
    if test_path.implementation_agent:
        agents[test_path.implementation_agent] = AgentConfig(
            agent_id=test_path.implementation_agent,
            enabled=True,
        )
    if test_path.review_agent and test_path.review_agent != test_path.implementation_agent:
        agents[test_path.review_agent] = AgentConfig(
            agent_id=test_path.review_agent,
            enabled=True,
        )

    config = OrchestratorConfig(
        agents=agents,
        defaults={
            "implementation": [test_path.implementation_agent] if test_path.implementation_agent else [],
            "review": [test_path.review_agent] if test_path.review_agent else [],
        },
        concurrency_limit=2,
        default_timeout=300,  # 5 minute timeout for tests
    )

    # Create initial state
    state = OrchestrationRun(
        run_id=f"test-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        feature_slug=feature_dir.name,
        started_at=datetime.now(timezone.utc),
    )

    # Run orchestration (suppress live display in tests)
    console = Console(quiet=True)
    try:
        await run_orchestration_loop(
            state=state,
            config=config,
            feature_dir=feature_dir,
            repo_root=repo_root,
            console=console,
            live_display=False,
        )
        return {
            "success": state.wps_failed == 0 and state.wps_completed > 0,
            "state": state,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "state": state,
            "error": str(e),
        }


# =============================================================================
# T031: Single WP Orchestration Tests
# =============================================================================


@pytest.mark.slow
@pytest.mark.orchestrator_happy_path
@pytest.mark.core_agent
class TestSingleWPOrchestration:
    """Tests for single work package orchestration."""

    @pytest.mark.skip(reason="E2E test requires real agents - run manually with --run-slow")
    def test_single_wp_completes_successfully(
        self,
        test_context_wp_created: TestContext,
    ) -> None:
        """A single WP should complete through implement→review→done."""
        ctx = test_context_wp_created

        # Setup test repository
        setup_test_repo(ctx)

        # Run orchestration
        result = asyncio.get_event_loop().run_until_complete(
            run_test_orchestration(
                feature_dir=ctx.feature_dir,
                repo_root=ctx.repo_root,
                test_path=ctx.test_path,
                wp_ids=["WP01"],
            )
        )

        # Assert success
        assert result["success"], f"Orchestration failed: {result['error']}"

        # Verify final state
        state = result["state"]
        assert state.wps_completed >= 1
        assert state.wps_failed == 0

        # Verify WP01 is in 'done' state
        wp_state = state.work_packages.get("WP01")
        assert wp_state is not None
        assert wp_state.status.value in ("completed", "done")

    @pytest.mark.skip(reason="E2E test requires real agents - run manually with --run-slow")
    def test_single_wp_creates_worktree(
        self,
        test_context_wp_created: TestContext,
    ) -> None:
        """Orchestration should create worktree for WP."""
        ctx = test_context_wp_created

        # Setup test repository
        setup_test_repo(ctx)

        result = asyncio.get_event_loop().run_until_complete(
            run_test_orchestration(
                feature_dir=ctx.feature_dir,
                repo_root=ctx.repo_root,
                test_path=ctx.test_path,
                wp_ids=["WP01"],
            )
        )

        assert result["success"]

        # Verify worktree was created
        worktrees_dir = ctx.worktrees_dir
        assert worktrees_dir.exists(), "Worktrees directory should be created"

        # Should have at least one worktree
        worktree_dirs = list(worktrees_dir.iterdir()) if worktrees_dir.exists() else []
        assert len(worktree_dirs) >= 1, "Should have at least one worktree"


# =============================================================================
# T032: Multiple Parallel WPs Tests
# =============================================================================


@pytest.mark.slow
@pytest.mark.orchestrator_happy_path
@pytest.mark.core_agent
class TestParallelWPOrchestration:
    """Tests for parallel work package orchestration."""

    @pytest.mark.skip(reason="E2E test requires real agents - run manually with --run-slow")
    def test_multiple_wps_all_reach_done(
        self,
        test_context_wp_created: TestContext,
    ) -> None:
        """All orchestrated WPs should reach 'done' state."""
        ctx = test_context_wp_created

        # Setup test repository
        setup_test_repo(ctx)

        result = asyncio.get_event_loop().run_until_complete(
            run_test_orchestration(
                feature_dir=ctx.feature_dir,
                repo_root=ctx.repo_root,
                test_path=ctx.test_path,
            )
        )

        assert result["success"]

        # All WPs should be done
        state = result["state"]
        for wp_id, wp_state in state.work_packages.items():
            assert wp_state.status.value in ("completed", "done"), (
                f"{wp_id} not done: {wp_state.status}"
            )

    @pytest.mark.skip(reason="E2E test requires real agents - run manually with --run-slow")
    def test_parallel_peak_recorded(
        self,
        test_context_wp_created: TestContext,
    ) -> None:
        """Orchestration should record peak parallelism."""
        ctx = test_context_wp_created

        # Setup test repository
        setup_test_repo(ctx)

        result = asyncio.get_event_loop().run_until_complete(
            run_test_orchestration(
                feature_dir=ctx.feature_dir,
                repo_root=ctx.repo_root,
                test_path=ctx.test_path,
            )
        )

        assert result["success"]

        # Should have recorded parallel peak
        state = result["state"]
        assert state.parallel_peak >= 1, "Should have parallel peak >= 1"


# =============================================================================
# Local Fixtures (for tests that don't need agents)
# =============================================================================


def get_checkpoint_state_file(checkpoint_name: str) -> Path:
    """Get state.json path for a checkpoint."""
    return FIXTURES_DIR / f"checkpoint_{checkpoint_name}" / "state.json"


def get_checkpoint_feature_dir(checkpoint_name: str) -> Path:
    """Get feature directory path for a checkpoint."""
    return FIXTURES_DIR / f"checkpoint_{checkpoint_name}" / "feature"


def get_checkpoint_worktrees_file(checkpoint_name: str) -> Path:
    """Get worktrees.json path for a checkpoint."""
    return FIXTURES_DIR / f"checkpoint_{checkpoint_name}" / "worktrees.json"


# =============================================================================
# T033: State Validation Tests
# =============================================================================


@pytest.mark.orchestrator_happy_path
class TestStateValidation:
    """Tests for orchestration state file integrity."""

    def test_state_file_structure_valid(self) -> None:
        """State file from checkpoint should have valid structure."""
        state_file = get_checkpoint_state_file("wp_created")
        if not state_file.exists():
            pytest.skip("No checkpoint state file available")

        with open(state_file) as f:
            state_data = json.load(f)

        # Check required fields
        assert "run_id" in state_data
        assert "feature_slug" in state_data
        assert "status" in state_data
        assert "work_packages" in state_data
        assert "wps_total" in state_data
        assert "wps_completed" in state_data
        assert "wps_failed" in state_data

    def test_state_counts_match_wps(self) -> None:
        """State counters should match actual WP states."""
        state_file = get_checkpoint_state_file("wp_created")
        if not state_file.exists():
            pytest.skip("No checkpoint state file available")

        with open(state_file) as f:
            state_data = json.load(f)

        # Count WPs by status
        wps = state_data.get("work_packages", {})
        assert state_data["wps_total"] == len(wps), (
            f"wps_total {state_data['wps_total']} != len(work_packages) {len(wps)}"
        )

    def test_state_timestamps_are_iso_format(self) -> None:
        """State timestamps should be valid ISO format."""
        state_file = get_checkpoint_state_file("wp_created")
        if not state_file.exists():
            pytest.skip("No checkpoint state file available")

        with open(state_file) as f:
            state_data = json.load(f)

        # Validate started_at
        started_at = state_data.get("started_at")
        assert started_at is not None
        # Should parse without error
        datetime.fromisoformat(started_at.replace("Z", "+00:00"))

    def test_wp_execution_fields_present(self) -> None:
        """WP execution should have required fields."""
        state_file = get_checkpoint_state_file("wp_created")
        if not state_file.exists():
            pytest.skip("No checkpoint state file available")

        with open(state_file) as f:
            state_data = json.load(f)

        wps = state_data.get("work_packages", {})
        required_fields = {"wp_id", "status"}

        for wp_id, wp in wps.items():
            missing = required_fields - set(wp.keys())
            assert not missing, f"{wp_id} missing required fields: {missing}"


# =============================================================================
# T034: Lane Status Consistency Tests
# =============================================================================


@pytest.mark.orchestrator_happy_path
class TestLaneConsistency:
    """Tests for lane status consistency between frontmatter and state."""

    def test_checkpoint_wp_frontmatter_exists(self) -> None:
        """WP files in checkpoint should have frontmatter."""
        tasks_dir = get_checkpoint_feature_dir("wp_created") / "tasks"
        if not tasks_dir.exists():
            pytest.skip("No tasks directory in checkpoint")

        wp_files = list(tasks_dir.glob("WP*.md"))
        assert len(wp_files) > 0, "Should have WP files"

        for wp_file in wp_files:
            frontmatter = read_wp_frontmatter(wp_file)
            assert "lane" in frontmatter, f"{wp_file.name} missing 'lane' in frontmatter"

    def test_wp_created_checkpoint_all_planned(self) -> None:
        """wp_created checkpoint should have all WPs in 'planned' lane."""
        tasks_dir = get_checkpoint_feature_dir("wp_created") / "tasks"
        if not tasks_dir.exists():
            pytest.skip("No tasks directory in checkpoint")

        for wp_file in tasks_dir.glob("WP*.md"):
            frontmatter = read_wp_frontmatter(wp_file)
            lane = frontmatter.get("lane")
            assert lane == "planned", f"{wp_file.name} should be in 'planned' lane, got '{lane}'"

    def test_wp_implemented_checkpoint_wp01_doing(self) -> None:
        """wp_implemented checkpoint should have WP01 in 'doing' lane."""
        tasks_dir = get_checkpoint_feature_dir("wp_implemented") / "tasks"
        wp01_file = tasks_dir / "WP01.md"

        if not wp01_file.exists():
            pytest.skip("WP01.md not found in checkpoint")

        frontmatter = read_wp_frontmatter(wp01_file)
        lane = frontmatter.get("lane")
        assert lane == "doing", f"WP01 should be in 'doing' lane, got '{lane}'"

    def test_review_pending_checkpoint_wp01_for_review(self) -> None:
        """review_pending checkpoint should have WP01 in 'for_review' lane."""
        tasks_dir = get_checkpoint_feature_dir("review_pending") / "tasks"
        wp01_file = tasks_dir / "WP01.md"

        if not wp01_file.exists():
            pytest.skip("WP01.md not found in checkpoint")

        frontmatter = read_wp_frontmatter(wp01_file)
        lane = frontmatter.get("lane")
        assert lane == "for_review", f"WP01 should be in 'for_review' lane, got '{lane}'"


# =============================================================================
# T035: Commit Verification Tests
# =============================================================================


@pytest.mark.orchestrator_happy_path
class TestCommitVerification:
    """Tests for git commit verification in worktrees."""

    def test_checkpoint_repo_structure(self) -> None:
        """Checkpoint should have expected directory structure."""
        checkpoint_dir = FIXTURES_DIR / "checkpoint_wp_created"

        # Should have feature directory
        assert (checkpoint_dir / "feature").exists(), "Feature dir should exist"

        # Should have state.json
        assert (checkpoint_dir / "state.json").exists(), "State file should exist"

        # Should have worktrees.json
        assert (checkpoint_dir / "worktrees.json").exists(), "Worktrees file should exist"

    def test_worktrees_json_valid(self) -> None:
        """Worktrees.json should be valid JSON with expected structure."""
        worktrees_file = get_checkpoint_worktrees_file("wp_implemented")
        if not worktrees_file.exists():
            pytest.skip("No worktrees.json in checkpoint")

        with open(worktrees_file) as f:
            data = json.load(f)

        assert "worktrees" in data, "Should have 'worktrees' key"
        assert isinstance(data["worktrees"], list), "'worktrees' should be a list"

        # Each worktree should have required fields
        for wt in data["worktrees"]:
            assert "wp_id" in wt, "Worktree should have 'wp_id'"
            assert "branch_name" in wt, "Worktree should have 'branch_name'"

    def test_wp_implemented_has_worktree(self) -> None:
        """wp_implemented checkpoint should have WP01 worktree entry."""
        worktrees_file = get_checkpoint_worktrees_file("wp_implemented")
        if not worktrees_file.exists():
            pytest.skip("No worktrees.json in checkpoint")

        with open(worktrees_file) as f:
            data = json.load(f)

        worktrees = data.get("worktrees", [])
        wp01_worktrees = [wt for wt in worktrees if wt.get("wp_id") == "WP01"]

        assert len(wp01_worktrees) >= 1, "Should have WP01 worktree entry"

    def test_wp_created_has_no_worktrees(self) -> None:
        """wp_created checkpoint should have no worktree entries."""
        worktrees_file = get_checkpoint_worktrees_file("wp_created")
        if not worktrees_file.exists():
            pytest.skip("No worktrees.json in checkpoint")

        with open(worktrees_file) as f:
            data = json.load(f)

        worktrees = data.get("worktrees", [])
        assert len(worktrees) == 0, "wp_created should have no worktrees"

    @pytest.mark.skip(reason="E2E test requires real agents - run manually with --run-slow")
    def test_worktree_has_implementation_commit(
        self,
        test_context_wp_created: TestContext,
    ) -> None:
        """Worktree should have commit from implementation phase."""
        ctx = test_context_wp_created

        # Setup and run orchestration
        setup_test_repo(ctx)

        result = asyncio.get_event_loop().run_until_complete(
            run_test_orchestration(
                feature_dir=ctx.feature_dir,
                repo_root=ctx.repo_root,
                test_path=ctx.test_path,
                wp_ids=["WP01"],
            )
        )

        assert result["success"]

        # Find WP01 worktree
        worktrees_dir = ctx.worktrees_dir
        wp01_dirs = list(worktrees_dir.glob("*WP01*")) if worktrees_dir.exists() else []

        if not wp01_dirs:
            pytest.skip("WP01 worktree not created")

        worktree_path = wp01_dirs[0]

        # Get commit count
        commit_count = get_commit_count(worktree_path)

        # Should have more than just initial commit
        assert commit_count > 1, f"Expected implementation commits, found only {commit_count}"

    @pytest.mark.skip(reason="E2E test requires real agents - run manually with --run-slow")
    def test_main_branch_unchanged_during_orchestration(
        self,
        test_context_wp_created: TestContext,
    ) -> None:
        """Main branch should not receive commits during orchestration."""
        ctx = test_context_wp_created

        # Setup test repository
        setup_test_repo(ctx)

        # Get initial main branch commit count
        initial_count = get_commit_count(ctx.repo_root)

        result = asyncio.get_event_loop().run_until_complete(
            run_test_orchestration(
                feature_dir=ctx.feature_dir,
                repo_root=ctx.repo_root,
                test_path=ctx.test_path,
                wp_ids=["WP01"],
            )
        )

        assert result["success"]

        # Main branch should have same commit count
        final_count = get_commit_count(ctx.repo_root)

        assert final_count == initial_count, (
            f"Main branch modified: {initial_count} -> {final_count} commits"
        )

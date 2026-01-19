"""Tests for orchestrator conftest fixtures.

Verifies that the fixtures defined in conftest.py work correctly.
These tests mock agent detection to avoid slow real agent calls.
"""

from __future__ import annotations

import pytest

from specify_cli.orchestrator.testing.availability import AgentAvailability


# =============================================================================
# Mock Fixtures for Testing (override real agent detection)
# =============================================================================


@pytest.fixture(scope="module")
def mock_agents():
    """Provide mock agent data for testing."""
    return [
        AgentAvailability(
            agent_id="claude",
            is_installed=True,
            is_authenticated=True,
            tier="core",
            failure_reason=None,
        ),
        AgentAvailability(
            agent_id="codex",
            is_installed=True,
            is_authenticated=True,
            tier="core",
            failure_reason=None,
        ),
        AgentAvailability(
            agent_id="gemini",
            is_installed=True,
            is_authenticated=True,
            tier="core",
            failure_reason=None,
        ),
        AgentAvailability(
            agent_id="cursor",
            is_installed=True,
            is_authenticated=False,
            tier="extended",
            failure_reason="Not authenticated",
        ),
    ]


# =============================================================================
# Agent Fixture Tests (with mocking)
# =============================================================================


class TestAgentFixturesWithMock:
    """Tests for agent availability fixtures using mocked agents."""

    def test_available_agents_returns_dict(self, mock_agents):
        """available_agents fixture should return a dict."""
        import asyncio

        async def mock_detect():
            return mock_agents

        # Simulate what available_agents fixture does
        loop = asyncio.new_event_loop()
        try:
            agents_list = loop.run_until_complete(mock_detect())
            result = {a.agent_id: a for a in agents_list}
        finally:
            loop.close()

        assert isinstance(result, dict)
        assert len(result) == 4
        assert "claude" in result
        assert "codex" in result

    def test_available_agent_ids_sorted(self, mock_agents):
        """available_agent_ids should return sorted list of authenticated agents."""
        # Simulate the fixture logic
        agents_dict = {a.agent_id: a for a in mock_agents}
        result = sorted([
            agent_id for agent_id, avail in agents_dict.items()
            if avail.is_authenticated
        ])

        assert isinstance(result, list)
        assert result == sorted(result)
        # cursor is not authenticated, so only 3 agents
        assert len(result) == 3
        assert "cursor" not in result

    def test_core_agents_filtered(self, mock_agents):
        """core_agents_available should only include core tier agents."""
        from tests.specify_cli.orchestrator.conftest import CORE_AGENTS

        agents_dict = {a.agent_id: a for a in mock_agents}
        result = sorted([
            agent_id for agent_id, avail in agents_dict.items()
            if avail.is_authenticated and agent_id in CORE_AGENTS
        ])

        # claude, codex, gemini are core agents
        assert "claude" in result
        assert "codex" in result
        assert "gemini" in result

    def test_extended_agents_filtered(self, mock_agents):
        """extended_agents_available should only include extended tier agents."""
        from tests.specify_cli.orchestrator.conftest import EXTENDED_AGENTS

        agents_dict = {a.agent_id: a for a in mock_agents}
        result = sorted([
            agent_id for agent_id, avail in agents_dict.items()
            if avail.is_authenticated and agent_id in EXTENDED_AGENTS
        ])

        # cursor would be extended but it's not authenticated
        assert len(result) == 0


# =============================================================================
# Test Path Fixture Tests
# =============================================================================


class TestTestPathFixtureLogic:
    """Tests for test path fixture logic."""

    def test_test_path_dataclass_has_required_fields(self):
        """TestPath should have all required fields."""
        from specify_cli.orchestrator.testing.paths import TestPath

        path = TestPath(
            path_type="2-agent",
            available_agents=["claude", "codex"],
            implementation_agent="claude",
            review_agent="codex",
            fallback_agent=None,
        )

        assert path.path_type == "2-agent"
        assert path.available_agents == ["claude", "codex"]
        assert path.implementation_agent == "claude"
        assert path.review_agent == "codex"
        assert path.fallback_agent is None

    def test_test_path_is_cross_agent_property(self):
        """TestPath.is_cross_agent should detect different agents."""
        from specify_cli.orchestrator.testing.paths import TestPath

        # Same agent (1-agent path)
        path1 = TestPath(
            path_type="1-agent",
            available_agents=["claude"],
            implementation_agent="claude",
            review_agent="claude",
            fallback_agent=None,
        )
        assert path1.is_cross_agent is False

        # Different agents (2-agent path)
        path2 = TestPath(
            path_type="2-agent",
            available_agents=["claude", "codex"],
            implementation_agent="claude",
            review_agent="codex",
            fallback_agent=None,
        )
        assert path2.is_cross_agent is True


# =============================================================================
# Test Context Fixture Tests
# =============================================================================


class TestTestContextFixtureLogic:
    """Tests for test context fixture logic."""

    def test_checkpoint_path_generation(self, tmp_path):
        """get_checkpoint_path should return correct path."""
        from tests.specify_cli.orchestrator.conftest import get_checkpoint_path

        path = get_checkpoint_path("wp_created")
        assert "checkpoint_wp_created" in str(path)
        assert path.name == "checkpoint_wp_created"

    def test_cleanup_function_handles_missing_dir(self, tmp_path):
        """_cleanup_test_context should not fail on missing directory."""
        from tests.specify_cli.orchestrator.conftest import _cleanup_test_context
        from specify_cli.orchestrator.testing.fixtures import TestContext
        from specify_cli.orchestrator.testing.paths import TestPath

        # Create a context with non-existent temp_dir
        test_path = TestPath(
            path_type="1-agent",
            available_agents=["claude"],
            implementation_agent="claude",
            review_agent="claude",
            fallback_agent=None,
        )

        ctx = TestContext(
            temp_dir=tmp_path / "nonexistent",
            repo_root=tmp_path,
            feature_dir=tmp_path / "feature",
            test_path=test_path,
            checkpoint=None,
            orchestration_state=None,
            worktrees=[],
        )

        # Should not raise
        _cleanup_test_context(ctx)


# =============================================================================
# Marker Tests
# =============================================================================


class TestMarkers:
    """Tests to verify markers work and don't cause warnings."""

    @pytest.mark.orchestrator_availability
    def test_orchestrator_availability_marker(self):
        """Marker should not cause warnings."""
        pass

    @pytest.mark.orchestrator_fixtures
    def test_orchestrator_fixtures_marker(self):
        """Marker should not cause warnings."""
        pass

    @pytest.mark.orchestrator_happy_path
    def test_orchestrator_happy_path_marker(self):
        """Marker should not cause warnings."""
        pass

    @pytest.mark.orchestrator_review_cycles
    def test_orchestrator_review_cycles_marker(self):
        """Marker should not cause warnings."""
        pass

    @pytest.mark.orchestrator_parallel
    def test_orchestrator_parallel_marker(self):
        """Marker should not cause warnings."""
        pass

    @pytest.mark.orchestrator_smoke
    def test_orchestrator_smoke_marker(self):
        """Marker should not cause warnings."""
        pass

    @pytest.mark.core_agent
    def test_core_agent_marker(self):
        """Marker should not cause warnings."""
        pass

    @pytest.mark.extended_agent
    def test_extended_agent_marker(self):
        """Marker should not cause warnings."""
        pass

    @pytest.mark.slow
    def test_slow_marker(self):
        """Marker should not cause warnings."""
        pass

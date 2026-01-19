"""Tests for test path selection logic.

Tests for WP02 implementation:
- T006: TestPath dataclass
- T007: determine_path_type function
- T008: assign_agents function
- T009: select_test_path with caching
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from specify_cli.orchestrator.testing.paths import (
    TestPath,
    assign_agents,
    clear_test_path_cache,
    determine_path_type,
    select_test_path,
)


# =============================================================================
# T006: TestPath dataclass tests
# =============================================================================


class TestTestPathDataclass:
    """Tests for TestPath dataclass properties."""

    def test_single_agent_path(self) -> None:
        """Single agent path has same impl and review agent."""
        path = TestPath(
            path_type="1-agent",
            available_agents=["claude"],
            implementation_agent="claude",
            review_agent="claude",
            fallback_agent=None,
        )

        assert path.path_type == "1-agent"
        assert path.is_cross_agent is False
        assert path.has_fallback is False
        assert path.agent_count == 1

    def test_two_agent_path(self) -> None:
        """Two agent path has different impl and review agents."""
        path = TestPath(
            path_type="2-agent",
            available_agents=["claude", "codex"],
            implementation_agent="claude",
            review_agent="codex",
            fallback_agent=None,
        )

        assert path.path_type == "2-agent"
        assert path.is_cross_agent is True
        assert path.has_fallback is False
        assert path.agent_count == 2

    def test_three_plus_agent_path(self) -> None:
        """Three+ agent path has fallback agent."""
        path = TestPath(
            path_type="3+-agent",
            available_agents=["claude", "codex", "gemini"],
            implementation_agent="claude",
            review_agent="codex",
            fallback_agent="gemini",
        )

        assert path.path_type == "3+-agent"
        assert path.is_cross_agent is True
        assert path.has_fallback is True
        assert path.agent_count == 3


# =============================================================================
# T007: determine_path_type tests
# =============================================================================


class TestDeterminePathType:
    """Tests for path type determination."""

    def test_zero_agents_raises_error(self) -> None:
        """Zero agents should raise ValueError."""
        with pytest.raises(ValueError, match="No agents available"):
            determine_path_type(0)

    def test_one_agent_returns_1_agent(self) -> None:
        """One agent returns 1-agent path."""
        assert determine_path_type(1) == "1-agent"

    def test_two_agents_returns_2_agent(self) -> None:
        """Two agents returns 2-agent path."""
        assert determine_path_type(2) == "2-agent"

    def test_three_agents_returns_3_plus_agent(self) -> None:
        """Three agents returns 3+-agent path."""
        assert determine_path_type(3) == "3+-agent"

    def test_many_agents_returns_3_plus_agent(self) -> None:
        """Many agents returns 3+-agent path."""
        assert determine_path_type(10) == "3+-agent"


# =============================================================================
# T008: assign_agents tests
# =============================================================================


class TestAssignAgents:
    """Tests for agent role assignment."""

    def test_empty_agents_raises_error(self) -> None:
        """Empty agent list should raise ValueError."""
        with pytest.raises(ValueError, match="No agents available"):
            assign_agents([], "1-agent")

    def test_single_agent_same_for_impl_and_review(self) -> None:
        """1-agent path uses same agent for both roles."""
        impl, review, fallback = assign_agents(["claude"], "1-agent")

        assert impl == "claude"
        assert review == "claude"
        assert fallback is None

    def test_two_agent_different_for_impl_and_review(self) -> None:
        """2-agent path uses different agents."""
        impl, review, fallback = assign_agents(["claude", "codex"], "2-agent")

        assert impl == "claude"  # First alphabetically
        assert review == "codex"  # Second alphabetically
        assert fallback is None

    def test_three_plus_agent_with_fallback(self) -> None:
        """3+-agent path includes fallback."""
        impl, review, fallback = assign_agents(
            ["gemini", "codex", "claude"], "3+-agent"
        )

        # Sorted alphabetically: claude, codex, gemini
        assert impl == "claude"
        assert review == "codex"
        assert fallback == "gemini"

    def test_deterministic_assignment_regardless_of_order(self) -> None:
        """Agent assignment is deterministic regardless of input order."""
        agents_order1 = ["gemini", "codex", "claude"]
        agents_order2 = ["claude", "gemini", "codex"]
        agents_order3 = ["codex", "claude", "gemini"]

        result1 = assign_agents(agents_order1, "3+-agent")
        result2 = assign_agents(agents_order2, "3+-agent")
        result3 = assign_agents(agents_order3, "3+-agent")

        # All should produce same result (sorted alphabetically)
        assert result1 == result2 == result3
        assert result1 == ("claude", "codex", "gemini")

    def test_two_agent_with_more_available(self) -> None:
        """2-agent path with 3+ agents only uses first two."""
        impl, review, fallback = assign_agents(
            ["claude", "codex", "gemini"], "2-agent"
        )

        assert impl == "claude"
        assert review == "codex"
        assert fallback is None  # Not assigned in 2-agent mode


# =============================================================================
# T009: select_test_path tests
# =============================================================================


class TestSelectTestPath:
    """Tests for the main select_test_path function.

    These tests use asyncio.run() directly to avoid pytest-asyncio version issues.
    The patching targets the availability module directly since paths.py imports
    from it inside the select_test_path function.
    """

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear the test path cache before and after each test."""
        clear_test_path_cache()
        yield
        clear_test_path_cache()

    def test_no_agents_available_raises_error(self) -> None:
        """Should raise ValueError when no agents available."""

        async def run_test():
            with patch(
                "specify_cli.orchestrator.testing.availability.detect_all_agents",
                new_callable=AsyncMock,
            ) as mock_detect:
                with patch(
                    "specify_cli.orchestrator.testing.availability.get_available_agents",
                    return_value=[],
                ):
                    mock_detect.return_value = None

                    with pytest.raises(
                        ValueError, match="No agents available for testing"
                    ):
                        await select_test_path()

        asyncio.run(run_test())

    def test_single_agent_path_selection(self) -> None:
        """Should select 1-agent path when one agent available."""

        async def run_test():
            with patch(
                "specify_cli.orchestrator.testing.availability.detect_all_agents",
                new_callable=AsyncMock,
            ) as mock_detect:
                with patch(
                    "specify_cli.orchestrator.testing.availability.get_available_agents",
                    return_value=["claude"],
                ):
                    mock_detect.return_value = None

                    path = await select_test_path()

                    assert path.path_type == "1-agent"
                    assert path.implementation_agent == "claude"
                    assert path.review_agent == "claude"
                    assert path.fallback_agent is None

        asyncio.run(run_test())

    def test_two_agent_path_selection(self) -> None:
        """Should select 2-agent path when two agents available."""

        async def run_test():
            with patch(
                "specify_cli.orchestrator.testing.availability.detect_all_agents",
                new_callable=AsyncMock,
            ) as mock_detect:
                with patch(
                    "specify_cli.orchestrator.testing.availability.get_available_agents",
                    return_value=["claude", "codex"],
                ):
                    mock_detect.return_value = None

                    path = await select_test_path()

                    assert path.path_type == "2-agent"
                    assert path.is_cross_agent is True

        asyncio.run(run_test())

    def test_three_plus_agent_path_selection(self) -> None:
        """Should select 3+-agent path when three+ agents available."""

        async def run_test():
            with patch(
                "specify_cli.orchestrator.testing.availability.detect_all_agents",
                new_callable=AsyncMock,
            ) as mock_detect:
                with patch(
                    "specify_cli.orchestrator.testing.availability.get_available_agents",
                    return_value=["claude", "codex", "gemini", "opencode"],
                ):
                    mock_detect.return_value = None

                    path = await select_test_path()

                    assert path.path_type == "3+-agent"
                    assert path.has_fallback is True
                    assert path.agent_count == 4

        asyncio.run(run_test())

    def test_force_path_overrides_detection(self) -> None:
        """force_path parameter should override automatic detection."""

        async def run_test():
            with patch(
                "specify_cli.orchestrator.testing.availability.detect_all_agents",
                new_callable=AsyncMock,
            ) as mock_detect:
                with patch(
                    "specify_cli.orchestrator.testing.availability.get_available_agents",
                    return_value=["claude", "codex", "gemini"],
                ):
                    mock_detect.return_value = None

                    # Would normally be 3+-agent, but force to 2-agent
                    path = await select_test_path(force_path="2-agent")

                    assert path.path_type == "2-agent"
                    # Not assigned in forced 2-agent
                    assert path.fallback_agent is None

        asyncio.run(run_test())

    def test_force_path_invalid_raises_error(self) -> None:
        """Invalid force_path should raise ValueError."""

        async def run_test():
            with patch(
                "specify_cli.orchestrator.testing.availability.detect_all_agents",
                new_callable=AsyncMock,
            ) as mock_detect:
                with patch(
                    "specify_cli.orchestrator.testing.availability.get_available_agents",
                    return_value=["claude"],
                ):
                    mock_detect.return_value = None

                    with pytest.raises(ValueError, match="Invalid force_path"):
                        await select_test_path(force_path="invalid-path")

        asyncio.run(run_test())

    def test_caching_returns_same_object(self) -> None:
        """Second call should return cached object without re-detecting."""

        async def run_test():
            with patch(
                "specify_cli.orchestrator.testing.availability.detect_all_agents",
                new_callable=AsyncMock,
            ) as mock_detect:
                with patch(
                    "specify_cli.orchestrator.testing.availability.get_available_agents",
                    return_value=["claude", "codex"],
                ):
                    mock_detect.return_value = None

                    path1 = await select_test_path()
                    path2 = await select_test_path()

                    # Should be same object
                    assert path1 is path2
                    # Should only detect once
                    assert mock_detect.call_count == 1

        asyncio.run(run_test())

    def test_force_path_bypasses_cache(self) -> None:
        """force_path should not use or update cache."""

        async def run_test():
            with patch(
                "specify_cli.orchestrator.testing.availability.detect_all_agents",
                new_callable=AsyncMock,
            ) as mock_detect:
                with patch(
                    "specify_cli.orchestrator.testing.availability.get_available_agents",
                    return_value=["claude", "codex", "gemini"],
                ):
                    mock_detect.return_value = None

                    # First call caches
                    path1 = await select_test_path()
                    assert path1.path_type == "3+-agent"

                    # Force path doesn't use cache
                    path2 = await select_test_path(force_path="1-agent")
                    assert path2.path_type == "1-agent"

                    # Original cache still intact
                    path3 = await select_test_path()
                    assert path3.path_type == "3+-agent"
                    assert path3 is path1

        asyncio.run(run_test())

    def test_clear_cache_forces_redetection(self) -> None:
        """clear_test_path_cache should force re-detection."""

        async def run_test():
            call_count = 0

            async def counting_detect():
                nonlocal call_count
                call_count += 1

            with patch(
                "specify_cli.orchestrator.testing.availability.detect_all_agents",
                side_effect=counting_detect,
            ):
                with patch(
                    "specify_cli.orchestrator.testing.availability.get_available_agents",
                    return_value=["claude"],
                ):
                    await select_test_path()
                    assert call_count == 1

                    # Clear cache and call again
                    clear_test_path_cache()
                    await select_test_path()
                    assert call_count == 2

        asyncio.run(run_test())

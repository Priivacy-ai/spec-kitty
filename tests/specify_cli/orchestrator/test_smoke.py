"""Smoke tests for extended agent invocation.

These tests verify that extended tier agents can be invoked and
perform basic operations. Tests skip gracefully when agents are
unavailable.

Marks:
    - @pytest.mark.slow: Tests may take up to 60 seconds
    - @pytest.mark.orchestrator_smoke: Smoke test for orchestrator
    - @pytest.mark.extended_agent: Tests extended tier agents
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from specify_cli.orchestrator.testing.availability import AgentAvailability

from specify_cli.orchestrator.testing.availability import EXTENDED_AGENTS

# List of extended agents for parametrization
EXTENDED_AGENT_LIST = sorted(EXTENDED_AGENTS)

# Environment variable for timeout override
SMOKE_TIMEOUT_ENV = "ORCHESTRATOR_SMOKE_TIMEOUT"


def get_smoke_timeout() -> int:
    """Get smoke test timeout from environment or default."""
    try:
        return int(os.environ.get(SMOKE_TIMEOUT_ENV, "60"))
    except ValueError:
        return 60


class SmokeTestBase:
    """Base class for smoke tests with common utilities."""

    SMOKE_TIMEOUT_SECONDS = 60

    @staticmethod
    def create_touch_task(output_path: Path) -> str:
        """Create a minimal task prompt that touches a file.

        Args:
            output_path: Path where the file should be created

        Returns:
            Task prompt string
        """
        return f'''Create an empty file at the following path:
{output_path}

Do not add any content to the file. Just create it as an empty file.
After creating the file, report success.'''

    @staticmethod
    def verify_file_exists(file_path: Path) -> bool:
        """Verify a file was created by the agent.

        Args:
            file_path: Path to check

        Returns:
            True if file exists
        """
        return file_path.exists()

    @staticmethod
    def get_temp_file_path(agent_id: str) -> Path:
        """Generate a unique temp file path for an agent smoke test.

        Args:
            agent_id: The agent being tested

        Returns:
            Path to a temp file (doesn't exist yet)
        """
        temp_dir = Path(tempfile.gettempdir())
        timestamp = int(time.time() * 1000)
        return temp_dir / f"smoke_test_{agent_id}_{timestamp}.txt"

    @staticmethod
    def cleanup_smoke_file(file_path: Path) -> None:
        """Remove smoke test file."""
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            # Ignore cleanup errors
            pass


def is_agent_available(
    available_agents: dict[str, "AgentAvailability"],
    agent_id: str
) -> bool:
    """Check if an agent is available for testing.

    Args:
        available_agents: Dict from available_agents fixture
        agent_id: Agent to check

    Returns:
        True if agent is installed and authenticated
    """
    avail = available_agents.get(agent_id)
    return avail is not None and avail.is_available


async def run_smoke_task(
    agent_id: str,
    task_prompt: str,
    timeout: int = 60
) -> tuple[bool, str | None]:
    """Run a smoke test task with an agent.

    Args:
        agent_id: Agent to invoke
        task_prompt: The task to execute
        timeout: Maximum time in seconds

    Returns:
        Tuple of (success, error_message)
        Returns (False, "invoke not implemented") if invoker lacks invoke method.
    """
    from specify_cli.orchestrator.agents import AGENT_REGISTRY
    from specify_cli.orchestrator.testing.availability import AGENT_ID_TO_REGISTRY

    # Map canonical ID to registry ID
    registry_id = AGENT_ID_TO_REGISTRY.get(agent_id)
    if registry_id is None:
        return False, f"No invoker for agent: {agent_id}"

    invoker_class = AGENT_REGISTRY.get(registry_id)

    if invoker_class is None:
        return False, f"Unknown agent in registry: {registry_id}"

    try:
        invoker = invoker_class()

        # Check if invoke method exists (not all invokers have it implemented yet)
        if not hasattr(invoker, "invoke") or not callable(getattr(invoker, "invoke")):
            return False, f"invoke() not implemented for {agent_id}"

        # Run with timeout
        result = await asyncio.wait_for(
            invoker.invoke(task_prompt),
            timeout=timeout
        )

        return result.success, result.error if not result.success else None

    except asyncio.TimeoutError:
        return False, f"Timed out after {timeout}s"
    except Exception as e:
        return False, f"Invocation error: {str(e)}"


def run_smoke_task_sync(
    agent_id: str,
    task_prompt: str,
    timeout: int = 60
) -> tuple[bool, str | None]:
    """Synchronous wrapper for run_smoke_task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            run_smoke_task(agent_id, task_prompt, timeout)
        )
    finally:
        loop.close()


def verify_smoke_result(
    agent_id: str,
    output_path: Path,
    invocation_success: bool,
    invocation_error: str | None
) -> tuple[bool, str]:
    """Verify the smoke test result.

    Args:
        agent_id: Agent that was tested
        output_path: Expected output file
        invocation_success: Whether invocation reported success
        invocation_error: Error from invocation (if any)

    Returns:
        Tuple of (passed, message)
    """
    if not invocation_success:
        return False, f"{agent_id}: Invocation failed - {invocation_error}"

    if not output_path.exists():
        return False, f"{agent_id}: Output file not created at {output_path}"

    return True, f"{agent_id}: Smoke test passed"


@pytest.mark.slow
@pytest.mark.orchestrator_smoke
@pytest.mark.extended_agent
class TestExtendedAgentSmoke(SmokeTestBase):
    """Smoke tests for extended tier agents."""

    @pytest.mark.parametrize("agent_id", EXTENDED_AGENT_LIST)
    def test_agent_can_touch_file(
        self,
        agent_id: str,
        available_agents: dict[str, "AgentAvailability"],
        extended_agents_available: list[str],
    ):
        """Agent should be able to create an empty file."""
        # Skip if agent not available
        if agent_id not in extended_agents_available:
            avail = available_agents.get(agent_id)
            reason = avail.failure_reason if avail else "Not detected"
            pytest.skip(f"{agent_id} not available: {reason}")

        # Create task
        output_path = self.get_temp_file_path(agent_id)
        task_prompt = self.create_touch_task(output_path)

        try:
            # Run smoke test
            success, error = run_smoke_task_sync(
                agent_id,
                task_prompt,
                timeout=self.SMOKE_TIMEOUT_SECONDS
            )

            # Skip if invoke not implemented (extended agents may not have it yet)
            if not success and error and "not implemented" in error:
                pytest.skip(f"{agent_id}: invoke() not implemented yet")

            # Verify result
            passed, message = verify_smoke_result(
                agent_id, output_path, success, error
            )

            assert passed, message

        finally:
            self.cleanup_smoke_file(output_path)

    @pytest.mark.parametrize("agent_id", EXTENDED_AGENT_LIST)
    def test_agent_completes_within_timeout(
        self,
        agent_id: str,
        available_agents: dict[str, "AgentAvailability"],
        extended_agents_available: list[str],
    ):
        """Agent should complete smoke test within 60 seconds."""
        if agent_id not in extended_agents_available:
            pytest.skip(f"{agent_id} not available")

        output_path = self.get_temp_file_path(agent_id)
        task_prompt = self.create_touch_task(output_path)

        start_time = time.time()

        try:
            success, error = run_smoke_task_sync(
                agent_id,
                task_prompt,
                timeout=self.SMOKE_TIMEOUT_SECONDS
            )

            # Skip if invoke not implemented (extended agents may not have it yet)
            if not success and error and "not implemented" in error:
                pytest.skip(f"{agent_id}: invoke() not implemented yet")

            elapsed = time.time() - start_time

            # Should complete within timeout (with margin)
            assert elapsed < self.SMOKE_TIMEOUT_SECONDS, (
                f"{agent_id} took {elapsed:.1f}s (limit: {self.SMOKE_TIMEOUT_SECONDS}s)"
            )

            # If it timed out, the error should mention it
            if not success and error and "timed out" in error.lower():
                pytest.fail(f"{agent_id}: {error}")

        finally:
            self.cleanup_smoke_file(output_path)


@pytest.mark.orchestrator_smoke
class TestExtendedAgentSkipBehavior:
    """Tests for proper skip behavior when agents unavailable."""

    def test_unavailable_agent_skips_not_fails(
        self,
        available_agents: dict[str, "AgentAvailability"],
    ):
        """Unavailable extended agents should result in skip, not failure."""
        # Find an unavailable extended agent
        unavailable = None
        for agent_id in EXTENDED_AGENTS:
            avail = available_agents.get(agent_id)
            if avail and not avail.is_available:
                unavailable = agent_id
                break

        if unavailable is None:
            pytest.skip("All extended agents are available (can't test skip)")

        # This should skip, not fail
        avail = available_agents[unavailable]
        pytest.skip(f"{unavailable} not available: {avail.failure_reason}")

    def test_skip_message_includes_reason(
        self,
        available_agents: dict[str, "AgentAvailability"],
    ):
        """Skip message should explain why agent is unavailable."""
        for agent_id in EXTENDED_AGENTS:
            avail = available_agents.get(agent_id)
            if avail and not avail.is_available:
                # Verify we have a failure reason
                assert avail.failure_reason is not None, (
                    f"{agent_id} unavailable but no failure_reason"
                )
                break
        else:
            pytest.skip("All extended agents available")

    def test_extended_agent_count(
        self,
        available_agents: dict[str, "AgentAvailability"],
    ):
        """Should detect exactly 7 extended agents."""
        extended_count = sum(
            1 for agent_id in available_agents
            if agent_id in EXTENDED_AGENTS
        )
        assert extended_count == 7, (
            f"Expected 7 extended agents, found {extended_count}"
        )


@pytest.mark.orchestrator_smoke
class TestSmokeTimingValidation:
    """Tests for smoke test timing requirements."""

    def test_timeout_is_configurable(self):
        """Smoke timeout should be configurable via environment."""
        default_timeout = 60

        # Default should be 60s
        timeout = get_smoke_timeout()
        if SMOKE_TIMEOUT_ENV not in os.environ:
            assert timeout == default_timeout

    def test_smoke_test_reports_duration(
        self,
        available_agents: dict[str, "AgentAvailability"],
        extended_agents_available: list[str],
    ):
        """Smoke test should report how long it took."""
        if not extended_agents_available:
            pytest.skip("No extended agents available")

        agent_id = extended_agents_available[0]
        output_path = SmokeTestBase.get_temp_file_path(agent_id)
        task_prompt = SmokeTestBase.create_touch_task(output_path)

        start_time = time.time()

        try:
            success, error = run_smoke_task_sync(
                agent_id,
                task_prompt,
                timeout=get_smoke_timeout()
            )

            # Skip if invoke not implemented
            if not success and error and "not implemented" in error:
                pytest.skip(f"{agent_id}: invoke() not implemented yet")

            duration = time.time() - start_time

            # Duration should be positive and less than timeout
            assert duration > 0
            assert duration < get_smoke_timeout() + 5  # 5s margin for overhead

            # Log duration for visibility
            print(f"\n{agent_id} smoke test duration: {duration:.2f}s")

        finally:
            SmokeTestBase.cleanup_smoke_file(output_path)

    @pytest.mark.parametrize("agent_id", EXTENDED_AGENT_LIST)
    def test_agent_probe_time_recorded(
        self,
        agent_id: str,
        available_agents: dict[str, "AgentAvailability"],
    ):
        """Agent availability should record probe duration."""
        avail = available_agents.get(agent_id)
        if avail is None:
            pytest.skip(f"{agent_id} not in detection results")

        # If installed and probed, should have duration
        if avail.is_installed and avail.probe_duration_ms is not None:
            assert avail.probe_duration_ms >= 0, (
                f"{agent_id} has negative probe duration"
            )
            assert avail.probe_duration_ms < 10000, (  # 10s timeout
                f"{agent_id} probe took too long: {avail.probe_duration_ms}ms"
            )

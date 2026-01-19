"""Configuration for orchestrator tests.

All timeouts and limits are configurable via environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class OrchestratorTestConfig:
    """Configuration for orchestrator tests."""

    # Agent detection
    probe_timeout_seconds: int = 10
    """Timeout for agent probe calls."""

    # Test execution
    test_timeout_seconds: int = 300
    """Default timeout for e2e tests."""

    smoke_timeout_seconds: int = 60
    """Timeout for smoke tests."""

    # Orchestration
    max_review_cycles: int = 3
    """Maximum review cycles before failure."""

    # Parallel timing
    parallel_start_tolerance_seconds: int = 30
    """Max time difference for 'parallel' start times."""

    @classmethod
    def from_environment(cls) -> "OrchestratorTestConfig":
        """Load configuration from environment variables.

        Environment variables:
            ORCHESTRATOR_PROBE_TIMEOUT: Probe timeout (default: 10)
            ORCHESTRATOR_TEST_TIMEOUT: Test timeout (default: 300)
            ORCHESTRATOR_SMOKE_TIMEOUT: Smoke test timeout (default: 60)
            ORCHESTRATOR_MAX_REVIEW_CYCLES: Max review cycles (default: 3)
            ORCHESTRATOR_PARALLEL_TOLERANCE: Parallel timing tolerance (default: 30)

        Returns:
            OrchestratorTestConfig with values from environment
        """
        return cls(
            probe_timeout_seconds=int(
                os.environ.get("ORCHESTRATOR_PROBE_TIMEOUT", "10")
            ),
            test_timeout_seconds=int(
                os.environ.get("ORCHESTRATOR_TEST_TIMEOUT", "300")
            ),
            smoke_timeout_seconds=int(
                os.environ.get("ORCHESTRATOR_SMOKE_TIMEOUT", "60")
            ),
            max_review_cycles=int(
                os.environ.get("ORCHESTRATOR_MAX_REVIEW_CYCLES", "3")
            ),
            parallel_start_tolerance_seconds=int(
                os.environ.get("ORCHESTRATOR_PARALLEL_TOLERANCE", "30")
            ),
        )


# Global config instance
_config: OrchestratorTestConfig | None = None


def get_config() -> OrchestratorTestConfig:
    """Get the test configuration (singleton).

    Returns:
        OrchestratorTestConfig instance
    """
    global _config
    if _config is None:
        _config = OrchestratorTestConfig.from_environment()
    return _config


def reset_config() -> None:
    """Reset configuration (for testing)."""
    global _config
    _config = None

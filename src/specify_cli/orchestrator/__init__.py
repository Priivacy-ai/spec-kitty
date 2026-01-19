"""Orchestrator package for autonomous multi-agent work package execution.

This package provides the infrastructure to orchestrate multiple AI agents
(Claude Code, Codex, Copilot, Gemini, etc.) to implement and review work
packages in parallel, with automatic fallback and retry handling.

Core Components:
    - Scheduler: Dependency resolution and agent assignment
    - Executor: Process spawning and management with asyncio
    - Monitor: Completion detection and failure handling
    - State Manager: Persistent orchestration state
    - Integration: Main orchestration loop connecting all components (WP09)

Configuration:
    - OrchestratorConfig: Main configuration dataclass
    - AgentConfig: Per-agent settings
    - load_config(): Load from .kittify/agents.yaml

Usage:
    from specify_cli.orchestrator import (
        OrchestratorConfig,
        AgentConfig,
        load_config,
        OrchestrationStatus,
        WPStatus,
        FallbackStrategy,
        run_orchestration_loop,
    )

    config = load_config(repo_root / ".kittify" / "agents.yaml")
"""

from specify_cli.orchestrator.config import (
    AgentConfig,
    ConfigValidationError,
    FallbackStrategy,
    OrchestratorConfig,
    OrchestrationStatus,
    WPStatus,
    generate_default_config,
    load_config,
)
from specify_cli.orchestrator.integration import (
    CircularDependencyError,
    NoAgentsError,
    OrchestrationError,
    ValidationError,
    print_summary,
    run_orchestration_loop,
    validate_agents,
    validate_feature,
)

__all__ = [
    # Enums
    "OrchestrationStatus",
    "WPStatus",
    "FallbackStrategy",
    # Config dataclasses
    "OrchestratorConfig",
    "AgentConfig",
    # Functions
    "load_config",
    "generate_default_config",
    "run_orchestration_loop",
    "validate_feature",
    "validate_agents",
    "print_summary",
    # Exceptions
    "ConfigValidationError",
    "OrchestrationError",
    "CircularDependencyError",
    "NoAgentsError",
    "ValidationError",
]

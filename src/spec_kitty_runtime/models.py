"""Core data structures for the lightweight runtime shim."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DiscoveryContext:
    """Template discovery settings passed by the CLI bridge."""

    project_dir: Path
    builtin_roots: list[Path]
    explicit_paths: list[Path] = field(default_factory=list)
    env_var_name: str = "SPEC_KITTY_MISSION_PATHS"
    user_home: Path = field(default_factory=Path.home)


@dataclass(frozen=True)
class MissionPolicySnapshot:
    """Compatibility placeholder for runtime policy metadata."""


@dataclass(frozen=True)
class MissionRunRef:
    """Reference to persisted runtime state on disk."""

    run_id: str
    run_dir: str
    mission_key: str


@dataclass(frozen=True)
class NextDecision:
    """Runtime decision returned to the CLI bridge."""

    kind: str
    run_id: str
    step_id: str | None = None
    reason: str | None = None
    decision_id: str | None = None
    input_key: str | None = None
    question: str | None = None
    options: list[str] | None = None


@dataclass(frozen=True)
class PendingDecision:
    """Pending decision metadata persisted in runtime state."""

    input_key: str
    question: str
    options: list[str]
    step_id: str


@dataclass
class RuntimeState:
    """On-disk mutable mission run state."""

    run_id: str
    mission_key: str
    steps: list[dict[str, object]]
    current_index: int = -1
    issued_step_id: str | None = None
    terminal: bool = False
    pending_decisions: dict[str, PendingDecision] = field(default_factory=dict)
    answered_inputs: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Snapshot:
    """Read-only snapshot used by tests and bridge logic."""

    run_id: str
    mission_key: str
    issued_step_id: str | None
    pending_decisions: dict[str, PendingDecision]
    current_index: int
    terminal: bool

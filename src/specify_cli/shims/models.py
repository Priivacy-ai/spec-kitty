"""Dataclasses for shim configuration.

ShimTemplate holds the per-skill, per-agent identity needed to generate
one shim markdown file.  AgentShimConfig groups all templates for a
single agent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShimTemplate:
    """Identity for a single shim markdown file.

    Attributes:
        command_name: Slash-command identifier, e.g. ``"spec-kitty.implement"``.
        cli_command:  CLI verb used in the shim body, e.g.
                      ``"spec-kitty agent shim implement"``.
        agent_name:   Agent key, e.g. ``"claude"``.
        filename:     Output filename, e.g. ``"spec-kitty.implement.md"``.
    """

    command_name: str
    cli_command: str
    agent_name: str
    filename: str


@dataclass(frozen=True)
class AgentShimConfig:
    """All shim templates for a single AI agent.

    Attributes:
        agent_key:      Config key, e.g. ``"claude"``.
        agent_dir:      Root directory, e.g. ``".claude"``.
        command_subdir: Subdirectory under agent_dir, e.g. ``"commands"``.
        templates:      Tuple of :class:`ShimTemplate` objects (one per skill).
    """

    agent_key: str
    agent_dir: str
    command_subdir: str
    templates: tuple[ShimTemplate, ...]

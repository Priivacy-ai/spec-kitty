"""Per-harness renderers for native agent profile projection.

Each renderer converts a resolved :class:`~charter.profiles.AgentProfile`
into the file format a specific tool expects for a *named agent* (a subagent
the user can pick from the tool's agent picker). A renderer owns three things:

* ``format_key`` -- the stable native-format identifier recorded in the manifest
  and in :class:`~specify_cli.tool_surface.model.NativeAgentProfile`.
* ``output_path`` -- where the rendered file lives, relative to the project root.
* ``render`` -- the file body (YAML frontmatter + Markdown instructions).

:func:`get_renderer` maps a tool key to its renderer, or ``None`` when the tool
has no verified native named-agent primitive. A ``None`` renderer is the signal
that the surface is a *research gap*: the provider emits an ``info`` finding
rather than treating the tool as healthy or broken.

Shared rendering helpers live in :mod:`._render_helpers` to avoid circular
imports between renderer modules (each renderer module was formerly importing
from this module, which itself imports from each renderer module to build the
registry -- a circular dependency).  The public helpers are re-exported below
for backward compatibility.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol, runtime_checkable

from charter.profiles import AgentProfile

from specify_cli.tool_surface.profiles._render_helpers import (
    _body_lines,
    _frontmatter_lines,
    _roles_csv,
    _yaml_scalar,
    render_markdown_agent as _render_markdown_agent,
)
from specify_cli.tool_surface.profiles.amazon_q_renderer import (
    AmazonQProfileRenderer,
)
from specify_cli.tool_surface.profiles.augment_renderer import (
    AugmentProfileRenderer,
)
from specify_cli.tool_surface.profiles.codex_renderer import (
    CodexProfileRenderer,
)

# Native format identifiers (stable strings recorded in the manifest).
FORMAT_CLAUDE_AGENT = "claude-agent"
FORMAT_COPILOT_AGENT = "copilot-agent"

# NOTE: FORMAT_AMAZON_Q_AGENT / FORMAT_AUGMENT_AGENT / FORMAT_CODEX_AGENT are
# NOT re-exported here. Their canonical home is the individual renderer modules
# (amazon_q_renderer / augment_renderer / codex_renderer); other src/ files
# import them from there directly.
__all__ = [
    "FORMAT_CLAUDE_AGENT",
    "FORMAT_COPILOT_AGENT",
]

# Directory / suffix fragments (hoisted: each appears in path + tests >=3x).
_CLAUDE_AGENTS_DIR = ".claude"
_AGENTS_SUBDIR = "agents"
_GITHUB_DIR = ".github"
_COPILOT_AGENT_SUFFIX = ".agent.md"

# A profile id becomes the *stem* of a native agent file (``<id>.md`` /
# ``<id>.agent.md``). It must therefore be a single safe path segment: no path
# separators, no traversal, no whitespace or control characters. The native
# formats agree on this constraint, so the check is renderer-agnostic.
_NATIVE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_NATIVE_NAME_TRAVERSAL = {".", ".."}


def native_name_violation(profile_id: str) -> str | None:
    """Return a reason string if ``profile_id`` is illegal as a native filename.

    Returns ``None`` for a legal id. A violation means the id cannot be used as
    the filename stem of a host-native agent file (``.claude/agents/<id>.md``)
    without escaping the agents directory or producing an unsafe path — the
    condition that surfaces as ``profile-name-invalid``.
    """
    if not profile_id:
        return "empty profile id has no native filename stem"
    if profile_id in _NATIVE_NAME_TRAVERSAL:
        return f"profile id {profile_id!r} is a path-traversal segment"
    if not _NATIVE_NAME_PATTERN.fullmatch(profile_id):
        return (
            f"profile id {profile_id!r} contains characters illegal in a "
            "native agent filename (allowed: letters, digits, '.', '_', '-')"
        )
    return None

# Re-export shared helpers for backward compatibility.
__all__ += [
    "_body_lines",
    "_frontmatter_lines",
    "_render_markdown_agent",
    "_roles_csv",
    "_yaml_scalar",
    "native_name_violation",
]


@runtime_checkable
class ProfileRenderer(Protocol):
    """Render contract a per-harness profile renderer must satisfy."""

    format_key: str

    def can_render(self, tool_key: str) -> bool:
        """Return whether this renderer handles ``tool_key``."""
        ...

    def output_path(
        self, tool_key: str, profile: AgentProfile, project_root: Path
    ) -> Path:
        """Return the absolute output path for ``profile`` under ``project_root``."""
        ...

    def render(self, profile: AgentProfile) -> str:
        """Return the file body (frontmatter + instructions) for ``profile``."""
        ...


class ClaudeCodeProfileRenderer:
    """Renderer for Claude Code project agents (``.claude/agents/<id>.md``)."""

    format_key = FORMAT_CLAUDE_AGENT

    def can_render(self, tool_key: str) -> bool:
        return tool_key == "claude"

    def output_path(
        self, tool_key: str, profile: AgentProfile, project_root: Path
    ) -> Path:
        _ = tool_key  # path is identical across the renderer's accepted tool keys
        return (
            project_root
            / _CLAUDE_AGENTS_DIR
            / _AGENTS_SUBDIR
            / f"{profile.profile_id}.md"
        )

    def render(self, profile: AgentProfile) -> str:
        return _render_markdown_agent(profile)


class CopilotProfileRenderer:
    """Renderer for Copilot/VS Code agents (``.github/agents/<id>.agent.md``)."""

    format_key = FORMAT_COPILOT_AGENT

    def can_render(self, tool_key: str) -> bool:
        return tool_key in ("copilot", "vscode")

    def output_path(
        self, tool_key: str, profile: AgentProfile, project_root: Path
    ) -> Path:
        _ = tool_key  # path is identical across the renderer's accepted tool keys
        return (
            project_root
            / _GITHUB_DIR
            / _AGENTS_SUBDIR
            / f"{profile.profile_id}{_COPILOT_AGENT_SUFFIX}"
        )

    def render(self, profile: AgentProfile) -> str:
        return _render_markdown_agent(profile)


# Ordered renderer registry: the first renderer whose ``can_render`` accepts the
# tool key wins. Tools absent from every renderer are research gaps (``None``).
_RENDERERS: tuple[ProfileRenderer, ...] = (
    ClaudeCodeProfileRenderer(),
    CopilotProfileRenderer(),
    CodexProfileRenderer(),
    AugmentProfileRenderer(),
    AmazonQProfileRenderer(),
)


def get_renderer(tool_key: str) -> ProfileRenderer | None:
    """Return the renderer for ``tool_key``, or ``None`` if unsupported.

    A ``None`` result means the tool has no verified native named-agent
    primitive and yields a research-gap finding rather than projected files.
    """
    for renderer in _RENDERERS:
        if renderer.can_render(tool_key):
            return renderer
    return None

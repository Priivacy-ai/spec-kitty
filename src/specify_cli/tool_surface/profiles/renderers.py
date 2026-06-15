"""Per-harness renderers for native agent profile projection.

Each renderer converts a resolved :class:`~charter.profiles.AgentProfile`
into the file format a specific tool expects for a *named agent* (a subagent
the user can pick from the tool's agent picker). A renderer owns three things:

* ``format_key`` -- the stable native-format identifier recorded in the manifest
  and in :class:`~specify_cli.tool_surface.model.NativeAgentProfile`.
* ``output_path`` -- where the rendered file lives, relative to the project root.
* ``render`` -- the file body (YAML frontmatter + Markdown instructions).

:func:`get_renderer` maps a tool key to its renderer, or ``None`` when the tool
has no verified native named-agent primitive (e.g. Codex). A ``None`` renderer is
the signal that the surface is a *research gap*: the provider emits an ``info``
finding rather than treating the tool as healthy or broken.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol, runtime_checkable

from charter.profiles import AgentProfile

# Native format identifiers (stable strings recorded in the manifest).
FORMAT_CLAUDE_AGENT = "claude-agent"
FORMAT_COPILOT_AGENT = "copilot-agent"

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


def _yaml_scalar(value: str) -> str:
    """Quote a scalar for single-line YAML frontmatter.

    Profile descriptions and purposes are free text that may contain colons or
    leading characters that would otherwise break a bare YAML scalar, so they
    are always double-quoted with internal quotes/backslashes escaped.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    # Collapse newlines so the value stays a single YAML line.
    escaped = escaped.replace("\n", " ").replace("\r", " ")
    return f'"{escaped}"'


def _roles_csv(profile: AgentProfile) -> str:
    return ", ".join(str(role) for role in profile.roles)


def _frontmatter_lines(profile: AgentProfile) -> list[str]:
    """Shared YAML frontmatter lines common to the supported native formats."""
    description = profile.description or profile.purpose
    return [
        "---",
        f"name: {profile.profile_id}",
        f"description: {_yaml_scalar(description)}",
        f"roles: [{_roles_csv(profile)}]",
        "---",
    ]


def _body_lines(profile: AgentProfile) -> list[str]:
    """Shared Markdown body describing the projected agent profile."""
    spec = profile.specialization
    return [
        f"# {profile.name}",
        "",
        profile.purpose,
        "",
        "## Specialization",
        "",
        f"- Primary focus: {spec.primary_focus}",
        f"- Avoidance boundary: {spec.avoidance_boundary or '(none declared)'}",
        "",
        (
            "_Projected from Spec Kitty agent profile "
            f"`{profile.profile_id}`; do not edit by hand._"
        ),
        "",
    ]


def _render_markdown_agent(profile: AgentProfile) -> str:
    """Render a Markdown agent file (frontmatter + body).

    Both the Claude Code ``claude-agent`` and Copilot ``copilot-agent`` formats
    are frontmatter-plus-Markdown; they share the same body and frontmatter
    shape, differing only in file extension and output directory.
    """
    lines = _frontmatter_lines(profile) + [""] + _body_lines(profile)
    return "\n".join(lines)


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
)


def get_renderer(tool_key: str) -> ProfileRenderer | None:
    """Return the renderer for ``tool_key``, or ``None`` if unsupported.

    A ``None`` result means the tool has no verified native named-agent
    primitive (e.g. ``codex``, ``unknown``) and yields a research-gap finding
    rather than projected files.
    """
    for renderer in _RENDERERS:
        if renderer.can_render(tool_key):
            return renderer
    return None

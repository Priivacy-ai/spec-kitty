"""Shared rendering helpers for native agent profile file formats.

This module provides the pure-function building blocks used by multiple
per-harness renderers.  Extracting them here avoids circular imports between
individual renderer modules and ``renderers.py`` (the registry module).

All functions in this module are intentionally private to the
``tool_surface.profiles`` subpackage (note the leading underscore in the module
name).  Renderers that share a rendering structure should import from here
rather than from each other or from ``renderers.py``.
"""

from __future__ import annotations

from charter.profiles import AgentProfile


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


def render_markdown_agent(profile: AgentProfile) -> str:
    """Render a Markdown agent file (frontmatter + body).

    Both the Claude Code ``claude-agent``, Copilot ``copilot-agent``, and
    Augment ``augment-agent`` formats are frontmatter-plus-Markdown; they share
    the same body and frontmatter shape, differing only in file extension and
    output directory.
    """
    lines = _frontmatter_lines(profile) + [""] + _body_lines(profile)
    return "\n".join(lines)

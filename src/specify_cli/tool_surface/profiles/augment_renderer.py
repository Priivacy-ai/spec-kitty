"""Augment Code native profile renderer.

Projects a :class:`~charter.profiles.AgentProfile` into a Markdown agent file at
``.augment/agents/<profile_id>.md``.

The Augment subagent format mirrors the Claude Code ``.claude/agents/`` pattern:
YAML frontmatter (``name``, ``description``, ``version``) followed by a Markdown
body containing the system prompt.  The shared
:func:`~specify_cli.tool_surface.profiles.renderers._render_markdown_agent`
helper is reused here because the two formats are structurally identical.
"""

from __future__ import annotations

from pathlib import Path

from charter.profiles import AgentProfile

from ._render_helpers import render_markdown_agent as _render_markdown_agent

# Native format identifier (stable string recorded in the manifest).
FORMAT_AUGMENT_AGENT = "augment-agent"

# Directory fragments (hoisted: appear in path + tests >=3x).
_AUGMENT_DIR = ".augment"
_AGENTS_SUBDIR = "agents"
_MD_SUFFIX = ".md"


class AugmentProfileRenderer:
    """Renderer for Augment Code project agents (``.augment/agents/<id>.md``).

    Project-local and manifest-tracked (``USER_GLOBAL = False``).
    """

    format_key: str = FORMAT_AUGMENT_AGENT

    #: Signals to callers that this renderer writes inside the project tree.
    USER_GLOBAL: bool = False

    def can_render(self, tool_key: str) -> bool:
        """Return ``True`` for the three Augment tool-key aliases."""
        return tool_key in {"auggie", "augment", FORMAT_AUGMENT_AGENT}

    def output_path(
        self, tool_key: str, profile: AgentProfile, project_root: Path
    ) -> Path:
        """Return ``.augment/agents/<profile_id>.md`` under *project_root*."""
        _ = tool_key  # path is identical across the renderer's accepted tool keys
        return (
            project_root
            / _AUGMENT_DIR
            / _AGENTS_SUBDIR
            / f"{profile.profile_id}{_MD_SUFFIX}"
        )

    def render(self, profile: AgentProfile) -> str:
        """Return the Markdown agent file body (frontmatter + instructions)."""
        return _render_markdown_agent(profile)

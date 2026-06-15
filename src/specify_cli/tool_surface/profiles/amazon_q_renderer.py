"""Amazon Q Developer CLI native profile renderer.

Projects a :class:`~charter.profiles.AgentProfile` into a JSON agent file at
``~/.aws/amazonq/cli-agents/<profile_id>.json``.

Key design decisions:

* **User-global, not project-local.** Amazon Q custom agent definitions live in
  the user's home directory (``~/.aws/amazonq/cli-agents/``), not in the project
  tree. This means the projected file is NOT tracked in the project manifest and
  NOT written to the project root.  The :attr:`USER_GLOBAL` flag signals this to
  callers (e.g. the provider's repair path).

* **JSON format.** The Amazon Q CLI agent spec requires ``.json`` files; Markdown
  frontmatter is not supported for this harness.

* **Doctor inspection via filesystem.** Because the file lives outside the
  project manifest, the doctor must check ``~/.aws/amazonq/cli-agents/`` directly
  rather than consulting ``ProfileManifest``. A missing file at the user-global
  path is expected (the user may not have run a repair yet), never an error.
"""

from __future__ import annotations

import json
from pathlib import Path

from charter.profiles import AgentProfile

# Native format identifier (stable string, never appears in the project manifest).
FORMAT_AMAZON_Q_AGENT = "amazon-q-agent"

# Directory fragments (hoisted: appear in path + tests >=3x).
_AWS_DIR = ".aws"
_AMAZONQ_SUBDIR = "amazonq"
_CLI_AGENTS_SUBDIR = "cli-agents"
_JSON_SUFFIX = ".json"


class AmazonQProfileRenderer:
    """Renderer for Amazon Q Developer CLI user-global agents.

    Outputs to ``~/.aws/amazonq/cli-agents/<profile_id>.json``.  Because the
    path is user-global (not inside the project tree) this renderer is **not**
    manifest-tracked; callers must inspect the filesystem directly.
    """

    format_key: str = FORMAT_AMAZON_Q_AGENT

    #: Signals to callers that this renderer writes outside the project tree.
    USER_GLOBAL: bool = True

    def can_render(self, tool_key: str) -> bool:
        """Return ``True`` for the three Amazon Q tool-key aliases."""
        return tool_key in {"q", "amazon-q", FORMAT_AMAZON_Q_AGENT}

    def output_path(
        self, tool_key: str, profile: AgentProfile, project_root: Path
    ) -> Path:
        """Return the user-global path for ``profile``.

        ``tool_key`` and ``project_root`` are accepted to satisfy the
        :class:`~specify_cli.tool_surface.profiles.renderers.ProfileRenderer`
        protocol, but both are intentionally ignored — the output path is
        always under ``~/.aws/``, independent of the project.
        """
        _ = tool_key, project_root
        return (
            Path.home()
            / _AWS_DIR
            / _AMAZONQ_SUBDIR
            / _CLI_AGENTS_SUBDIR
            / f"{profile.profile_id}{_JSON_SUFFIX}"
        )

    def render(self, profile: AgentProfile) -> str:
        """Return a JSON string for the Amazon Q CLI agent spec."""
        description = profile.description or profile.purpose or ""
        payload: dict[str, object] = {
            "name": profile.name or profile.profile_id,
            "description": description,
            "instructions": profile.purpose or "",
        }
        return json.dumps(payload, indent=2)

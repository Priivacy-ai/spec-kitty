"""Codex CLI native profile renderer.

Projects a :class:`~charter.profiles.AgentProfile` into a TOML agent file at
``.codex/agents/<profile_id>.toml``.  The Codex per-project agent format
(confirmed in research.md R-03) requires three fields:

* ``name`` -- display name shown in the Codex agent picker.
* ``description`` -- one-line summary of the agent's purpose.
* ``developer_instructions`` -- the system prompt body supplied to the agent.

Optional fields (``model``, ``model_reasoning_effort``, ``sandbox_mode``) are
emitted only when the profile carries them; unknown attributes are silently
skipped via :func:`getattr`.
"""

from __future__ import annotations

from pathlib import Path

from charter.profiles import AgentProfile

# Native format identifier (stable string recorded in the manifest).
FORMAT_CODEX_AGENT = "codex-agent"

# Directory fragments (hoisted: each appears in path + tests >=3x).
_CODEX_DIR = ".codex"
_CODEX_AGENTS_SUBDIR = "agents"
_CODEX_SUFFIX = ".toml"

# Codex-specific optional field names surfaced by some profile variants.
_FIELD_MODEL = "model"
_FIELD_REASONING_EFFORT = "model_reasoning_effort"
_FIELD_SANDBOX_MODE = "sandbox_mode"


def _optional_fields(profile: AgentProfile) -> dict[str, object]:
    """Collect optional TOML fields present on *profile*."""
    extras: dict[str, object] = {}
    model = getattr(profile, _FIELD_MODEL, None)
    if model:
        extras[_FIELD_MODEL] = model
    effort = getattr(profile, _FIELD_REASONING_EFFORT, None)
    if effort:
        extras[_FIELD_REASONING_EFFORT] = effort
    sandbox = getattr(profile, _FIELD_SANDBOX_MODE, None)
    if sandbox is not None:
        extras[_FIELD_SANDBOX_MODE] = sandbox
    return extras


class CodexProfileRenderer:
    """Renderer for Codex CLI per-project agents (``.codex/agents/<id>.toml``)."""

    format_key: str = FORMAT_CODEX_AGENT

    def can_render(self, tool_key: str) -> bool:
        """Return ``True`` for the three Codex tool-key aliases."""
        return tool_key in {"codex", "codex-cli", FORMAT_CODEX_AGENT}

    def output_path(
        self, tool_key: str, profile: AgentProfile, project_root: Path
    ) -> Path:
        """Return ``.codex/agents/<profile_id>.toml`` under *project_root*."""
        _ = tool_key  # path is identical across the renderer's accepted tool keys
        return (
            project_root
            / _CODEX_DIR
            / _CODEX_AGENTS_SUBDIR
            / f"{profile.profile_id}{_CODEX_SUFFIX}"
        )

    def render(self, profile: AgentProfile) -> str:
        """Return valid TOML text for the Codex per-project agent format.

        ``tomli_w`` is imported lazily here rather than at module load: it is a
        declared runtime dependency but is only needed on this Codex-rendering
        path, so a stale/mismatched install that is missing it must not brick
        every CLI command at import time (issue #2103). The guard turns the
        opaque ``ModuleNotFoundError`` into an actionable message.
        """
        try:
            import tomli_w
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "tomli_w is required to render Codex agent profiles but is not "
                "available in this environment. spec-kitty declares it as a "
                "runtime dependency, so this usually means a stale install — "
                "reinstall or upgrade spec-kitty (e.g. `uv tool upgrade "
                "spec-kitty`) so its declared dependencies are present."
            ) from exc

        description = profile.description or profile.purpose or ""
        doc: dict[str, object] = {
            "name": profile.name or profile.profile_id,
            "description": description,
            "developer_instructions": profile.purpose or "",
        }
        doc.update(_optional_fields(profile))
        return tomli_w.dumps(doc)

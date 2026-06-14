"""Project Spec Kitty agent profiles into host-native agent files.

:class:`ProfileProjector` reads resolved profiles from an
:class:`~doctrine.agent_profiles.repository.AgentProfileRepository` and renders
each into a :class:`~specify_cli.tool_surface.model.NativeAgentProfile` for a
given tool, using the per-harness renderer registry in :mod:`.renderers`.

The projector is *read-only* with respect to the profile model: it calls only
the repository's public query API (``list_all`` / ``get_provenance``) and never
mutates profiles, the DRG, or the scoring model. Tools without a native
named-agent primitive (no renderer) project to an empty list -- the provider
turns that into a research-gap finding.
"""

from __future__ import annotations

from pathlib import Path

from doctrine.agent_profiles.profile import AgentProfile
from doctrine.agent_profiles.repository import AgentProfileRepository

from ..model import NativeAgentProfile
from .renderers import ProfileRenderer, get_renderer

# Provenance layers exposed by ``AgentProfileRepository.get_provenance``.
LAYER_BUILTIN = "builtin"
LAYER_ORG = "org"
LAYER_PROJECT = "project"

_PROJECT_PROFILE_SUBDIR = ".kittify/agent-profiles"


def _profile_urn(profile: AgentProfile) -> str:
    """Return the DRG-style URN for ``profile`` (``agent_profile:<id>``)."""
    return f"agent_profile:{profile.profile_id}"


def default_profile_repository(project_root: Path) -> AgentProfileRepository:
    """Build the standard repository for ``project_root``.

    Built-in profiles always load from package data. Project overlay profiles
    load from ``.kittify/agent-profiles/`` when that directory exists; it is
    passed through unconditionally because the repository treats a missing
    ``project_dir`` gracefully (no overlay).
    """
    project_dir = project_root / _PROJECT_PROFILE_SUBDIR
    return AgentProfileRepository(project_dir=project_dir)


class ProfileProjector:
    """Project agent profiles into native agent files for a tool."""

    def __init__(self, profile_repo: AgentProfileRepository) -> None:
        self._repo = profile_repo

    def project(
        self,
        tool_key: str,
        project_root: Path,
        source_layers: list[str] | None = None,
    ) -> list[NativeAgentProfile]:
        """Project available profiles into native format for ``tool_key``.

        ``source_layers`` filters by provenance (``builtin``/``org``/
        ``project``); ``None`` projects every layer. Sentinel profiles (workflow
        routing signals, not agent identities) are never projected. Returns an
        empty list for tools without a native named-agent primitive.
        """
        renderer = get_renderer(tool_key)
        if renderer is None:
            return []
        layer_filter = set(source_layers) if source_layers is not None else None
        return [
            self._project_one(renderer, tool_key, profile, project_root)
            for profile in self._repo.list_all()
            if self._include(profile, layer_filter)
        ]

    def _include(
        self, profile: AgentProfile, layer_filter: set[str] | None
    ) -> bool:
        if profile.sentinel:
            return False
        if layer_filter is None:
            return True
        layer = self._repo.get_provenance(profile.profile_id) or LAYER_BUILTIN
        return layer in layer_filter

    def _project_one(
        self,
        renderer: ProfileRenderer,
        tool_key: str,
        profile: AgentProfile,
        project_root: Path,
    ) -> NativeAgentProfile:
        output_path = renderer.output_path(tool_key, profile, project_root)
        layer = self._repo.get_provenance(profile.profile_id) or LAYER_BUILTIN
        return NativeAgentProfile(
            profile_urn=_profile_urn(profile),
            source_layer=layer,
            tool_key=tool_key,
            output_path=output_path,
            format=renderer.format_key,
            file_hash=None,
        )

    def render(self, tool_key: str, profile_urn: str) -> str | None:
        """Render the native file body for one ``profile_urn`` and ``tool_key``.

        Returns ``None`` when the tool has no renderer or the profile id is not
        loaded. Used by the provider's repair path to obtain file content for a
        single projected surface without re-projecting the whole set.
        """
        renderer = get_renderer(tool_key)
        if renderer is None:
            return None
        profile_id = profile_urn.split(":", 1)[1] if ":" in profile_urn else profile_urn
        profile = self._repo.get(profile_id)
        if profile is None:
            return None
        return renderer.render(profile)

"""Native agent profile projection for the tool surface contract.

This subpackage projects Spec Kitty agent profiles (resolved by
:class:`charter.profiles.AgentProfileRepository`) into
host-native agent/subagent files (e.g. ``.claude/agents/<id>.md``,
``.github/agents/<id>.agent.md``) and tracks the projected files in a manifest
at ``.kittify/agent_profiles_manifest.json``.

The projection layer sits *on top of* the profile loading/scoring model: it
never mutates :class:`AgentProfileRepository` or the profile resolution graph,
it only reads resolved profiles and renders them to disk. Tools that have no
native named-agent primitive (e.g. Codex) yield no projected profiles -- the
provider surfaces a research-gap finding for them instead.
"""

from __future__ import annotations

from .manifest import MANIFEST_FILENAME, PROJECTION_VERSION, ProfileManifest
from .projection import ProfileProjector, default_profile_repository
from .renderers import (
    ClaudeCodeProfileRenderer,
    CopilotProfileRenderer,
    ProfileRenderer,
    get_renderer,
    native_name_violation,
)

__all__ = [
    "MANIFEST_FILENAME",
    "PROJECTION_VERSION",
    "ClaudeCodeProfileRenderer",
    "CopilotProfileRenderer",
    "ProfileManifest",
    "ProfileProjector",
    "ProfileRenderer",
    "default_profile_repository",
    "get_renderer",
    "native_name_violation",
]

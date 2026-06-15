"""Native agent profile projection for the tool surface contract.

This subpackage projects Spec Kitty agent profiles (resolved by
:class:`charter.profiles.AgentProfileRepository`) into
host-native agent/subagent files (e.g. ``.claude/agents/<id>.md``,
``.github/agents/<id>.agent.md``) and tracks the projected files in a manifest
at ``.kittify/agent_profiles_manifest.json``.

The projection layer sits *on top of* the profile loading/scoring model: it
never mutates :class:`AgentProfileRepository` or the profile resolution graph,
it only reads resolved profiles and renders them to disk. Tools that have no
native named-agent primitive yield no projected profiles -- the provider
surfaces a research-gap finding for them instead.
"""

from __future__ import annotations

from .amazon_q_renderer import AmazonQProfileRenderer, FORMAT_AMAZON_Q_AGENT
from .augment_renderer import AugmentProfileRenderer, FORMAT_AUGMENT_AGENT
from .capability_matrix import HARNESS_CAPABILITY_MATRIX, HarnessCapabilityRecord
from .codex_renderer import CodexProfileRenderer, FORMAT_CODEX_AGENT
from .manifest import MANIFEST_FILENAME, PROJECTION_VERSION, ProfileManifest
from .projection import ProfileProjector, default_profile_repository
from .renderers import (
    ClaudeCodeProfileRenderer,
    CopilotProfileRenderer,
    FORMAT_CLAUDE_AGENT,
    FORMAT_COPILOT_AGENT,
    ProfileRenderer,
    get_renderer,
    native_name_violation,
)

__all__ = [
    "FORMAT_AMAZON_Q_AGENT",
    "FORMAT_AUGMENT_AGENT",
    "FORMAT_CLAUDE_AGENT",
    "FORMAT_CODEX_AGENT",
    "FORMAT_COPILOT_AGENT",
    "HARNESS_CAPABILITY_MATRIX",
    "HarnessCapabilityRecord",
    "MANIFEST_FILENAME",
    "PROJECTION_VERSION",
    "AmazonQProfileRenderer",
    "AugmentProfileRenderer",
    "ClaudeCodeProfileRenderer",
    "CodexProfileRenderer",
    "CopilotProfileRenderer",
    "ProfileManifest",
    "ProfileProjector",
    "ProfileRenderer",
    "default_profile_repository",
    "get_renderer",
    "native_name_violation",
]

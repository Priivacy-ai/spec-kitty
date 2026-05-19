"""Charter facade for agent profile types.

This module is the charter-layer proxy for runtime callers that historically
imported from ``doctrine.agent_profiles`` directly. The runtime → charter →
doctrine boundary (ADR 2026-03-27-1, tightened by mission
``charter-mediated-doctrine-selection-01KRTZCA``) requires runtime modules
under ``src/specify_cli/`` to reach doctrine artifacts only through such
charter facades.

This file is a **pure re-export** module — no behaviour, no wrappers, no
type aliases. Identity is preserved (``charter.profiles.AgentProfile is
doctrine.agent_profiles.profile.AgentProfile``).
"""

from doctrine.agent_profiles.capabilities import DEFAULT_ROLE_CAPABILITIES
from doctrine.agent_profiles.profile import AgentProfile, Role
from doctrine.agent_profiles.repository import AgentProfileRepository

__all__ = [
    "AgentProfile",
    "AgentProfileRepository",
    "DEFAULT_ROLE_CAPABILITIES",
    "Role",
]

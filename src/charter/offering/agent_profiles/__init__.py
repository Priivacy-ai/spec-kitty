"""
Agent profiles domain model - public API.

This package provides the AgentProfile domain entity and related value objects
for defining agent behavioral identities in spec-kitty.
"""

from charter.offering.agent_profiles.capabilities import DEFAULT_ROLE_CAPABILITIES, RoleCapabilities, get_capabilities
from charter.offering.agent_profiles.diagnostics import SkippedProfile
from charter.offering.agent_profiles.profile import (
    AgentProfile,
    CollaborationContract,
    ContextSources,
    DirectiveRef,
    ModeDefault,
    Role,
    Specialization,
    SpecializationContext,
    TaskContext,
)
from charter.offering.agent_profiles.repository import AgentProfileRepository

__all__ = [
    # Main domain model
    "AgentProfile",
    "Role",
    # Value objects
    "Specialization",
    "CollaborationContract",
    "SpecializationContext",
    "ContextSources",
    "ModeDefault",
    "DirectiveRef",
    # Task context
    "TaskContext",
    # Capabilities
    "RoleCapabilities",
    "DEFAULT_ROLE_CAPABILITIES",
    "get_capabilities",
    # Repository
    "AgentProfileRepository",
    # Diagnostics
    "SkippedProfile",
]

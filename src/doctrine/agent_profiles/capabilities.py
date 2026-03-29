"""
RoleCapabilities mapping - defines default capabilities and canonical verbs per role.
"""

from dataclasses import dataclass

from doctrine.agent_profiles.profile import Role


@dataclass(frozen=True)
class RoleCapabilities:
    """Capabilities and canonical verbs for an agent role."""

    role: Role | str
    default_capabilities: list[str]
    canonical_verbs: list[str]
    description: str = ""


# Default capabilities per role
DEFAULT_ROLE_CAPABILITIES: dict[Role, RoleCapabilities] = {
    Role.IMPLEMENTER: RoleCapabilities(
        role=Role.IMPLEMENTER,
        default_capabilities=["read", "write", "edit", "bash", "search"],
        canonical_verbs=["generate", "refine", "implement"],
        description="Code implementation and feature development",
    ),
    Role.REVIEWER: RoleCapabilities(
        role=Role.REVIEWER,
        default_capabilities=["read", "search"],
        canonical_verbs=["audit", "assess", "review"],
        description="Code review and quality assurance",
    ),
    Role.ARCHITECT: RoleCapabilities(
        role=Role.ARCHITECT,
        default_capabilities=["read", "write", "search", "edit", "bash"],
        canonical_verbs=["audit", "synthesize", "plan"],
        description="System design and architectural decisions",
    ),
    Role.DESIGNER: RoleCapabilities(
        role=Role.DESIGNER,
        default_capabilities=["read", "write", "search"],
        canonical_verbs=["synthesize", "draft", "design"],
        description="UI/UX and interface design",
    ),
    Role.PLANNER: RoleCapabilities(
        role=Role.PLANNER,
        default_capabilities=["read", "write", "search"],
        canonical_verbs=["plan", "decompose", "prioritize"],
        description="Project planning and task decomposition",
    ),
    Role.RESEARCHER: RoleCapabilities(
        role=Role.RESEARCHER,
        default_capabilities=["read", "search"],
        canonical_verbs=["analyze", "investigate", "summarize"],
        description="Research and information gathering",
    ),
    Role.CURATOR: RoleCapabilities(
        role=Role.CURATOR,
        default_capabilities=["read", "write", "search"],
        canonical_verbs=["classify", "curate", "validate"],
        description="Content curation and organization",
    ),
    Role.MANAGER: RoleCapabilities(
        role=Role.MANAGER,
        default_capabilities=["read", "search"],
        canonical_verbs=["coordinate", "delegate", "monitor"],
        description="Project and team management",
    ),
}


def get_capabilities(role: Role | str) -> RoleCapabilities | None:
    """
    Get default capabilities for a role.

    Returns None for custom roles not in the controlled vocabulary.
    """
    if isinstance(role, Role):
        return DEFAULT_ROLE_CAPABILITIES.get(role)
    if isinstance(role, str):
        try:
            role_enum = Role(role.lower())
            return DEFAULT_ROLE_CAPABILITIES.get(role_enum)
        except ValueError:
            # Custom role - no default capabilities
            return None
    return None

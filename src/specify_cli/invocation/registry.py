"""ProfileRegistry: thin wrapper over AgentProfileRepository for invocation use."""

from __future__ import annotations

from pathlib import Path

from doctrine.agent_profiles.profile import AgentProfile
from doctrine.agent_profiles.repository import AgentProfileRepository

from specify_cli.invocation.errors import ProfileNotFoundError


class ProfileRegistry:
    """Thin wrapper over AgentProfileRepository with invocation-friendly API.

    When ``.kittify/profiles/`` does not exist, ``project_dir=None`` causes
    the repo to fall back to shipped profiles gracefully (no exception).
    If shipped profiles also produce an empty list, ``has_profiles()``
    returns False — the executor uses this to produce the
    "run charter synthesize" error message.
    """

    def __init__(self, repo_root: Path) -> None:
        project_profiles_dir = repo_root / ".kittify" / "profiles"
        self._repo = AgentProfileRepository(
            project_dir=project_profiles_dir if project_profiles_dir.exists() else None,
        )

    def list_all(self) -> list[AgentProfile]:
        """Return all loaded profiles sorted by profile_id."""
        return self._repo.list_all()

    def get(self, profile_id: str) -> AgentProfile | None:
        """Get profile by ID or None if not found."""
        return self._repo.get(profile_id)

    def resolve(self, profile_id: str) -> AgentProfile:
        """Get profile by ID, raising ProfileNotFoundError if not found."""
        profile = self._repo.get(profile_id)
        if profile is None:
            available = [p.profile_id for p in self._repo.list_all()]
            raise ProfileNotFoundError(profile_id, available)
        return profile

    def has_profiles(self) -> bool:
        """Return True if any profiles are available."""
        return len(self._repo.list_all()) > 0

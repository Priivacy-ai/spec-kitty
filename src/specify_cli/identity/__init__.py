"""Identity compatibility helpers — leaf package with no dependencies on core or status."""

from specify_cli.identity.aliases import with_tracked_mission_slug_aliases
from specify_cli.identity.project import ProjectIdentity as ProjectIdentity  # noqa: F401

__all__ = ["ProjectIdentity", "with_tracked_mission_slug_aliases"]

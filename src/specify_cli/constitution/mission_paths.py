"""Centralized project-local mission path resolution.

All ``.kittify/missions/`` path construction flows through this module
so that filesystem layout details do not leak into the rest of the
codebase.  Future work will make resolution constitution-aware.

Exports
-------
``MissionType``
    Half-open enum of mission types — predefined constants for built-in
    missions plus a ``with_name()`` factory for custom types.

``ProjectMissionPaths``
    Singleton that resolves every project-local mission path.  Initialize
    once (explicitly or lazily) and query paths without passing
    directories around.

Quick start
-----------
::

    from specify_cli.constitution.mission_paths import (
        MissionType,
        ProjectMissionPaths,
    )

    # Explicit init (CLI entry-point, test fixture):
    ProjectMissionPaths.init(repo_root)

    # Lazy init (discovers repo root from cwd):
    paths = ProjectMissionPaths.get()

    # Query:
    paths.missions_root()
    paths.command_templates_for(MissionType.SOFTWARE_DEV)
    paths.mission_dir_for(MissionType.with_name("my-custom"))

    # Callers that only have a kittify_dir (Path to .kittify/):
    paths = ProjectMissionPaths.from_kittify(kittify_dir)
    paths.mission_dir_for(MissionType.SOFTWARE_DEV)
"""

from __future__ import annotations

from pathlib import Path


# ── MissionType (half-open enum) ────────────────────────────────────

class MissionType:
    """Half-open enumeration of mission types.

    Predefined constants cover the built-in missions that ship with
    Spec Kitty.  Custom mission types are created via ``with_name()``.

    Predefined constants
    --------------------
    ``SOFTWARE_DEV``  — ``"software-dev"``
    ``RESEARCH``      — ``"research"``
    ``WRITING``       — ``"writing"``
    ``DOCUMENTATION`` — ``"documentation"``
    ``SEO``           — ``"seo"``

    Custom types
    ------------
    ::

        custom = MissionType.with_name("my-org-workflow")
    """

    # Forward-declared class attributes (assigned after the class body).
    SOFTWARE_DEV: MissionType
    RESEARCH: MissionType
    WRITING: MissionType
    DOCUMENTATION: MissionType
    SEO: MissionType

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        """Filesystem-safe mission key (e.g. ``"software-dev"``)."""
        return self._name

    @classmethod
    def with_name(cls, name: str) -> MissionType:
        """Create a ``MissionType`` from an arbitrary string name."""
        return cls(name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MissionType):
            return self._name == other._name
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._name)

    def __repr__(self) -> str:
        return f"MissionType({self._name!r})"


# Predefined mission types (set after class body to avoid forward-ref issues).
MissionType.SOFTWARE_DEV = MissionType("software-dev")
MissionType.RESEARCH = MissionType("research")
MissionType.WRITING = MissionType("writing")
MissionType.DOCUMENTATION = MissionType("documentation")
MissionType.SEO = MissionType("seo")


# ── ProjectMissionPaths (singleton) ─────────────────────────────────

class ProjectMissionPaths:
    """Singleton for centralized project-local mission path resolution.

    Encapsulates **all** ``.kittify/missions/`` path construction so that
    filesystem layout details do not leak into the rest of the codebase.

    Initialization
    --------------
    Explicit — use at CLI entry-points or in test fixtures::

        ProjectMissionPaths.init(repo_root)

    Lazy — auto-discovers the repo root by walking up from ``cwd``::

        paths = ProjectMissionPaths.get()

    From a ``.kittify/`` directory (for callers that already hold one)::

        paths = ProjectMissionPaths.from_kittify(kittify_dir)

    Path queries
    ------------
    ::

        paths.missions_root()
        paths.mission_dir_for(MissionType.SOFTWARE_DEV)
        paths.mission_config_for(MissionType.with_name("research"))
        paths.command_templates_for(MissionType.SOFTWARE_DEV)
        paths.templates_for(MissionType.DOCUMENTATION)

    Testing
    -------
    ::

        ProjectMissionPaths.init(tmp_path)
        # …assertions…
        ProjectMissionPaths.reset()  # clean up singleton state
    """

    _instance: ProjectMissionPaths | None = None

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    # ── Lifecycle ────────────────────────────────────────────────────

    @classmethod
    def init(cls, repo_root: Path) -> ProjectMissionPaths:
        """Set the singleton to an explicit repo root and return it."""
        cls._instance = cls(repo_root)
        return cls._instance

    @classmethod
    def get(cls) -> ProjectMissionPaths:
        """Return the singleton, lazily initializing from ``cwd`` if needed."""
        if cls._instance is None:
            cls._instance = cls(cls._discover_repo_root())
        return cls._instance

    @classmethod
    def from_kittify(cls, kittify_dir: Path) -> ProjectMissionPaths:
        """Construct an instance from a ``.kittify/`` directory.

        This does **not** replace the singleton — it returns a
        stand-alone instance that is useful for callers that already
        hold a ``kittify_dir`` reference (e.g. functions whose public
        API accepts ``kittify_dir: Path``).
        """
        return cls(kittify_dir.parent)

    @classmethod
    def reset(cls) -> None:
        """Clear the singleton.  Intended for test teardown."""
        cls._instance = None

    # ── Path resolution ──────────────────────────────────────────────

    def missions_root(self) -> Path:
        """Root directory for all project-local missions."""
        return self._repo_root / ".kittify" / "missions"

    def mission_dir_for(self, mission: MissionType) -> Path:
        """Directory for a specific mission."""
        return self.missions_root() / mission.name

    def mission_config_for(self, mission: MissionType) -> Path:
        """Path to a mission's ``mission.yaml``."""
        return self.mission_dir_for(mission) / "mission.yaml"

    def command_templates_for(self, mission: MissionType) -> Path:
        """Directory containing command templates for a mission."""
        return self.mission_dir_for(mission) / "command-templates"

    def templates_for(self, mission: MissionType) -> Path:
        """Directory containing content templates for a mission."""
        return self.mission_dir_for(mission) / "templates"

    # ── Internals ────────────────────────────────────────────────────

    @staticmethod
    def _discover_repo_root() -> Path:
        """Walk up from ``cwd`` to find a directory containing ``.kittify/``."""
        current = Path.cwd().resolve()
        while True:
            if (current / ".kittify").is_dir():
                return current
            parent = current.parent
            if parent == current:
                raise RuntimeError(
                    "Could not find .kittify/ in any parent of "
                    f"{Path.cwd()}.  Is this a Spec Kitty project?"
                )
            current = parent

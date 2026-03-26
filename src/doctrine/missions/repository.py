"""Mission repository for path-based access to mission assets."""

from __future__ import annotations

from pathlib import Path


class MissionRepository:
    """Repository for locating mission asset files on the filesystem.

    Provides path-based lookup for command templates, content templates,
    action indexes, action guidelines, and mission configs.  All query
    methods return ``None`` (rather than raising) when the requested file
    does not exist, so callers can implement their own fallback logic.
    """

    def __init__(self, missions_root: Path) -> None:
        self._root = missions_root

    # ------------------------------------------------------------------
    # Class-level constructor helpers
    # ------------------------------------------------------------------

    @classmethod
    def default_missions_root(cls) -> Path:
        """Return the missions root bundled with the ``doctrine`` package.

        Uses ``importlib.resources`` so that the path is valid both when
        running from an editable install and from a built wheel.
        """
        try:
            from importlib.resources import files

            resource = files("doctrine") / "missions"
            return Path(str(resource))
        except Exception:
            return Path(__file__).parent

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------

    def list_missions(self) -> list[str]:
        """Return the names of all missions that contain a ``mission.yaml``.

        Returns:
            Sorted list of mission directory names.
        """
        if not self._root.is_dir():
            return []
        return sorted(
            d.name
            for d in self._root.iterdir()
            if d.is_dir() and (d / "mission.yaml").exists()
        )

    def get_command_template(self, mission: str, command: str) -> Path | None:
        """Return the path to a command template Markdown file.

        Looks for ``<missions_root>/<mission>/command-templates/<command>.md``.

        Args:
            mission: Mission name (e.g. ``"software-dev"``).
            command: Command/template name without extension (e.g. ``"implement"``).

        Returns:
            Path if the file exists, else ``None``.
        """
        path = self._root / mission / "command-templates" / f"{command}.md"
        return path if path.is_file() else None

    def get_template(self, mission: str, template: str) -> Path | None:
        """Return the path to a content template file.

        Looks for ``<missions_root>/<mission>/templates/<template>``.

        Args:
            mission: Mission name.
            template: Template filename including extension (e.g. ``"spec-template.md"``).

        Returns:
            Path if the file exists, else ``None``.
        """
        path = self._root / mission / "templates" / template
        return path if path.is_file() else None

    def get_action_index_path(self, mission: str, action: str) -> Path | None:
        """Return the path to an action's ``index.yaml``.

        Looks for ``<missions_root>/<mission>/actions/<action>/index.yaml``.

        Args:
            mission: Mission name.
            action: Action name (e.g. ``"implement"``).

        Returns:
            Path if the file exists, else ``None``.
        """
        path = self._root / mission / "actions" / action / "index.yaml"
        return path if path.is_file() else None

    def get_action_guidelines_path(self, mission: str, action: str) -> Path | None:
        """Return the path to an action's ``guidelines.md``.

        Looks for ``<missions_root>/<mission>/actions/<action>/guidelines.md``.

        Args:
            mission: Mission name.
            action: Action name.

        Returns:
            Path if the file exists, else ``None``.
        """
        path = self._root / mission / "actions" / action / "guidelines.md"
        return path if path.is_file() else None

    def get_mission_config_path(self, mission: str) -> Path | None:
        """Return the path to a mission's ``mission.yaml``.

        Args:
            mission: Mission name.

        Returns:
            Path if the file exists, else ``None``.
        """
        path = self._root / mission / "mission.yaml"
        return path if path.is_file() else None

    def get_expected_artifacts(self, mission: str) -> Path | None:
        """Return the path to a mission's ``expected-artifacts.yaml``.

        The expected-artifacts manifest defines step-aware, class-tagged,
        blocking-semantics artifact requirements used by the dossier
        ``ManifestRegistry``.

        Args:
            mission: Mission name (e.g. ``"software-dev"``).

        Returns:
            Path if the file exists, else ``None``.
        """
        path = self._root / mission / "expected-artifacts.yaml"
        return path if path.is_file() else None

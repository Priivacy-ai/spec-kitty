"""Mission template repository for content-based access to mission assets."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class TemplateResult:
    """Value object wrapping template content with origin metadata.

    Constructed internally by MissionTemplateRepository.
    Consumers should not instantiate directly.
    """

    __slots__ = ("_data",)

    def __init__(self, content: str, origin: str, tier: Any = None) -> None:
        self._data: dict[str, Any] = {
            "content": content,
            "origin": origin,
            "tier": tier,
        }

    @property
    def content(self) -> str:
        """Raw template text (UTF-8)."""
        return self._data["content"]

    @property
    def origin(self) -> str:
        """Human-readable origin label (e.g. 'doctrine/software-dev/command-templates/implement.md')."""
        return self._data["origin"]

    @property
    def tier(self) -> Any:
        """Resolution tier (ResolutionTier enum or None for doctrine-level lookups)."""
        return self._data["tier"]

    def __repr__(self) -> str:
        return f"TemplateResult(origin={self.origin!r}, tier={self.tier})"


class ConfigResult:
    """Value object wrapping parsed YAML config with origin metadata.

    Constructed internally by MissionTemplateRepository.
    Consumers should not instantiate directly.
    """

    __slots__ = ("_data",)

    def __init__(self, content: str, origin: str, parsed: dict | list) -> None:
        self._data: dict[str, Any] = {
            "content": content,
            "origin": origin,
            "parsed": parsed,
        }

    @property
    def content(self) -> str:
        """Raw YAML text (UTF-8)."""
        return self._data["content"]

    @property
    def origin(self) -> str:
        """Human-readable origin label (e.g. 'doctrine/software-dev/mission.yaml')."""
        return self._data["origin"]

    @property
    def parsed(self) -> dict | list:
        """Pre-parsed YAML data (parsed with ruamel.yaml YAML(typ='safe'))."""
        return self._data["parsed"]

    def __repr__(self) -> str:
        return f"ConfigResult(origin={self.origin!r})"


class MissionTemplateRepository:
    """Single authority for mission asset access.

    Provides content-returning public methods (via TemplateResult and
    ConfigResult value objects) and private _*_path() methods for
    internal callers that need filesystem access.  All query methods
    return None (rather than raising) when the requested asset does
    not exist, so callers can implement their own fallback logic.
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

    @classmethod
    def default(cls) -> MissionTemplateRepository:
        """Return a repository instance for the doctrine-bundled missions."""
        return cls(cls.default_missions_root())

    # ------------------------------------------------------------------
    # Enumeration interface
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

    # ------------------------------------------------------------------
    # Private path methods (internal use only)
    # ------------------------------------------------------------------

    @property
    def _missions_root(self) -> Path:
        """Return the missions root directory (internal use only)."""
        return self._root

    def _command_template_path(self, mission: str, name: str) -> Path | None:
        """Return the path to a command template Markdown file.

        Looks for ``<missions_root>/<mission>/command-templates/<name>.md``.

        Args:
            mission: Mission name (e.g. ``"software-dev"``).
            name: Template name without extension (e.g. ``"implement"``).

        Returns:
            Path if the file exists, else ``None``.
        """
        path = self._root / mission / "command-templates" / f"{name}.md"
        return path if path.is_file() else None

    def _content_template_path(self, mission: str, name: str) -> Path | None:
        """Return the path to a content template file.

        Looks for ``<missions_root>/<mission>/templates/<name>``.

        Args:
            mission: Mission name.
            name: Template filename including extension (e.g. ``"spec-template.md"``).

        Returns:
            Path if the file exists, else ``None``.
        """
        path = self._root / mission / "templates" / name
        return path if path.is_file() else None

    def _action_index_path(self, mission: str, action: str) -> Path | None:
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

    def _action_guidelines_path(self, mission: str, action: str) -> Path | None:
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

    def _mission_config_path(self, mission: str) -> Path | None:
        """Return the path to a mission's ``mission.yaml``.

        Args:
            mission: Mission name.

        Returns:
            Path if the file exists, else ``None``.
        """
        path = self._root / mission / "mission.yaml"
        return path if path.is_file() else None

    def _expected_artifacts_path(self, mission: str) -> Path | None:
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

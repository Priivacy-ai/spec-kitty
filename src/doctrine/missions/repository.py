"""Mission template repository for content-based access to mission assets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

ParsedConfig = dict[str, Any] | list[Any]


class TemplateResult:
    """Value object wrapping template content with origin metadata.

    Constructed internally by MissionTemplateRepository.
    Consumers should not instantiate directly.
    """

    __slots__ = ("_content", "_origin", "_tier")

    def __init__(self, content: str, origin: str, tier: Any = None) -> None:
        self._content = content
        self._origin = origin
        self._tier = tier

    @property
    def content(self) -> str:
        """Raw template text (UTF-8)."""
        return self._content

    @property
    def origin(self) -> str:
        """Human-readable origin label (e.g. 'doctrine/software-dev/command-templates/implement.md')."""
        return self._origin

    @property
    def tier(self) -> Any:
        """Resolution tier (ResolutionTier enum or None for doctrine-level lookups)."""
        return self._tier

    def __repr__(self) -> str:
        return f"TemplateResult(origin={self.origin!r}, tier={self.tier})"


class ConfigResult:
    """Value object wrapping parsed YAML config with origin metadata.

    Constructed internally by MissionTemplateRepository.
    Consumers should not instantiate directly.
    """

    __slots__ = ("_content", "_origin", "_parsed")

    def __init__(self, content: str, origin: str, parsed: ParsedConfig) -> None:
        self._content = content
        self._origin = origin
        self._parsed = parsed

    @property
    def content(self) -> str:
        """Raw YAML text (UTF-8)."""
        return self._content

    @property
    def origin(self) -> str:
        """Human-readable origin label (e.g. 'doctrine/software-dev/mission.yaml')."""
        return self._origin

    @property
    def parsed(self) -> ParsedConfig:
        """Pre-parsed YAML data (parsed with ruamel.yaml YAML(typ='safe'))."""
        return self._parsed

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
        except (ModuleNotFoundError, TypeError):
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
        return sorted(d.name for d in self._root.iterdir() if d.is_dir() and (d / "mission.yaml").exists())

    # ------------------------------------------------------------------
    # Public content-returning methods
    # ------------------------------------------------------------------

    def get_command_template(self, mission: str, name: str) -> TemplateResult | None:
        """Read a command template's content from doctrine assets.

        Looks for ``<missions_root>/<mission>/command-templates/<name>.md``.

        Args:
            mission: Mission name (e.g. ``"software-dev"``).
            name: Template name without ``.md`` extension (e.g. ``"implement"``).

        Returns:
            TemplateResult with content and origin, or ``None`` if not found.
        """
        path = self._command_template_path(mission, name)
        if path is None:
            return None
        try:
            content = path.read_text(encoding="utf-8")
            origin = f"doctrine/{mission}/command-templates/{name}.md"
            return TemplateResult(content=content, origin=origin)
        except (OSError, UnicodeDecodeError):
            return None

    def get_content_template(self, mission: str, name: str) -> TemplateResult | None:
        """Read a content template's content from doctrine assets.

        Looks for ``<missions_root>/<mission>/templates/<name>``.

        Args:
            mission: Mission name.
            name: Template filename with extension (e.g. ``"spec-template.md"``).

        Returns:
            TemplateResult with content and origin, or ``None`` if not found.
        """
        path = self._content_template_path(mission, name)
        if path is None:
            return None
        try:
            content = path.read_text(encoding="utf-8")
            origin = f"doctrine/{mission}/templates/{name}"
            return TemplateResult(content=content, origin=origin)
        except (OSError, UnicodeDecodeError):
            return None

    def list_command_templates(self, mission: str) -> list[str]:
        """Return names of all command templates for a mission.

        Args:
            mission: Mission name (e.g. ``"software-dev"``).

        Returns:
            Sorted list of template names WITHOUT ``.md`` extension
            (e.g. ``["implement", "plan", "specify", "tasks"]``).
            Empty list if mission or command-templates dir doesn't exist.
        """
        cmd_dir = self._root / mission / "command-templates"
        if not cmd_dir.is_dir():
            return []
        return sorted(p.stem for p in cmd_dir.iterdir() if p.is_file() and p.suffix == ".md" and p.name != "README.md")

    def list_content_templates(self, mission: str) -> list[str]:
        """Return filenames of all content templates for a mission.

        Args:
            mission: Mission name.

        Returns:
            Sorted list of template filenames WITH extension
            (e.g. ``["plan-template.md", "spec-template.md"]``).
            Empty list if mission or templates dir doesn't exist.
        """
        tpl_dir = self._root / mission / "templates"
        if not tpl_dir.is_dir():
            return []
        return sorted(p.name for p in tpl_dir.iterdir() if p.is_file() and p.name != "README.md")

    # ------------------------------------------------------------------
    # Public config-returning methods
    # ------------------------------------------------------------------

    def get_action_index(self, mission: str, action: str) -> ConfigResult | None:
        """Read and parse an action's index.yaml from doctrine assets.

        Args:
            mission: Mission name.
            action: Action name (e.g. ``"implement"``).

        Returns:
            ConfigResult with raw YAML text and parsed dict, or ``None`` if not found.
        """
        path = self._action_index_path(mission, action)
        if path is None:
            return None
        try:
            content = path.read_text(encoding="utf-8")
            yaml = YAML(typ="safe")
            parsed = cast(ParsedConfig | None, yaml.load(content))
            if parsed is None:
                return None
            origin = f"doctrine/{mission}/actions/{action}/index.yaml"
            return ConfigResult(content=content, origin=origin, parsed=parsed)
        except (OSError, UnicodeDecodeError, YAMLError):
            return None

    def get_action_guidelines(self, mission: str, action: str) -> TemplateResult | None:
        """Read an action's guidelines.md from doctrine assets.

        Args:
            mission: Mission name.
            action: Action name.

        Returns:
            TemplateResult with content and origin, or ``None`` if not found.
        """
        path = self._action_guidelines_path(mission, action)
        if path is None:
            return None
        try:
            content = path.read_text(encoding="utf-8")
            origin = f"doctrine/{mission}/actions/{action}/guidelines.md"
            return TemplateResult(content=content, origin=origin)
        except (OSError, UnicodeDecodeError):
            return None

    def get_mission_config(self, mission: str) -> ConfigResult | None:
        """Read and parse a mission's mission.yaml from doctrine assets.

        Args:
            mission: Mission name.

        Returns:
            ConfigResult with raw YAML text and parsed dict, or ``None`` if not found.
        """
        path = self._mission_config_path(mission)
        if path is None:
            return None
        try:
            content = path.read_text(encoding="utf-8")
            yaml = YAML(typ="safe")
            parsed = cast(ParsedConfig | None, yaml.load(content))
            if parsed is None:
                return None
            origin = f"doctrine/{mission}/mission.yaml"
            return ConfigResult(content=content, origin=origin, parsed=parsed)
        except (OSError, UnicodeDecodeError, YAMLError):
            return None

    def get_expected_artifacts(self, mission: str) -> ConfigResult | None:
        """Read and parse a mission's expected-artifacts.yaml.

        Args:
            mission: Mission name (e.g. ``"software-dev"``).

        Returns:
            ConfigResult with raw YAML text and parsed data, or ``None`` if not found.
        """
        path = self._expected_artifacts_path(mission)
        if path is None:
            return None
        try:
            content = path.read_text(encoding="utf-8")
            yaml = YAML(typ="safe")
            parsed = cast(ParsedConfig | None, yaml.load(content))
            if parsed is None:
                return None
            origin = f"doctrine/{mission}/expected-artifacts.yaml"
            return ConfigResult(content=content, origin=origin, parsed=parsed)
        except (OSError, UnicodeDecodeError, YAMLError):
            return None

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


# Backward-compat alias so ``from doctrine.missions.repository import MissionRepository``
# works the same as ``from doctrine.missions import MissionRepository``.
MissionRepository = MissionTemplateRepository

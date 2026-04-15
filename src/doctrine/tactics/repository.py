"""
Tactic repository with two-source loading (shipped + project).

Provides:
- Two-source YAML loading (shipped package data + project filesystem)
- Field-level merge semantics for project overrides
- Query methods (list_all, get)
- Save for project tactics
"""

from pathlib import Path
from typing import Any

from importlib.resources import files
from ruamel.yaml import YAML

from doctrine.base import BaseDoctrineRepository
from .models import Tactic
from .validation import reject_tactic_inline_refs


class TacticRepository(BaseDoctrineRepository[Tactic]):
    """Repository for loading and managing tactic YAML files."""

    def __init__(
        self,
        shipped_dir: Path | None = None,
        project_dir: Path | None = None,
        active_languages: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(
            shipped_dir=shipped_dir or self._default_shipped_dir(),
            project_dir=project_dir,
            active_languages=active_languages,
        )

    @staticmethod
    def _default_shipped_dir() -> Path:
        """Get default shipped tactics directory from package data."""
        try:
            resource = files("doctrine.tactics")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "shipped"

    @property
    def _schema(self) -> type[Tactic]:
        return Tactic

    @property
    def _glob(self) -> str:
        return "*.tactic.yaml"

    def _pre_validate(self, data: dict[str, Any], yaml_file: Path) -> None:
        reject_tactic_inline_refs(data, file_path=str(yaml_file))

    def save(self, tactic: Tactic) -> Path:
        """Save tactic to project directory.

        Returns:
            Path to the written YAML file.

        Raises:
            ValueError: If project_dir is not configured.
        """
        if self._project_dir is None:
            raise ValueError("Cannot save tactic: project_dir not configured")

        self._project_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{tactic.id}.tactic.yaml"
        yaml = YAML()
        yaml.default_flow_style = False
        yaml_file = self._project_dir / filename

        data = tactic.model_dump(mode="json", exclude_none=True)

        with yaml_file.open("w") as f:
            yaml.dump(data, f)

        self._items[tactic.id] = tactic
        return yaml_file

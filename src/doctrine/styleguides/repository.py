"""
Styleguide repository with two-source loading (shipped + project).

Provides:
- Two-source YAML loading (shipped package data + project filesystem)
- Recursive scan to handle subdirectory structure (e.g. writing/)
- Field-level merge semantics for project overrides
- Query methods (list_all, get)
- Save for project styleguides
"""

import re
from pathlib import Path
from typing import Any

from importlib.resources import files
from ruamel.yaml import YAML

from doctrine.base import BaseDoctrineRepository
from .models import Styleguide
from .validation import reject_styleguide_inline_refs


class StyleguideRepository(BaseDoctrineRepository[Styleguide]):
    """Repository for loading and managing styleguide YAML files."""

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
        """Get default shipped styleguides directory from package data."""
        try:
            resource = files("doctrine.styleguides")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "shipped"

    @property
    def _schema(self) -> type[Styleguide]:
        return Styleguide

    @property
    def _glob(self) -> str:
        return "*.styleguide.yaml"

    def _pre_validate(self, data: dict[str, Any], yaml_file: Path) -> None:
        reject_styleguide_inline_refs(data, file_path=str(yaml_file))

    def _project_scan(self, project_dir: Path) -> list[Path]:
        """Recursive scan — styleguides may live in subdirectories."""
        return sorted(project_dir.rglob(self._glob))

    def save(self, styleguide: Styleguide) -> Path:
        """Save styleguide to project directory.

        Returns:
            Path to the written YAML file.

        Raises:
            ValueError: If project_dir is not configured.
        """
        if self._project_dir is None:
            raise ValueError("Cannot save styleguide: project_dir not configured")

        self._project_dir.mkdir(parents=True, exist_ok=True)

        slug = re.sub(r"[^a-z0-9-]", "", styleguide.id)
        filename = f"{slug}.styleguide.yaml"
        yaml = YAML()
        yaml.default_flow_style = False
        yaml_file = self._project_dir / filename

        data = styleguide.model_dump(mode="json", exclude_none=True)

        with yaml_file.open("w") as f:
            yaml.dump(data, f)

        self._items[styleguide.id] = styleguide
        return yaml_file

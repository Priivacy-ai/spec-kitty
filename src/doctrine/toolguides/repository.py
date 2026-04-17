"""
Toolguide repository with two-source loading (shipped + project).
"""

import re
from pathlib import Path
from typing import Any

from importlib.resources import files
from ruamel.yaml import YAML

from doctrine.base import BaseDoctrineRepository
from .models import Toolguide
from .validation import reject_toolguide_inline_refs


class ToolguideRepository(BaseDoctrineRepository[Toolguide]):
    """Repository for loading and managing toolguide YAML files."""

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
        try:
            resource = files("doctrine.toolguides")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "shipped"

    @property
    def _schema(self) -> type[Toolguide]:
        return Toolguide

    @property
    def _glob(self) -> str:
        return "*.toolguide.yaml"

    def _pre_validate(self, data: dict[str, Any], yaml_file: Path) -> None:
        reject_toolguide_inline_refs(data, file_path=str(yaml_file))

    def save(self, toolguide: Toolguide) -> Path:
        if self._project_dir is None:
            raise ValueError("Cannot save toolguide: project_dir not configured")

        self._project_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9-]", "", toolguide.id)
        filename = f"{slug}.toolguide.yaml"
        yaml = YAML()
        yaml.default_flow_style = False
        yaml_file = self._project_dir / filename
        data = toolguide.model_dump(mode="json", exclude_none=True)
        with yaml_file.open("w") as f:
            yaml.dump(data, f)
        self._items[toolguide.id] = toolguide
        return yaml_file

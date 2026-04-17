"""
Paradigm repository with two-source loading (shipped + project).
"""

from pathlib import Path
from typing import Any

from importlib.resources import files
from ruamel.yaml import YAML

from doctrine.base import BaseDoctrineRepository
from .models import Paradigm
from .validation import reject_paradigm_inline_refs


class ParadigmRepository(BaseDoctrineRepository[Paradigm]):
    """Repository for loading and managing paradigm YAML files."""

    def __init__(
        self,
        shipped_dir: Path | None = None,
        project_dir: Path | None = None,
    ) -> None:
        super().__init__(
            shipped_dir=shipped_dir or self._default_shipped_dir(),
            project_dir=project_dir,
        )

    @staticmethod
    def _default_shipped_dir() -> Path:
        """Get default shipped paradigms directory from package data."""
        try:
            resource = files("doctrine.paradigms")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "shipped"

    @property
    def _schema(self) -> type[Paradigm]:
        return Paradigm

    @property
    def _glob(self) -> str:
        return "*.paradigm.yaml"

    def _pre_validate(self, data: dict[str, Any], yaml_file: Path) -> None:
        reject_paradigm_inline_refs(data, file_path=str(yaml_file))

    def save(self, paradigm: Paradigm) -> Path:
        """Save paradigm to project directory."""
        if self._project_dir is None:
            raise ValueError("Cannot save paradigm: project_dir not configured")

        self._project_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{paradigm.id}.paradigm.yaml"
        yaml = YAML()
        yaml.default_flow_style = False
        yaml_file = self._project_dir / filename

        data = paradigm.model_dump(mode="json", exclude_none=True)
        with yaml_file.open("w") as f:
            yaml.dump(data, f)

        self._items[paradigm.id] = paradigm
        return yaml_file

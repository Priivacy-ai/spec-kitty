"""
Toolguide repository with two-source loading (shipped + project).
"""

import re
import warnings
from pathlib import Path
from typing import Any

from importlib.resources import files
from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .models import Toolguide


class ToolguideRepository:
    """Repository for loading and managing toolguide YAML files."""

    def __init__(
        self,
        shipped_dir: Path | None = None,
        project_dir: Path | None = None,
    ) -> None:
        self._toolguides: dict[str, Toolguide] = {}
        self._shipped_dir = shipped_dir or self._default_shipped_dir()
        self._project_dir = project_dir
        self._load()

    @staticmethod
    def _default_shipped_dir() -> Path:
        try:
            resource = files("doctrine.toolguides")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "shipped"

    def _load(self) -> None:
        yaml = YAML(typ="safe")
        shipped: dict[str, Toolguide] = {}

        if self._shipped_dir.exists():
            for yaml_file in sorted(self._shipped_dir.glob("*.toolguide.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    toolguide = Toolguide.model_validate(data)
                    shipped[toolguide.id] = toolguide
                except (YAMLError, ValidationError, OSError) as e:
                    warnings.warn(
                        f"Skipping invalid shipped toolguide {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

        self._toolguides = shipped.copy()

        if self._project_dir and self._project_dir.exists():
            for yaml_file in sorted(self._project_dir.glob("*.toolguide.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    tg_id = data.get("id")
                    if not tg_id:
                        warnings.warn(
                            f"Skipping project toolguide {yaml_file.name}: no id",
                            UserWarning,
                            stacklevel=2,
                        )
                        continue

                    if tg_id in shipped:
                        merged = self._merge(shipped[tg_id], data)
                        self._toolguides[tg_id] = merged
                    else:
                        toolguide = Toolguide.model_validate(data)
                        self._toolguides[toolguide.id] = toolguide
                except (YAMLError, ValidationError, OSError) as e:
                    warnings.warn(
                        f"Skipping invalid project toolguide {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

    @staticmethod
    def _merge(shipped: Toolguide, project_data: dict[str, Any]) -> Toolguide:
        shipped_dict = shipped.model_dump()
        merged = {**shipped_dict, **project_data}
        return Toolguide.model_validate(merged)

    def list_all(self) -> list[Toolguide]:
        return sorted(self._toolguides.values(), key=lambda t: t.id)

    def get(self, toolguide_id: str) -> Toolguide | None:
        return self._toolguides.get(toolguide_id)

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
        self._toolguides[toolguide.id] = toolguide
        return yaml_file

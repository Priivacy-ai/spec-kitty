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
import warnings
from pathlib import Path
from typing import Any

from importlib.resources import files
from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from doctrine.shared.scoping import applies_to_languages_match, normalize_languages

from .models import Styleguide
from .validation import reject_styleguide_inline_refs


class StyleguideRepository:
    """Repository for loading and managing styleguide YAML files."""

    def __init__(
        self,
        shipped_dir: Path | None = None,
        project_dir: Path | None = None,
        active_languages: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self._styleguides: dict[str, Styleguide] = {}
        self._shipped_dir = shipped_dir or self._default_shipped_dir()
        self._project_dir = project_dir
        self._active_languages = None if active_languages is None else normalize_languages(active_languages)
        self._load()

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

    def _load(self) -> None:
        """Load styleguides from shipped and project directories."""
        yaml = YAML(typ="safe")
        shipped: dict[str, Styleguide] = {}

        if self._shipped_dir.exists():
            for yaml_file in sorted(self._shipped_dir.rglob("*.styleguide.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    reject_styleguide_inline_refs(data, file_path=str(yaml_file))
                    styleguide = Styleguide.model_validate(data)
                    if not applies_to_languages_match(styleguide.applies_to_languages, self._active_languages):
                        continue
                    shipped[styleguide.id] = styleguide
                except (YAMLError, ValidationError, OSError) as e:
                    warnings.warn(
                        f"Skipping invalid shipped styleguide {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

        self._styleguides = shipped.copy()

        if self._project_dir and self._project_dir.exists():
            for yaml_file in sorted(self._project_dir.rglob("*.styleguide.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    reject_styleguide_inline_refs(data, file_path=str(yaml_file))
                    styleguide_id = data.get("id")
                    if not styleguide_id:
                        warnings.warn(
                            f"Skipping project styleguide {yaml_file.name}: no id",
                            UserWarning,
                            stacklevel=2,
                        )
                        continue

                    if styleguide_id in shipped:
                        merged = self._merge_styleguides(
                            shipped[styleguide_id], data
                        )
                        if not applies_to_languages_match(merged.applies_to_languages, self._active_languages):
                            continue
                        self._styleguides[styleguide_id] = merged
                    else:
                        styleguide = Styleguide.model_validate(data)
                        if not applies_to_languages_match(styleguide.applies_to_languages, self._active_languages):
                            continue
                        self._styleguides[styleguide.id] = styleguide
                except (YAMLError, ValidationError, OSError) as e:
                    warnings.warn(
                        f"Skipping invalid project styleguide {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

    @staticmethod
    def _merge_styleguides(
        shipped: Styleguide, project_data: dict[str, Any]
    ) -> Styleguide:
        """Merge project data into shipped styleguide at field level."""
        shipped_dict = shipped.model_dump()
        merged = {**shipped_dict, **project_data}
        return Styleguide.model_validate(merged)

    def list_all(self) -> list[Styleguide]:
        """Return all loaded styleguides sorted by ID."""
        return sorted(self._styleguides.values(), key=lambda s: s.id)

    def get(self, styleguide_id: str) -> Styleguide | None:
        """Get styleguide by ID (kebab-case)."""
        return self._styleguides.get(styleguide_id)

    def save(self, styleguide: Styleguide) -> Path:
        """Save styleguide to project directory.

        Returns:
            Path to the written YAML file.

        Raises:
            ValueError: If project_dir is not configured.
        """
        if self._project_dir is None:
            raise ValueError(
                "Cannot save styleguide: project_dir not configured"
            )

        self._project_dir.mkdir(parents=True, exist_ok=True)

        slug = re.sub(r"[^a-z0-9-]", "", styleguide.id)
        filename = f"{slug}.styleguide.yaml"
        yaml = YAML()
        yaml.default_flow_style = False
        yaml_file = self._project_dir / filename

        data = styleguide.model_dump(mode="json", exclude_none=True)

        with yaml_file.open("w") as f:
            yaml.dump(data, f)

        self._styleguides[styleguide.id] = styleguide
        return yaml_file

"""
Directive repository with two-source loading (shipped + project).

Provides:
- Two-source YAML loading (shipped package data + project filesystem)
- Field-level merge semantics for project overrides
- Query methods (list_all, get)
- Save for project directives
- ID normalization (accepts both "004" and "DIRECTIVE_004")
"""

import re
import warnings
from pathlib import Path
from typing import Any

from importlib.resources import files
from ruamel.yaml import YAML

from .models import Directive


class DirectiveRepository:
    """Repository for loading and managing directive YAML files."""

    def __init__(
        self,
        shipped_dir: Path | None = None,
        project_dir: Path | None = None,
    ) -> None:
        self._directives: dict[str, Directive] = {}
        self._shipped_dir = shipped_dir or self._default_shipped_dir()
        self._project_dir = project_dir
        self._load()

    @staticmethod
    def _default_shipped_dir() -> Path:
        """Get default shipped directives directory from package data."""
        try:
            resource = files("doctrine.directives")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except Exception:
            return Path(__file__).parent / "shipped"

    def _load(self) -> None:
        """Load directives from shipped and project directories."""
        yaml = YAML(typ="safe")
        shipped: dict[str, Directive] = {}

        if self._shipped_dir.exists():
            for yaml_file in sorted(self._shipped_dir.glob("*.directive.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    directive = Directive.model_validate(data)
                    shipped[directive.id] = directive
                except Exception as e:
                    warnings.warn(
                        f"Skipping invalid shipped directive {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

        self._directives = shipped.copy()

        if self._project_dir and self._project_dir.exists():
            for yaml_file in sorted(self._project_dir.glob("*.directive.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    directive_id = data.get("id")
                    if not directive_id:
                        warnings.warn(
                            f"Skipping project directive {yaml_file.name}: no id",
                            UserWarning,
                            stacklevel=2,
                        )
                        continue

                    if directive_id in shipped:
                        merged = self._merge_directives(shipped[directive_id], data)
                        self._directives[directive_id] = merged
                    else:
                        directive = Directive.model_validate(data)
                        self._directives[directive.id] = directive
                except Exception as e:
                    warnings.warn(
                        f"Skipping invalid project directive {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

    @staticmethod
    def _normalize_id(directive_id: str) -> str:
        """Normalize directive ID to canonical form.

        Accepts:
        - "004" or "4" → "DIRECTIVE_004"
        - "DIRECTIVE_004" → "DIRECTIVE_004" (pass-through)
        """
        if re.match(r"^\d+$", directive_id):
            return f"DIRECTIVE_{directive_id.zfill(3)}"
        return directive_id

    def _merge_directives(
        self, shipped: Directive, project_data: dict[str, Any]
    ) -> Directive:
        """Merge project data into shipped directive at field level."""
        shipped_dict = shipped.model_dump()
        merged = {**shipped_dict, **project_data}
        return Directive.model_validate(merged)

    def list_all(self) -> list[Directive]:
        """Return all loaded directives sorted by ID."""
        return sorted(self._directives.values(), key=lambda d: d.id)

    def get(self, directive_id: str) -> Directive | None:
        """Get directive by ID.

        Accepts both numeric shorthand ("004") and full ID ("DIRECTIVE_004").
        """
        normalized = self._normalize_id(directive_id)
        return self._directives.get(normalized)

    def save(self, directive: Directive) -> Path:
        """Save directive to project directory.

        Returns:
            Path to the written YAML file.

        Raises:
            ValueError: If project_dir is not configured.
        """
        if self._project_dir is None:
            raise ValueError("Cannot save directive: project_dir not configured")

        self._project_dir.mkdir(parents=True, exist_ok=True)

        # Derive filename from ID
        match = re.search(r"\d+", directive.id)
        numeric = match.group() if match else directive.id.lower()
        slug = directive.title.lower().replace(" ", "-")
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        filename = f"{numeric}-{slug}.directive.yaml"

        yaml = YAML()
        yaml.default_flow_style = False
        yaml_file = self._project_dir / filename

        data = directive.model_dump(mode="json", exclude_none=True)

        with yaml_file.open("w") as f:
            yaml.dump(data, f)

        self._directives[directive.id] = directive
        return yaml_file

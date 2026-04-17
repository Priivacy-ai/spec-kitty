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
from pathlib import Path
from typing import Any

from importlib.resources import files
from ruamel.yaml import YAML

from doctrine.base import BaseDoctrineRepository
from .models import Directive
from .validation import reject_directive_inline_refs


class DirectiveRepository(BaseDoctrineRepository[Directive]):
    """Repository for loading and managing directive YAML files."""

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
        """Get default shipped directives directory from package data."""
        try:
            resource = files("doctrine.directives")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "shipped"

    @property
    def _schema(self) -> type[Directive]:
        return Directive

    @property
    def _glob(self) -> str:
        return "*.directive.yaml"

    def _pre_validate(self, data: dict[str, Any], yaml_file: Path) -> None:
        reject_directive_inline_refs(data, file_path=str(yaml_file))

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

    def get(self, directive_id: str) -> Directive | None:
        """Get directive by ID.

        Accepts both numeric shorthand ("004") and full ID ("DIRECTIVE_004").
        """
        normalized = self._normalize_id(directive_id)
        return self._items.get(normalized)

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

        self._items[directive.id] = directive
        return yaml_file

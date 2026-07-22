"""Glossary pack repository (FR-004).

``GlossaryPackRepository`` inherits the shared three-source loading pattern
from :class:`doctrine.base.BaseDoctrineRepository` (built-in rglob + org glob
+ project glob, field-level merge, provenance tagging) and globs
``*.glossary-pack.yaml``. No glob/merge logic is re-implemented here.
"""

from pathlib import Path

from importlib.resources import files

from doctrine.base import BaseDoctrineRepository
from .models import GlossaryPack


class GlossaryPackRepository(BaseDoctrineRepository[GlossaryPack]):
    """Repository for loading and managing glossary-pack YAML files."""

    def __init__(
        self,
        built_in_dir: Path | None = None,
        *,
        org_dirs: list[Path] | None = None,
        project_dir: Path | None = None,
    ) -> None:
        super().__init__(
            built_in_dir=built_in_dir or self._default_built_in_dir(),
            org_dirs=org_dirs,
            project_dir=project_dir,
        )

    @staticmethod
    def _default_built_in_dir() -> Path:
        """Get default built-in glossary-packs directory from package data."""
        try:
            resource = files("doctrine.glossary_packs")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("built-in")))
            return Path(str(resource)) / "built-in"
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "built-in"

    @property
    def _schema(self) -> type[GlossaryPack]:
        return GlossaryPack

    @property
    def _glob(self) -> str:
        return "*.glossary-pack.yaml"


__all__ = ["GlossaryPackRepository"]

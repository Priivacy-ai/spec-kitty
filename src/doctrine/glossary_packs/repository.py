"""Glossary pack repository (FR-004).

``GlossaryPackRepository`` inherits the shared three-source loading pattern
from :class:`doctrine.base.BaseDoctrineRepository` (built-in rglob + org glob
+ project glob, field-level merge, provenance tagging) and globs
``*.glossary-pack.yaml``. No glob/merge logic is re-implemented here.
"""

from pathlib import Path


from doctrine.pack_paths import resolve_pack_root
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
        return resolve_pack_root("built-in") / "glossary_packs"

    @property
    def _schema(self) -> type[GlossaryPack]:
        return GlossaryPack

    @property
    def _glob(self) -> str:
        return "*.glossary-pack.yaml"


__all__ = ["GlossaryPackRepository"]

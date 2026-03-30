"""Repository for central (non-mission-scoped) command templates.

Central command templates are the base layer that ``spec-kitty init`` merges
with mission-specific overrides.  They live in
``doctrine/templates/command-templates/`` and are resolved via
``importlib.resources`` so the path is valid from both editable installs and
built wheels.

This repository is intentionally *not* exposed via ``doctrine.__init__`` --
it is an internal domain accessor.  If external consumers need it, we can
promote it later.
"""

from __future__ import annotations

from pathlib import Path


class CentralTemplateRepository:
    """Path-based lookup for the central (base) command templates."""

    def __init__(self, templates_root: Path) -> None:
        self._root = templates_root

    # ------------------------------------------------------------------
    # Class-level constructor helpers
    # ------------------------------------------------------------------

    @classmethod
    def default(cls) -> CentralTemplateRepository:
        """Return a repository rooted at the package-bundled templates."""
        return cls(cls.default_root())

    @classmethod
    def default_root(cls) -> Path:
        """Return the command-templates dir bundled with the ``doctrine`` package.

        Uses ``importlib.resources`` so the path works from editable installs
        and built wheels alike.
        """
        try:
            from importlib.resources import files

            resource = files("doctrine") / "templates" / "command-templates"
            return Path(str(resource))
        except Exception:
            return Path(__file__).parent / "command-templates"

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------

    def get(self, name: str) -> Path | None:
        """Return the path to a central command template, or ``None``.

        Args:
            name: Template filename (e.g. ``"plan.md"``).
        """
        path = self._root / name
        return path if path.is_file() else None

    def list_templates(self) -> list[str]:
        """Return sorted filenames of all ``.md`` templates in the root."""
        if not self._root.is_dir():
            return []
        return sorted(p.name for p in self._root.glob("*.md"))

    def root(self) -> Path:
        """Return the underlying root directory."""
        return self._root

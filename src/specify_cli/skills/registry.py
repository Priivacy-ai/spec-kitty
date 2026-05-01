"""Canonical skill registry — discovers skills from the doctrine layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CanonicalSkill:
    """A single canonical skill discovered from the doctrine skills directory."""

    name: str
    skill_dir: Path
    skill_md: Path
    references: list[Path] = field(default_factory=list)
    scripts: list[Path] = field(default_factory=list)
    assets: list[Path] = field(default_factory=list)

    @property
    def all_files(self) -> list[Path]:
        """All installable files (SKILL.md + references + scripts + assets)."""
        return [self.skill_md] + self.references + self.scripts + self.assets


def _collect_files(directory: Path) -> list[Path]:
    """Return sorted list of files in *directory*, excluding dotfiles like .gitkeep."""
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.is_file() and not p.name.startswith("."))


class SkillRegistry:
    """Discovers canonical skills from a skills root directory."""

    def __init__(self, skills_root: Path) -> None:
        self._skills_root = skills_root

    @classmethod
    def from_local_repo(cls, repo_root: Path) -> SkillRegistry:
        """Create registry from local dev checkout."""
        return cls(repo_root / "src" / "doctrine" / "skills")

    @classmethod
    def from_package(cls) -> SkillRegistry:
        """Create registry from installed package.

        ``get_package_asset_root()`` resolves to ``<pkg>/missions`` which is
        inside ``specify_cli/``.  The doctrine tree is a sibling top-level
        package (``site-packages/doctrine/skills``), so we resolve it via
        ``importlib.resources`` directly.  A development-mode fallback walks
        up from ``specify_cli`` to ``src/doctrine/skills``.
        """
        import importlib.resources

        # Installed package: doctrine is a sibling top-level package
        try:
            doctrine_root = importlib.resources.files("doctrine")
            skills_path = Path(str(doctrine_root / "skills"))
            if skills_path.is_dir():
                return cls(skills_path)
        except (ModuleNotFoundError, TypeError):
            pass

        # Development fallback: src/doctrine/skills relative to specify_cli
        dev_path = Path(__file__).resolve().parent.parent.parent / "doctrine" / "skills"
        return cls(dev_path)

    def discover_skills(self) -> list[CanonicalSkill]:
        """Discover all valid skills in the skills root.

        Scans subdirectories for those containing a ``SKILL.md`` file and
        returns a sorted list of :class:`CanonicalSkill` objects.

        Returns an empty list when *skills_root* does not exist.
        """
        if not self._skills_root.is_dir():
            return []

        skills: list[CanonicalSkill] = []
        for child in sorted(self._skills_root.iterdir()):
            if not child.is_dir():
                continue
            skill_md = child / "SKILL.md"
            if not skill_md.is_file():
                continue
            skills.append(
                CanonicalSkill(
                    name=child.name,
                    skill_dir=child,
                    skill_md=skill_md,
                    references=_collect_files(child / "references"),
                    scripts=_collect_files(child / "scripts"),
                    assets=_collect_files(child / "assets"),
                )
            )
        return skills

    def get_skill(self, name: str) -> CanonicalSkill | None:
        """Get a specific skill by name, or ``None`` if not found."""
        for skill in self.discover_skills():
            if skill.name == name:
                return skill
        return None

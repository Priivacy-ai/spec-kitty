"""Migration: replace 'planning repository' with 'project root checkout' in agent command files.

Agents interpret 'planning repository' as a separate repository, causing
features to be created in the wrong project. The intended meaning was always
'the main checkout of this repository, not a worktree.'

This migration performs a text replacement in all agent command/prompt files
that contain the old terminology.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project

logger = logging.getLogger(__name__)

_OLD_TERMS = [
    ("planning repository", "project root checkout"),
    ("planning repo", "project root"),
    ("Planning repository", "Project root checkout"),
    ("Planning repo", "Project root"),
]


def _needs_fix(project_path: Path) -> list[Path]:
    """Return list of agent command files that contain the old terminology."""
    hits: list[Path] = []
    agent_dirs = get_agent_dirs_for_project(project_path)
    for agent_root, command_subdir in agent_dirs:
        cmd_dir = project_path / agent_root / command_subdir
        if not cmd_dir.is_dir():
            continue
        for md_file in cmd_dir.glob("spec-kitty.*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if "planning repository" in content.lower():
                    hits.append(md_file)
            except OSError:
                continue
    return hits


@MigrationRegistry.register
class FixPlanningRepositoryTerminology(BaseMigration):
    """Replace ambiguous 'planning repository' in agent command files."""

    migration_id = "2.1.3_fix_planning_repository_terminology"
    description = (
        "Replace 'planning repository' with 'project root checkout' "
        "in agent command files to prevent agents from creating features "
        "in the wrong repository"
    )
    target_version = "2.1.3"

    def detect(self, project_path: Path) -> bool:
        """Return True if any agent command files contain the old term."""
        return len(_needs_fix(project_path)) > 0

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if there are files to fix."""
        hits = _needs_fix(project_path)
        if hits:
            return True, ""
        return False, "No agent command files contain 'planning repository'"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Replace terminology in all affected agent command files."""
        hits = _needs_fix(project_path)
        if not hits:
            return MigrationResult(
                success=True,
                changes_made=["No files needed updating"],
            )

        changed: list[str] = []
        for md_file in hits:
            try:
                content = md_file.read_text(encoding="utf-8")
                original = content
                for old, new in _OLD_TERMS:
                    content = content.replace(old, new)
                if content != original:
                    if not dry_run:
                        md_file.write_text(content, encoding="utf-8")
                    changed.append(str(md_file.relative_to(project_path)))
                    logger.info("Updated: %s", md_file.relative_to(project_path))
            except OSError as exc:
                logger.warning("Could not update %s: %s", md_file, exc)

        return MigrationResult(
            success=True,
            changes_made=changed or [f"Updated {len(changed)} file(s): 'planning repository' → 'project root checkout'"],
        )

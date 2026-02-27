"""Migration: Repair stale generated command prompts with deterministic command usage.

Updates existing generated agent prompts in user projects to fix:
- deprecated command path (`spec-kitty agent check-prerequisites`)
- invalid flag usage (`--require-tasks`)
- unresolved script placeholder (`(Missing script command for sh)`)
- stale merge wording that encourages sequential WP loops
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project


@MigrationRegistry.register
class FixGeneratedCommandTemplatesMigration(BaseMigration):
    """Repair stale generated command templates in configured agent dirs."""

    migration_id = "2.0.1_fix_generated_command_templates"
    description = "Repair stale generated command prompt commands and merge guidance"
    target_version = "2.0.1"

    FILE_GLOBS = ["spec-kitty.*.md", "spec-kitty.*.toml"]

    REPLACEMENTS: list[tuple[str, str]] = [
        (
            "spec-kitty agent check-prerequisites",
            "spec-kitty agent feature check-prerequisites",
        ),
        ("--require-tasks --include-tasks", "--include-tasks"),
        ("--require-tasks", "--include-tasks"),
        (
            "(Missing script command for sh)",
            "spec-kitty agent feature check-prerequisites --json --paths-only",
        ),
        (
            "merges each WP branch into main in sequence",
            "merges effective WP branch tips after ancestry pruning",
        ),
        (
            "Merges each WP branch into the target branch in sequence",
            "Merges effective WP branch tips after ancestry pruning",
        ),
        (
            "main repository root",
            "primary repository checkout root",
        ),
    ]

    def detect(self, project_path: Path) -> bool:
        """Detect stale generated prompts that require repair."""
        for file_path in self._iter_generated_prompt_files(project_path):
            try:
                content = file_path.read_text(encoding="utf-8")
            except OSError:
                continue
            if (
                "spec-kitty agent check-prerequisites" in content
                or "--require-tasks" in content
                or "(Missing script command for sh)" in content
                or "merges each WP branch into main in sequence" in content
            ):
                return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Apply textual repairs to generated prompt files."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        for file_path in self._iter_generated_prompt_files(project_path):
            try:
                original = file_path.read_text(encoding="utf-8")
            except OSError as exc:
                warnings.append(f"Skipped unreadable file {file_path}: {exc}")
                continue

            updated = original
            for old, new in self.REPLACEMENTS:
                updated = updated.replace(old, new)

            if updated == original:
                continue

            rel = str(file_path.relative_to(project_path))
            if dry_run:
                changes.append(f"Would update: {rel}")
                continue

            try:
                file_path.write_text(updated, encoding="utf-8")
            except OSError as exc:
                errors.append(f"Failed to update {rel}: {exc}")
                continue

            changes.append(f"Updated: {rel}")

        if not changes and not errors:
            changes.append("No generated prompt files needed repair")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

    def _iter_generated_prompt_files(self, project_path: Path) -> list[Path]:
        """Enumerate generated command prompt files for configured agents."""
        files: list[Path] = []
        for agent_dir, subdir in get_agent_dirs_for_project(project_path):
            command_dir = project_path / agent_dir / subdir
            if not command_dir.exists():
                continue
            for pattern in self.FILE_GLOBS:
                files.extend(sorted(command_dir.glob(pattern)))
        return files

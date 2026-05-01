"""Migration: Repair stale generated command prompts with deterministic command usage.

Updates existing generated agent prompts in user projects to fix:
- deprecated command path (`spec-kitty agent check-prerequisites`)
- invalid flag usage (`--require-tasks`)
- unresolved script placeholder (`(Missing script command for sh)`)
- stale merge wording that encourages sequential WP loops
"""

from __future__ import annotations

import re
from pathlib import Path

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
            "spec-kitty agent mission check-prerequisites",
        ),
        ("--require-tasks --include-tasks", "--include-tasks"),
        ("--require-tasks", "--include-tasks"),
        (
            "(Missing script command for sh)",
            "spec-kitty agent mission check-prerequisites --json --paths-only",
        ),
        (
            "main repository root",
            "primary repository checkout root",
        ),
    ]

    STALE_MERGE_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"merges each .* into main in sequence"),
        re.compile(r"Merges each .* into the target branch in sequence"),
        re.compile(r"merges each lane branch into the mission branch before the target branch"),
    )

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
                or any(pattern.search(content) for pattern in self.STALE_MERGE_PATTERNS)
            ):
                return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Apply textual repairs to generated prompt files."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        for file_path in self._iter_generated_prompt_files(project_path):
            try:
                original = file_path.read_text(encoding="utf-8")
            except OSError as exc:
                warnings.append(f"Skipped unreadable file {file_path}: {exc}")
                continue

            updated = original
            for old, new in self.REPLACEMENTS:
                updated = updated.replace(old, new)
            for pattern in self.STALE_MERGE_PATTERNS:
                updated = pattern.sub(
                    "merges lane branches into the mission branch before landing the mission branch",
                    updated,
                )

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
        """Enumerate generated command prompt files for configured agents.

        Includes legacy ``.codex/prompts`` when present so upgrades can still
        repair projects created before Codex moved to Agent Skills.
        """
        files: list[Path] = []
        command_dirs: list[Path] = [
            project_path / agent_dir / subdir
            for agent_dir, subdir in get_agent_dirs_for_project(project_path)
        ]

        legacy_codex_dir = project_path / ".codex" / "prompts"
        if legacy_codex_dir.exists():
            command_dirs.append(legacy_codex_dir)

        seen: set[Path] = set()
        for command_dir in command_dirs:
            if not command_dir.exists() or command_dir in seen:
                continue
            seen.add(command_dir)
            for pattern in self.FILE_GLOBS:
                files.extend(sorted(command_dir.glob(pattern)))
        return files

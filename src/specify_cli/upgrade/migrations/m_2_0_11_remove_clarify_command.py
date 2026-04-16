"""Migration: Remove deprecated /spec-kitty.clarify command artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from specify_cli.agent_utils.directories import AGENT_DIRS

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class RemoveClarifyCommandMigration(BaseMigration):
    """Delete stale clarify command files from initialized projects."""

    migration_id = "2.0.11_remove_clarify_command"
    description = "Remove deprecated /spec-kitty.clarify command artifacts"
    target_version = "2.0.11"

    def detect(self, project_path: Path) -> bool:
        """Check whether any clarify artifacts still exist."""
        return any(self._iter_targets(project_path))

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """This migration is safe whenever clarify artifacts are present."""
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Remove clarify command artifacts from agent dirs and .kittify templates."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        targets = list(self._iter_targets(project_path))
        if not targets:
            return MigrationResult(
                success=True,
                changes_made=["No clarify command artifacts found"],
                warnings=warnings,
                errors=errors,
            )

        for target in targets:
            rel = target.relative_to(project_path)
            if dry_run:
                changes.append(f"Would remove: {rel}")
                continue

            try:
                target.unlink()
                changes.append(f"Removed: {rel}")
            except OSError as exc:
                errors.append(f"Failed to remove {rel}: {exc}")

        if not errors:
            summary = (
                f"Would remove {len(targets)} clarify command artifacts"
                if dry_run
                else f"Removed {len(targets)} clarify command artifacts"
            )
            changes.append(summary)

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            warnings=warnings,
            errors=errors,
        )

    def _iter_targets(self, project_path: Path) -> Iterable[Path]:
        """Yield every on-disk clarify artifact that should be deleted."""
        candidates: list[Path] = []

        templates_root = project_path / ".kittify" / "templates"
        missions_root = project_path / ".kittify" / "missions"

        candidates.append(templates_root / "command-templates" / "clarify.md")
        if templates_root.exists():
            candidates.extend(sorted(templates_root.glob(".merged-*/clarify.md")))

        if missions_root.exists():
            candidates.extend(sorted(missions_root.glob("*/command-templates/clarify.md")))

        # Scan every known agent directory, including stale/orphaned ones that
        # may no longer be present in config.yaml.
        for agent_root, subdir in AGENT_DIRS:
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.exists():
                continue
            candidates.extend(sorted(path for path in agent_dir.glob("spec-kitty.clarify*") if path.is_file()))

        seen: set[Path] = set()
        sorted_candidates = sorted(
            candidates,
            key=lambda item: str(item.relative_to(project_path)) if item.exists() else str(item),
        )
        for path in sorted_candidates:
            if not path.exists():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path

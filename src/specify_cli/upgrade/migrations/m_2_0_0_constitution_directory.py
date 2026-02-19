"""Migration: Move constitution to .kittify/constitution/ directory."""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class Migration:
    version = "2.0.0"
    description = "Move constitution to .kittify/constitution/ directory"

    def apply(self, project_path: Path, dry_run: bool = False) -> list[str]:
        changes = []
        old_path = project_path / ".kittify" / "memory" / "constitution.md"
        new_dir = project_path / ".kittify" / "constitution"
        new_path = new_dir / "constitution.md"

        # Scenario 1: Old path exists, new doesn't → move
        if old_path.exists() and not new_path.exists():
            if not dry_run:
                new_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_path), str(new_path))
                changes.append(f"Moved {old_path.relative_to(project_path)} → {new_path.relative_to(project_path)}")

                # Trigger initial extraction
                try:
                    from specify_cli.constitution.sync import sync

                    result = sync(new_path, force=True)
                    if result.synced:
                        changes.append(
                            f"Initial extraction: {len(result.files_written)} YAML files created"
                        )
                    elif result.error:
                        changes.append(
                            f"Warning: Initial extraction failed: {result.error}"
                        )
                except Exception as e:
                    changes.append(
                        f"Warning: Initial extraction skipped ({e}). "
                        f"Run 'spec-kitty constitution sync' manually."
                    )
            else:
                changes.append(
                    f"Would move {old_path.relative_to(project_path)} → {new_path.relative_to(project_path)}"
                )

        # Scenario 2: Both exist → skip (user already migrated manually)
        elif old_path.exists() and new_path.exists():
            changes.append(
                f"Constitution already at {new_path.relative_to(project_path)}, "
                f"old copy remains at {old_path.relative_to(project_path)}"
            )

        # Scenario 3: New exists, old doesn't → skip (already migrated)
        elif new_path.exists() and not old_path.exists():
            changes.append(
                f"Constitution already at {new_path.relative_to(project_path)}"
            )

        # Scenario 4: Neither exists → skip (no constitution)
        else:
            changes.append("No constitution found, skipping migration")

        return changes

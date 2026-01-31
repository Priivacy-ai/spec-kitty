"""Migration: Add target_branch field to feature metadata.

This migration adds a target_branch field to all feature meta.json files.
The target_branch determines where status commits and implementation work
should be routed:
- "main" for 1.x features (CLI-only features)
- "2.x" for SaaS features (requires 2.x architecture)

This fixes the race condition where Feature 025 (targeting 2.x) was having
its status commits routed to main, causing branch divergence.

Version: 0.13.7 → 0.13.8
Breaking: No
Required: Yes
"""

from __future__ import annotations

import json
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class TargetBranchMigration(BaseMigration):
    """Add target_branch to all features."""

    migration_id = "0.13.8_target_branch"
    description = "Add target_branch field to feature metadata"
    target_version = "0.13.8"

    def detect(self, project_path: Path) -> bool:
        """Check if any feature is missing target_branch field."""
        kitty_specs = project_path / "kitty-specs"
        if not kitty_specs.exists():
            return False

        for feature_dir in kitty_specs.glob("[0-9][0-9][0-9]-*/"):
            meta_file = feature_dir / "meta.json"
            if not meta_file.exists():
                continue

            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                if "target_branch" not in meta:
                    # At least one feature missing target_branch
                    return True
            except (json.JSONDecodeError, OSError):
                # Skip malformed files
                continue

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if migration can be applied."""
        kitty_specs = project_path / "kitty-specs"
        if not kitty_specs.exists():
            return True, ""  # No features, nothing to do

        # Migration can always be applied (just adds missing fields)
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Add target_branch to all feature meta.json files."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        kitty_specs = project_path / "kitty-specs"
        if not kitty_specs.exists():
            return MigrationResult(
                success=True,
                changes_made=["No features found, skipping target_branch addition"],
            )

        for feature_dir in kitty_specs.glob("[0-9][0-9][0-9]-*/"):
            meta_file = feature_dir / "meta.json"
            if not meta_file.exists():
                continue

            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))

                # Skip if already has target_branch
                if "target_branch" in meta:
                    continue

                # Detect target from spec.md for Feature 025
                target_branch = "main"  # Default for all features

                if meta.get("feature_number") == "025":
                    spec_file = feature_dir / "spec.md"
                    if spec_file.exists():
                        try:
                            content = spec_file.read_text(encoding="utf-8")
                            # Look for explicit target branch markers
                            if any(
                                marker in content
                                for marker in [
                                    "**Target Branch**: 2.x",
                                    "Target Branch**: 2.x development",
                                    "**Target**: 2.x branch",
                                ]
                            ):
                                target_branch = "2.x"
                                warnings.append(
                                    f"Feature 025 auto-detected as 2.x target from spec.md"
                                )
                        except OSError:
                            # Can't read spec, use default
                            pass

                # Add target_branch field
                meta["target_branch"] = target_branch

                if dry_run:
                    changes.append(
                        f"Would add target_branch={target_branch} to {feature_dir.name}"
                    )
                else:
                    # Write updated meta.json with pretty formatting
                    meta_file.write_text(
                        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    changes.append(f"Added target_branch={target_branch} to {feature_dir.name}")

            except json.JSONDecodeError as e:
                errors.append(f"Malformed JSON in {feature_dir.name}/meta.json: {e}")
            except OSError as e:
                errors.append(f"Failed to update {feature_dir.name}/meta.json: {e}")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

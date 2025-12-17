"""Migration: Convert directory-based task lanes to frontmatter-only lanes."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import List, Tuple

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class FrontmatterOnlyLanesMigration(BaseMigration):
    """Migrate from directory-based to frontmatter-only lane management.

    As of v0.9.0, task lanes are determined solely by the `lane:` field
    in the YAML frontmatter of work package files. The directory structure
    (tasks/planned/, tasks/doing/, etc.) is flattened to a single tasks/
    directory.

    This migration:
    1. Moves WP files from tasks/{lane}/ to tasks/
    2. Ensures the `lane:` field is set from the source directory
    3. Removes empty lane subdirectories
    4. Processes main kitty-specs/ and all .worktrees/
    """

    migration_id = "0.9.0_frontmatter_only_lanes"
    description = "Flatten task lanes to frontmatter-only (no more directory-based lanes)"
    target_version = "0.9.0"

    LANE_DIRS: Tuple[str, ...] = ("planned", "doing", "for_review", "done")

    def detect(self, project_path: Path) -> bool:
        """Check if any feature uses legacy directory-based lanes."""
        # Check main kitty-specs/
        main_specs = project_path / "kitty-specs"
        if main_specs.exists():
            for feature_dir in main_specs.iterdir():
                if feature_dir.is_dir() and self._is_legacy_format(feature_dir):
                    return True

        # Check .worktrees/
        worktrees_dir = project_path / ".worktrees"
        if worktrees_dir.exists():
            for worktree in worktrees_dir.iterdir():
                if worktree.is_dir():
                    wt_specs = worktree / "kitty-specs"
                    if wt_specs.exists():
                        for feature_dir in wt_specs.iterdir():
                            if feature_dir.is_dir() and self._is_legacy_format(feature_dir):
                                return True

        return False

    def _is_legacy_format(self, feature_path: Path) -> bool:
        """Check if a feature uses legacy directory-based lanes."""
        tasks_dir = feature_path / "tasks"
        if not tasks_dir.exists():
            return False

        # A feature is legacy if it has ANY lane subdirectories
        # (even if empty - they shouldn't exist in new format)
        for lane in self.LANE_DIRS:
            lane_path = tasks_dir / lane
            if lane_path.exists() and lane_path.is_dir():
                # Directory exists - this is legacy format
                # Check if it has any content (not just .gitkeep)
                contents = [f for f in lane_path.iterdir() if f.name != ".gitkeep"]
                if contents:
                    return True
                # Even if only .gitkeep, still need migration to remove the directory
                elif any(lane_path.iterdir()):
                    return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Migration can always be applied if legacy format is detected."""
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Migrate all features from directory-based to frontmatter-only lanes."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        features_found = self._find_features_to_migrate(project_path)

        if not features_found:
            warnings.append("No features need migration - all already use flat structure")
            return MigrationResult(
                success=True,
                changes_made=changes,
                errors=errors,
                warnings=warnings,
            )

        total_migrated = 0
        total_skipped = 0

        for feature_dir, location_label in features_found:
            feature_changes, feature_warnings, feature_errors, migrated, skipped = (
                self._migrate_feature(feature_dir, location_label, dry_run)
            )
            changes.extend(feature_changes)
            warnings.extend(feature_warnings)
            errors.extend(feature_errors)
            total_migrated += migrated
            total_skipped += skipped

        if dry_run:
            changes.append(f"Would migrate {total_migrated} WP files across {len(features_found)} features")
        else:
            changes.append(f"Migrated {total_migrated} WP files across {len(features_found)} features")

        if total_skipped > 0:
            warnings.append(f"Skipped {total_skipped} files (already exist or conflicts)")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

    def _find_features_to_migrate(self, project_path: Path) -> List[Tuple[Path, str]]:
        """Find all features with legacy format in main repo and worktrees."""
        features: List[Tuple[Path, str]] = []

        # Scan main kitty-specs/
        main_specs = project_path / "kitty-specs"
        if main_specs.exists():
            for feature_dir in sorted(main_specs.iterdir()):
                if feature_dir.is_dir() and self._is_legacy_format(feature_dir):
                    features.append((feature_dir, "main"))

        # Scan .worktrees/
        worktrees_dir = project_path / ".worktrees"
        if worktrees_dir.exists():
            for worktree in sorted(worktrees_dir.iterdir()):
                if worktree.is_dir():
                    wt_specs = worktree / "kitty-specs"
                    if wt_specs.exists():
                        for feature_dir in sorted(wt_specs.iterdir()):
                            if feature_dir.is_dir() and self._is_legacy_format(feature_dir):
                                features.append((feature_dir, f"worktree:{worktree.name}"))

        return features

    def _migrate_feature(
        self,
        feature_dir: Path,
        location_label: str,
        dry_run: bool,
    ) -> Tuple[List[str], List[str], List[str], int, int]:
        """Migrate a single feature from directory-based to flat structure."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []
        migrated = 0
        skipped = 0

        tasks_dir = feature_dir / "tasks"
        if not tasks_dir.exists():
            return changes, warnings, errors, migrated, skipped

        feature_name = feature_dir.name
        changes.append(f"[{location_label}] {feature_name}:")

        for lane in self.LANE_DIRS:
            lane_dir = tasks_dir / lane
            if not lane_dir.is_dir():
                continue

            # Find ALL markdown files, not just WP*.md
            md_files = sorted(lane_dir.glob("*.md"))

            for md_file in md_files:
                # Skip README.md if it exists
                if md_file.name == "README.md":
                    continue

                target = tasks_dir / md_file.name

                # Check if already exists in flat directory
                if target.exists():
                    warnings.append(f"  Skip: {md_file.name} already exists in tasks/")
                    skipped += 1
                    continue

                try:
                    if dry_run:
                        changes.append(f"  Would move: {lane}/{md_file.name} → tasks/{md_file.name}")
                    else:
                        # Read and update content
                        content = md_file.read_text(encoding="utf-8-sig")
                        updated_content = self._ensure_lane_in_frontmatter(content, lane)

                        # Write to new location
                        target.write_text(updated_content, encoding="utf-8")

                        # Remove original
                        md_file.unlink()

                        changes.append(f"  Moved: {lane}/{md_file.name} → tasks/{md_file.name}")

                    migrated += 1

                except Exception as e:
                    errors.append(f"  Error migrating {md_file.name}: {e}")

        # Clean up empty lane directories
        if not dry_run:
            for lane in self.LANE_DIRS:
                lane_dir = tasks_dir / lane
                if lane_dir.exists() and lane_dir.is_dir():
                    contents = list(lane_dir.iterdir())
                    # Remove if empty or only .gitkeep
                    if not contents or (len(contents) == 1 and contents[0].name == ".gitkeep"):
                        try:
                            # Use shutil.rmtree for more robust removal
                            shutil.rmtree(lane_dir)
                            changes.append(f"  Removed empty: {lane}/")
                        except OSError as e:
                            warnings.append(f"  Could not remove {lane}/: {e}")
        else:
            for lane in self.LANE_DIRS:
                lane_dir = tasks_dir / lane
                if lane_dir.exists() and lane_dir.is_dir():
                    contents = list(lane_dir.iterdir())
                    if not contents or (len(contents) == 1 and contents[0].name == ".gitkeep"):
                        changes.append(f"  Would remove empty: {lane}/")

        return changes, warnings, errors, migrated, skipped

    def _ensure_lane_in_frontmatter(self, content: str, expected_lane: str) -> str:
        """Ensure frontmatter has correct lane field."""
        # Find frontmatter boundaries
        if not content.startswith("---"):
            # No frontmatter, add it
            return f'---\nlane: "{expected_lane}"\n---\n{content}'

        # Find closing ---
        lines = content.split("\n")
        closing_idx = -1
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                closing_idx = i
                break

        if closing_idx == -1:
            # Malformed frontmatter, add lane anyway
            return f'---\nlane: "{expected_lane}"\n---\n{content}'

        frontmatter_lines = lines[1:closing_idx]
        body_lines = lines[closing_idx + 1:]

        # Check if lane field exists
        lane_pattern = re.compile(r'^lane:\s*(.*)$')
        lane_found = False
        updated_lines = []

        for line in frontmatter_lines:
            match = lane_pattern.match(line)
            if match:
                lane_found = True
                current_value = match.group(1).strip().strip('"\'')
                if current_value != expected_lane:
                    # Replace with expected lane from directory
                    updated_lines.append(f'lane: "{expected_lane}"')
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        if not lane_found:
            # Insert lane field (before history: if present, otherwise at end)
            insert_idx = len(updated_lines)
            for i, line in enumerate(updated_lines):
                if line.startswith("history:"):
                    insert_idx = i
                    break
            updated_lines.insert(insert_idx, f'lane: "{expected_lane}"')

        # Reconstruct document
        result_lines = ["---"] + updated_lines + ["---"] + body_lines
        return "\n".join(result_lines)

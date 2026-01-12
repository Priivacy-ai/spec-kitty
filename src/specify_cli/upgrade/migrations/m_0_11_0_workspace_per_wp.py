"""Migration: Workspace-per-WP model with dependency tracking (0.11.0)."""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from specify_cli.template.manager import get_local_repo_root

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

MIGRATION_ID = "0.11.0_workspace_per_wp"
MIGRATION_VERSION = "0.11.0"
MIGRATION_DESCRIPTION = "Workspace-per-WP model with dependency tracking"

MISSION_NAME = "software-dev"
TEMPLATE_FILES = ("specify.md", "plan.md", "tasks.md", "implement.md")


def detect_legacy_worktrees(project_root: Path) -> List[Path]:
    """Find legacy worktrees (pre-0.11.0)."""
    worktrees_dir = project_root / ".worktrees"
    if not worktrees_dir.exists():
        return []

    legacy_worktrees: List[Path] = []
    for item in sorted(worktrees_dir.iterdir()):
        if not item.is_dir():
            continue

        name = item.name
        has_feature_pattern = re.match(r"^\d{3}-", name)
        has_wp_suffix = re.search(r"-WP\d{2}$", name)

        if has_feature_pattern and not has_wp_suffix:
            legacy_worktrees.append(item)

    return legacy_worktrees


def validate_upgrade(project_root: Path) -> Tuple[bool, List[str]]:
    """Validate project is ready for 0.11.0 upgrade."""
    legacy_worktrees = detect_legacy_worktrees(project_root)
    if not legacy_worktrees:
        return True, []

    errors = [
        "Cannot upgrade to 0.11.0 - legacy worktrees detected:",
        "",
    ]
    for worktree in legacy_worktrees:
        errors.append(f"  - {worktree.name}")

    errors.extend(
        [
            "",
            "Action required before upgrade:",
            "  1. Complete features: spec-kitty merge <feature>",
            "  2. OR delete worktrees: git worktree remove .worktrees/<feature>",
            "",
            "Use: spec-kitty list-legacy-features to see all legacy worktrees",
        ]
    )
    return False, errors


def _load_template_sources(base) -> Optional[Dict[str, str]]:
    contents: Dict[str, str] = {}
    for name in TEMPLATE_FILES:
        resource = base.joinpath(name)
        if not resource.exists():
            return None
        contents[name] = resource.read_text(encoding="utf-8")
    return contents


def _resolve_template_sources() -> Optional[Dict[str, str]]:
    local_repo = get_local_repo_root()
    if local_repo:
        candidates = [
            local_repo / "src" / "specify_cli" / "missions" / MISSION_NAME / "command-templates",  # 011: New location
            local_repo / ".kittify" / "missions" / MISSION_NAME / "command-templates",  # Legacy (pre-011)
        ]
        for candidate in candidates:
            if candidate.exists():
                contents = _load_template_sources(candidate)
                if contents:
                    return contents

    # 011: Templates packaged in src/specify_cli/missions/
    data_root = files("specify_cli")
    candidate = data_root.joinpath("missions", MISSION_NAME, "command-templates")
    if candidate.exists():
        contents = _load_template_sources(candidate)
        if contents:
            return contents

    return None


def update_template_sources(project_root: Path, dry_run: bool = False) -> Tuple[List[str], List[str]]:
    """Update mission command templates with workspace-per-WP workflow text."""
    changes: List[str] = []
    errors: List[str] = []

    templates_dir = project_root / ".kittify" / "missions" / MISSION_NAME / "command-templates"
    if not templates_dir.exists():
        errors.append(f"Missing mission templates at {templates_dir}")
        return changes, errors

    source_templates = _resolve_template_sources()
    if not source_templates:
        errors.append("Unable to locate packaged mission templates for update")
        return changes, errors

    updated = 0
    for name, content in source_templates.items():
        dest_path = templates_dir / name
        current = dest_path.read_text(encoding="utf-8") if dest_path.exists() else None
        if current == content:
            continue

        if dry_run:
            changes.append(f"Would update {dest_path}")
        else:
            dest_path.write_text(content, encoding="utf-8")
            changes.append(f"Updated {dest_path}")
        updated += 1

    if updated == 0:
        changes.append("Templates already up to date")

    return changes, errors


@MigrationRegistry.register
class WorkspacePerWPMigration(BaseMigration):
    """Upgrade templates for workspace-per-WP model with dependency tracking."""

    migration_id = MIGRATION_ID
    description = MIGRATION_DESCRIPTION
    target_version = MIGRATION_VERSION

    def detect(self, project_path: Path) -> bool:
        """Detect if mission templates need workspace-per-WP updates."""
        templates_dir = project_path / ".kittify" / "missions" / MISSION_NAME / "command-templates"
        if not templates_dir.exists():
            return False

        source_templates = _resolve_template_sources()
        if not source_templates:
            return False

        for name, content in source_templates.items():
            dest_path = templates_dir / name
            if not dest_path.exists():
                return True
            if dest_path.read_text(encoding="utf-8") != content:
                return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Block upgrade when legacy worktrees exist."""
        is_valid, errors = validate_upgrade(project_path)
        if not is_valid:
            return False, "\n".join(errors)
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Apply the workspace-per-WP migration."""
        changes, errors = update_template_sources(project_path, dry_run=dry_run)
        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=[],
        )

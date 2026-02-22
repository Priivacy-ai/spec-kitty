"""Migration: Install encoding validation pre-commit hooks."""

from __future__ import annotations

from pathlib import Path

from specify_cli.hooks import install_or_update_hooks, is_managed_shim

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class EncodingHooksMigration(BaseMigration):
    """Install encoding validation pre-commit hooks.

    This migration installs git hooks that validate file encoding
    before commits, preventing encoding issues from being committed.
    """

    migration_id = "0.5.0_encoding_hooks"
    description = "Install encoding validation pre-commit hooks"
    target_version = "0.5.0"

    HOOK_FILES = [
        "pre-commit",
        "commit-msg",
    ]

    def detect(self, project_path: Path) -> bool:
        """Check if encoding hooks are missing."""
        git_dir = project_path / ".git"
        if not git_dir.exists():
            return False  # Not a git repo, can't install hooks

        pre_commit = git_dir / "hooks" / "pre-commit"
        if not pre_commit.exists():
            return True

        if is_managed_shim(pre_commit):
            return False

        try:
            content = pre_commit.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return True

        # Check if it's our hook or a custom one
        return "spec-kitty" not in content.lower() and "encoding" not in content.lower()

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can install hooks."""
        git_dir = project_path / ".git"
        if not git_dir.exists():
            return False, "Not a git repository"

        hooks_dir = git_dir / "hooks"
        if not hooks_dir.exists():
            return True, ""

        pre_commit = hooks_dir / "pre-commit"
        if pre_commit.exists():
            try:
                content = pre_commit.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                return False, "Cannot read existing pre-commit hook"

            # Check if it's our hook
            if "spec-kitty" not in content.lower() and "encoding" not in content.lower():
                # It's a custom hook - warn but allow (will append)
                pass

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Install/update centralized hooks and per-project shims."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        git_dir = project_path / ".git"
        if not git_dir.exists():
            errors.append("Not a git repository")
            return MigrationResult(success=False, errors=errors)

        # Prefer project-local templates (legacy path), fallback to package assets.
        template_hooks_dir = project_path / ".kittify" / "templates" / "git-hooks"
        if not template_hooks_dir.exists():
            template_hooks_dir = None

        if dry_run:
            changes.append("Would install centralized hooks in ~/.kittify/hooks")
            changes.append("Would install/update project hook shims in .git/hooks")
            return MigrationResult(success=True, changes_made=changes)

        try:
            result = install_or_update_hooks(
                project_path,
                template_hooks_dir=template_hooks_dir,
                force=False,
            )
        except FileNotFoundError:
            warnings.append("Hook templates not found in package assets")
            return MigrationResult(
                success=True, changes_made=changes, warnings=warnings
            )
        except OSError as e:
            errors.append(f"Failed to install managed hooks: {e}")
            return MigrationResult(success=False, errors=errors)

        changes.append(
            f"Updated centralized hooks ({len(result.global_hooks)} file(s)) in {result.global_hooks_dir}"
        )
        if result.project.installed:
            changes.append(f"Installed shims: {', '.join(result.project.installed)}")
        if result.project.updated:
            changes.append(f"Updated shims: {', '.join(result.project.updated)}")
        if result.project.unchanged:
            changes.append(f"Unchanged shims: {', '.join(result.project.unchanged)}")
        if result.project.skipped_custom:
            warnings.append(
                f"Skipped custom hooks: {', '.join(result.project.skipped_custom)}"
            )
        if result.project.missing_global_targets:
            warnings.append(
                f"Missing global hook targets: {', '.join(result.project.missing_global_targets)}"
            )

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

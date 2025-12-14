"""Migration: Install encoding validation pre-commit hooks."""

from __future__ import annotations

import shutil
from pathlib import Path

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
        "pre-commit-encoding-check",
        "pre-commit-agent-check",
    ]

    def detect(self, project_path: Path) -> bool:
        """Check if encoding hooks are missing."""
        git_dir = project_path / ".git"
        if not git_dir.exists():
            return False  # Not a git repo, can't install hooks

        pre_commit = git_dir / "hooks" / "pre-commit"
        if not pre_commit.exists():
            return True

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
        """Install or update pre-commit hooks."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        git_dir = project_path / ".git"
        if not git_dir.exists():
            errors.append("Not a git repository")
            return MigrationResult(success=False, errors=errors)

        hooks_dir = git_dir / "hooks"

        # Find hook templates - try .kittify/templates first, then package
        template_hooks_dir = project_path / ".kittify" / "templates" / "git-hooks"

        if not template_hooks_dir.exists():
            # Try to find from package
            try:
                from importlib.resources import files

                pkg_hooks = files("specify_cli").joinpath("templates", "git-hooks")
                if hasattr(pkg_hooks, "is_dir") and pkg_hooks.is_dir():
                    template_hooks_dir = Path(str(pkg_hooks))
                else:
                    warnings.append(
                        "Hook templates not found in .kittify/templates/ or package"
                    )
                    return MigrationResult(
                        success=True, changes_made=changes, warnings=warnings
                    )
            except (ImportError, TypeError):
                warnings.append("Could not locate hook templates")
                return MigrationResult(
                    success=True, changes_made=changes, warnings=warnings
                )

        if dry_run:
            changes.append("Would install pre-commit hooks from templates")
            return MigrationResult(success=True, changes_made=changes)

        # Create hooks directory if needed
        try:
            hooks_dir.mkdir(exist_ok=True)
        except OSError as e:
            errors.append(f"Failed to create hooks directory: {e}")
            return MigrationResult(success=False, errors=errors)

        # Copy hook files
        for hook_name in self.HOOK_FILES:
            template_hook = template_hooks_dir / hook_name
            dest_hook = hooks_dir / hook_name

            if template_hook.exists():
                try:
                    shutil.copy2(template_hook, dest_hook)
                    dest_hook.chmod(0o755)
                    changes.append(f"Installed {hook_name} hook")
                except OSError as e:
                    errors.append(f"Failed to install {hook_name}: {e}")
            else:
                warnings.append(f"Template for {hook_name} not found")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

"""Migration: retire Spec Kitty-managed git hooks.

2.x no longer installs or manages git hooks. This migration removes only
hooks that match known Spec Kitty-managed signatures and leaves custom hooks
untouched.
"""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


MANAGED_HOOK_NAMES: tuple[str, ...] = (
    "pre-commit",
    "commit-msg",
    "pre-commit-agent-check",
    "pre-commit-encoding-check",
    "pre-commit-markdown-check",
)

MANAGED_HOOK_SIGNATURES: dict[str, tuple[tuple[str, ...], ...]] = {
    "pre-commit": (
        ("SPEC_KITTY_MANAGED_HOOK_SHIM=1",),
        (
            "Main pre-commit hook that orchestrates all pre-commit checks",
            "pre-commit-encoding-check",
            "pre-commit-agent-check",
        ),
    ),
    "commit-msg": (
        ("SPEC_KITTY_MANAGED_HOOK_SHIM=1",),
        (
            "commit-msg hook to enforce conventional commit messages via commitlint",
            "feat(doctrine): add markdown and commit quality gates",
        ),
    ),
    "pre-commit-agent-check": (
        (
            "Pre-commit hook to prevent committing agent directories",
            ".github/copilot",
        ),
    ),
    "pre-commit-encoding-check": (
        (
            "Pre-commit hook to validate UTF-8 encoding in markdown files",
            "spec-kitty validate-encoding --all --fix",
        ),
    ),
    "pre-commit-markdown-check": (
        (
            "Pre-commit hook to validate markdown style on staged files",
            "markdownlint-cli2",
            "SPEC_KITTY_TEST_MODE",
        ),
    ),
}


def _is_managed_hook_file(path: Path) -> bool:
    """Return True when *path* matches a known Spec Kitty-managed hook signature."""
    if not path.is_file():
        return False

    signatures = MANAGED_HOOK_SIGNATURES.get(path.name)
    if not signatures:
        return False

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False

    for signature in signatures:
        if all(marker in content for marker in signature):
            return True
    return False


@MigrationRegistry.register
class RetireGitHooksMigration(BaseMigration):
    """Remove known Spec Kitty-managed git hooks from .git/hooks."""

    migration_id = "2.0.0_retire_git_hooks"
    description = "Retire Spec Kitty-managed git hooks"
    target_version = "2.0.0"

    def detect(self, project_path: Path) -> bool:
        """Detect if this project still has managed Spec Kitty hooks."""
        hooks_dir = project_path / ".git" / "hooks"
        if not hooks_dir.is_dir():
            return False

        for hook_name in MANAGED_HOOK_NAMES:
            if _is_managed_hook_file(hooks_dir / hook_name):
                return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Always safe; missing .git/hooks simply yields a no-op migration."""
        if not project_path.exists():
            return False, "Project path does not exist"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Remove managed hooks and skip custom hooks with warnings."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        hooks_dir = project_path / ".git" / "hooks"
        if not hooks_dir.is_dir():
            changes.append("No .git/hooks directory found")
            return MigrationResult(success=True, changes_made=changes)

        removed_count = 0
        for hook_name in MANAGED_HOOK_NAMES:
            hook_path = hooks_dir / hook_name
            if not hook_path.exists():
                continue

            if not _is_managed_hook_file(hook_path):
                warnings.append(f"Skipped custom hook: {hook_name}")
                continue

            if dry_run:
                changes.append(f"Would remove managed hook: {hook_name}")
                continue

            try:
                hook_path.unlink()
                removed_count += 1
                changes.append(f"Removed managed hook: {hook_name}")
            except OSError as exc:
                errors.append(f"Failed to remove {hook_name}: {exc}")

        if not changes:
            changes.append("No managed git hooks found")

        success = len(errors) == 0
        if removed_count > 0 and not dry_run:
            changes.insert(0, f"Removed {removed_count} managed git hook(s)")
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )


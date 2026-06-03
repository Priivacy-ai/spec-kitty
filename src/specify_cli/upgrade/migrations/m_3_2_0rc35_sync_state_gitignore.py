"""Migration: repair local runtime ``.kittify`` git hygiene."""

from __future__ import annotations

import subprocess
from pathlib import Path

from specify_cli.gitignore_manager import GitignoreManager

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

_SYNC_STATE_ENTRY = ".kittify/sync-state.json"
_LOCAL_RUNTIME_TRACKED_PATHS = (
    ".kittify/charter/context-state.json",
    ".kittify/encoding-provenance/global.jsonl",
)


def _is_git_repo(project_path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(project_path), "rev-parse", "--is-inside-work-tree"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _is_tracked(project_path: Path, relative_path: str) -> bool:
    if not _is_git_repo(project_path):
        return False
    result = subprocess.run(
        ["git", "-C", str(project_path), "ls-files", "--error-unmatch", relative_path],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _untrack(project_path: Path, relative_path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(project_path), "rm", "--cached", "--", relative_path],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


@MigrationRegistry.register
class KittifyRuntimeGitHygieneMigration(BaseMigration):
    """Ignore sync state and untrack known local-runtime files."""

    migration_id = "3.2.0rc35_kittify_runtime_git_hygiene"
    description = "Repair local-runtime .kittify gitignore and tracked-file state"
    target_version = "3.2.0rc35"

    def detect(self, project_path: Path) -> bool:
        gitignore_path = project_path / ".gitignore"
        sync_entry_missing = (
            not gitignore_path.exists()
            or _SYNC_STATE_ENTRY not in gitignore_path.read_text(encoding="utf-8")
        )
        tracked_runtime = any(
            _is_tracked(project_path, path)
            for path in _LOCAL_RUNTIME_TRACKED_PATHS
        )
        return sync_entry_missing or tracked_runtime

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        if dry_run:
            tracked = [
                path
                for path in _LOCAL_RUNTIME_TRACKED_PATHS
                if _is_tracked(project_path, path)
            ]
            return MigrationResult(
                success=True,
                changes_made=[
                    f"Would add {_SYNC_STATE_ENTRY} to .gitignore",
                    *[f"Would untrack local runtime file: {path}" for path in tracked],
                ],
            )

        changes: list[str] = []
        errors: list[str] = []

        manager = GitignoreManager(project_path)
        modified = manager.ensure_entries([_SYNC_STATE_ENTRY])
        if modified:
            changes.append(f"Added {_SYNC_STATE_ENTRY} to .gitignore")
        else:
            changes.append(f"{_SYNC_STATE_ENTRY} already present in .gitignore")

        for path in _LOCAL_RUNTIME_TRACKED_PATHS:
            if not _is_tracked(project_path, path):
                continue
            if _untrack(project_path, path):
                changes.append(f"Untracked local runtime file: {path}")
            else:
                errors.append(f"Failed to untrack local runtime file: {path}")

        return MigrationResult(
            success=not errors,
            changes_made=changes,
            errors=errors,
        )

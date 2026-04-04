"""Migration: deploy profile-context command template to configured agents.

Adds the /spec-kitty.profile-context slash command to all configured agent
command directories, enabling agents to load specialist profiles for advisory
sessions.

Scope:
- Copies src/doctrine/templates/profile-context.md to each
  configured agent's command directory as spec-kitty.profile-context.md.
- Respects .kittify/config.yaml — only processes configured agents.
- Skips agent directories that do not exist on disk (respects user deletions).
- Idempotent: if the destination already contains identical content, skip.
  If the template was updated (content differs), overwrite.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project

_DEST_FILENAME = "spec-kitty.profile-context.md"


def _load_template() -> str | None:
    """Load profile-context.md from the doctrine package."""
    try:
        return files("doctrine").joinpath("templates", "profile-context.md").read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001, S110
        pass
    # Local repo fallback (development installs)
    fallback = Path(__file__).resolve().parents[3] / "doctrine" / "templates" / "profile-context.md"
    if fallback.is_file():
        return fallback.read_text(encoding="utf-8")
    return None


@MigrationRegistry.register
class ProfileContextDeploymentMigration(BaseMigration):
    """Deploy /spec-kitty.profile-context command template to configured agent dirs."""

    migration_id = "2.2.0_profile_context_deployment"
    description = "Deploy /spec-kitty.profile-context slash command to configured agents"
    target_version = "2.2.0"

    def detect(self, project_path: Path) -> bool:
        """Return True if any configured agent dir is missing the template."""
        for agent_root, subdir in get_agent_dirs_for_project(project_path):
            agent_dir = project_path / agent_root / subdir
            if agent_dir.exists() and not (agent_dir / _DEST_FILENAME).exists():
                return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
        """Always safe to apply — missing dirs are silently skipped."""
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Copy profile-context.md to every configured and present agent dir."""
        changes: list[str] = []
        errors: list[str] = []

        content = _load_template()
        if content is None:
            return MigrationResult(
                success=False,
                errors=["Cannot locate profile-context.md template in doctrine package"],
            )

        for agent_root, subdir in get_agent_dirs_for_project(project_path):
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.exists():
                continue  # Respect user deletion — do not recreate

            dest = agent_dir / _DEST_FILENAME

            # Idempotency: skip if content is already up-to-date
            if dest.exists() and dest.read_text(encoding="utf-8") == content:
                continue

            rel = str(dest.relative_to(project_path))
            if dry_run:
                changes.append(f"Would deploy {rel}")
                continue

            try:
                dest.write_text(content, encoding="utf-8")
                changes.append(f"Deployed {rel}")
            except OSError as exc:
                errors.append(f"Failed to deploy {rel}: {exc}")

        if not changes and not errors:
            changes.append(f"{_DEST_FILENAME} already up-to-date in all configured agent dirs")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
        )

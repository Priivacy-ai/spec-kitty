"""Migration 3.2.0: Update tasks-outline and tasks-packages to wps.yaml-based prompts.

Projects that ran spec-kitty upgrade before 3.2.0 have the old prompt-driven
command files for tasks-outline and tasks-packages. These instruct the LLM to
write tasks.md prose instead of wps.yaml. This migration detects and replaces them.

Detection: checks for the string "Create `tasks.md`" in any tasks-outline command
file. This string is unique to the pre-3.2.0 template and absent in the new version.

Idempotency: files already using the new wps.yaml instructions do not contain the
detection string and are left unchanged.

Schema reference: kitty-specs/069-planning-pipeline-integrity/wps_manifest_schema.py
(from WP02 of the same feature).
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project
from .m_2_1_3_restore_prompt_commands import (
    _agent_root_to_key,
    _compute_output_filename,
    _get_runtime_command_templates_dir,
    _render_full_prompt,
    _resolve_script_type,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# String present in old tasks-outline (pre-3.2.0), absent in new version.
_STALE_MARKER = "Create `tasks.md`"

_COMMANDS_TO_UPDATE = ("tasks-outline", "tasks-packages")


# ---------------------------------------------------------------------------
# Migration class
# ---------------------------------------------------------------------------


@MigrationRegistry.register
class UpdatePlanningTemplatesMigration(BaseMigration):
    """Replace pre-3.2.0 tasks-outline / tasks-packages with wps.yaml-based versions."""

    migration_id = "3.2.0_update_planning_templates"
    description = "Update tasks-outline and tasks-packages command files from prose tasks.md authoring to structured wps.yaml manifest authoring"
    target_version = "3.2.0"

    def detect(self, project_path: Path) -> bool:
        """Return True if any tasks-outline command file contains the stale marker.

        Iterates all configured agent directories. Returns True on the first file
        that contains _STALE_MARKER (pre-3.2.0 tasks.md instructions).

        Args:
            project_path: Root of the consumer project.

        Returns:
            True if a stale tasks-outline (or tasks-packages) file is found.
        """
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.is_dir():
                continue
            for command in _COMMANDS_TO_UPDATE:
                for candidate in agent_dir.glob(f"spec-kitty.{command}.*"):
                    try:
                        if _STALE_MARKER in candidate.read_text(encoding="utf-8"):
                            return True
                    except OSError:
                        continue
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check that runtime templates are available for rendering.

        Args:
            project_path: Root of the consumer project.

        Returns:
            (True, "") if templates are found; (False, reason) otherwise.
        """
        templates_dir = _get_runtime_command_templates_dir()
        if templates_dir is None:
            return (
                False,
                "Runtime command templates not found. Run 'spec-kitty upgrade' again after reinstalling spec-kitty-cli.",
            )
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Replace stale tasks-outline / tasks-packages with wps.yaml-based versions.

        Iterates configured agent directories, finds files containing the stale
        marker, and overwrites them with freshly-rendered template content.

        Idempotent: files that do not contain the stale marker are left untouched.

        Args:
            project_path: Root of the consumer project.
            dry_run:      When True, report what would change but write nothing.

        Returns:
            MigrationResult with changes_made, errors, and warnings.
        """
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        templates_dir = _get_runtime_command_templates_dir()
        if templates_dir is None:
            return MigrationResult(
                success=False,
                changes_made=changes,
                errors=["Runtime command templates not found — cannot update planning templates"],
                warnings=warnings,
            )

        script_type = _resolve_script_type()
        agent_dirs = get_agent_dirs_for_project(project_path)

        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.is_dir():
                continue

            agent_key = _agent_root_to_key(agent_root)
            if agent_key is None:
                logger.debug("Skipping unknown agent root %s", agent_root)
                continue

            for command in _COMMANDS_TO_UPDATE:
                template_path = templates_dir / f"{command}.md"
                if not template_path.is_file():
                    warnings.append(f"Template not found for command '{command}' in {templates_dir} — skipping")
                    continue

                # Find the stale file for this command in this agent dir
                stale_file: Path | None = None
                for candidate in agent_dir.glob(f"spec-kitty.{command}.*"):
                    try:
                        if _STALE_MARKER in candidate.read_text(encoding="utf-8"):
                            stale_file = candidate
                            break
                    except OSError:
                        continue

                if stale_file is None:
                    # No stale file — already up-to-date or not present; skip
                    continue

                # Compute the correct output filename for this agent
                output_filename = _compute_output_filename(command, agent_key)
                output_path = agent_dir / output_filename
                rel = str(output_path.relative_to(project_path))

                if dry_run:
                    changes.append(f"Would update: {rel}")
                    continue

                # Render the new template content
                rendered = _render_full_prompt(template_path, agent_key, script_type)
                if rendered is None:
                    errors.append(f"Failed to render {command} for {agent_key}")
                    continue

                # Write the updated content
                try:
                    output_path.write_text(rendered, encoding="utf-8")
                    changes.append(f"Updated: {rel}")
                except OSError as exc:
                    errors.append(f"Failed to write {rel}: {exc}")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

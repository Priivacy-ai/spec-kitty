"""Migration: Ensure workflow commands in agent prompts include --agent."""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project


@MigrationRegistry.register
class WorkflowAgentFlagMigration(BaseMigration):
    """Append --agent <name> to workflow commands in agent prompts."""

    migration_id = "0.11.3_workflow_agent_flag"
    description = "Ensure workflow commands in agent prompts include --agent"
    target_version = "0.11.3"

    AGENT_NAME_MAP = {
        ".github": "copilot",
        ".augment": "auggie",
        ".amazonq": "q",
    }

    TARGET_FILES = ("spec-kitty.implement.md", "spec-kitty.review.md")

    def _agent_name(self, agent_root: str) -> str:
        return self.AGENT_NAME_MAP.get(agent_root, agent_root.lstrip("."))

    def _update_workflow_lines(self, path: Path, agent_name: str, dry_run: bool) -> bool:
        if not path.exists():
            return False

        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        updated = False

        def _patch_line(line: str) -> str:
            nonlocal updated
            # Replace __AGENT__ placeholder with actual agent name
            if "__AGENT__" in line:
                updated = True
                line = line.replace("__AGENT__", agent_name)
            # Add --agent flag if missing
            if "spec-kitty agent workflow implement" in line and "--agent" not in line:
                updated = True
                return f"{line} --agent {agent_name}"
            if "spec-kitty agent workflow review" in line and "--agent" not in line:
                updated = True
                return f"{line} --agent {agent_name}"
            return line

        lines = [_patch_line(line) for line in lines]
        if updated and not dry_run:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return updated

    def detect(self, project_path: Path) -> bool:
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.exists():
                continue
            agent_name = self._agent_name(agent_root)
            for filename in self.TARGET_FILES:
                path = agent_dir / filename
                if not path.exists():
                    continue
                text = path.read_text(encoding="utf-8")
                for line in text.splitlines():
                    # Detect __AGENT__ placeholder that needs replacement
                    if "__AGENT__" in line:
                        return True
                    if "spec-kitty agent workflow implement" in line and "--agent" not in line:
                        return True
                    if "spec-kitty agent workflow review" in line and "--agent" not in line:
                        return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not (project_path / ".kittify").exists():
            return False, "No .kittify directory (not a spec-kitty project)"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.exists():
                continue
            agent_name = self._agent_name(agent_root)
            updated_count = 0
            for filename in self.TARGET_FILES:
                path = agent_dir / filename
                if self._update_workflow_lines(path, agent_name, dry_run):
                    updated_count += 1
            if updated_count:
                changes.append(f"Updated {updated_count} workflow prompts for {agent_name}")

        if not changes:
            warnings.append("No workflow prompts required updates")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

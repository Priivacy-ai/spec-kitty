"""Migration: Create skills manifest and empty skill roots for configured agents.

Pre-Phase-0 projects (those that have a config.yaml but no skills manifest)
gain a manifest and empty skill roots after running ``spec-kitty upgrade``.
Existing wrapper files are tracked in the manifest with correct hashes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class AgentSurfaceManifestMigration(BaseMigration):
    """Add skills manifest and empty skill roots for configured agents.

    This migration targets projects that were initialized before the agent
    skills infrastructure was introduced.  It:

    1. Resolves skill root directories for the configured agents.
    2. Creates empty skill roots with ``.gitkeep`` markers.
    3. Builds a skills manifest that tracks both the new markers and any
       existing wrapper files.
    """

    migration_id = "2_1_0_agent_surface_manifest"
    description = "Add skills manifest and empty skill roots for configured agents"
    target_version = "2.1.0"
    min_version = None  # Applicable to any previous version

    def detect(self, project_path: Path) -> bool:
        """Return ``True`` when config.yaml exists but no skills manifest."""
        config_exists = (project_path / ".kittify" / "config.yaml").exists()
        manifest_exists = (
            project_path / ".kittify" / "agent-surfaces" / "skills-manifest.yaml"
        ).exists()
        return config_exists and not manifest_exists

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Migration is always safe and idempotent."""
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Create manifest from current state and add empty skill roots."""
        from specify_cli.agent_utils.directories import get_agent_dirs_for_project
        from specify_cli.core.agent_config import get_configured_agents
        from specify_cli.skills.manifest import (
            ManagedFile,
            SkillsManifest,
            compute_file_hash,
            write_manifest,
        )
        from specify_cli.skills.roots import resolve_skill_roots

        changes: list[str] = []

        # 1. Read configured agents
        agents = get_configured_agents(project_path)
        if not agents:
            return MigrationResult(
                success=True,
                changes_made=["No agents configured, skipping manifest creation"],
            )

        # 2. Resolve skill roots in auto mode
        resolved_roots = resolve_skill_roots(agents, mode="auto")

        # 3. Create empty skill roots with .gitkeep markers
        for root in resolved_roots:
            root_path = project_path / root
            gitkeep = root_path / ".gitkeep"
            if not dry_run:
                root_path.mkdir(parents=True, exist_ok=True)
                if not gitkeep.exists():
                    gitkeep.write_text("", encoding="utf-8")
                    changes.append(f"Created skill root: {root}")
                else:
                    changes.append(f"Skill root already exists: {root}")
            else:
                changes.append(f"Would create skill root: {root}")

        # 4. Build manifest from existing state
        managed_files: list[ManagedFile] = []

        # Track skill root markers
        for root in resolved_roots:
            gitkeep = project_path / root / ".gitkeep"
            if not dry_run and gitkeep.exists():
                managed_files.append(
                    ManagedFile(
                        path=f"{root}.gitkeep",
                        sha256=compute_file_hash(gitkeep),
                        file_type="skill_root_marker",
                    )
                )

        # Track existing wrapper files
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_root, subdir in agent_dirs:
            wrapper_dir = project_path / agent_root / subdir
            if wrapper_dir.exists():
                for f in sorted(wrapper_dir.iterdir()):
                    if f.is_file() and f.name.startswith("spec-kitty."):
                        managed_files.append(
                            ManagedFile(
                                path=str(f.relative_to(project_path)),
                                sha256=compute_file_hash(f),
                                file_type="wrapper",
                            )
                        )
                        changes.append(f"Tracked wrapper: {f.relative_to(project_path)}")

        # 5. Write manifest
        if not dry_run:
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            manifest = SkillsManifest(
                spec_kitty_version="2.1.0",
                created_at=now_iso,
                updated_at=now_iso,
                skills_mode="auto",
                selected_agents=agents,
                installed_skill_roots=resolved_roots,
                managed_files=managed_files,
            )
            write_manifest(project_path, manifest)
            changes.append(
                f"Created skills manifest with {len(resolved_roots)} skill root(s) "
                f"and {len(managed_files)} tracked file(s)"
            )
        else:
            changes.append(
                f"Would create skills manifest with {len(resolved_roots)} skill root(s)"
            )

        return MigrationResult(success=True, changes_made=changes)

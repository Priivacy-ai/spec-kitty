"""
Manifest system for spec-kitty file verification.
This module generates and checks expected files based on the mission context.
"""

from pathlib import Path
import subprocess

from specify_cli.constitution.mission_paths import MissionType, ProjectMissionPaths


class FileManifest:
    """Manages the expected file manifest for spec-kitty missions.

    The mission context must be provided explicitly via *mission_key*.
    There is no project-level fallback -- callers should resolve the
    mission from mission-level ``meta.json`` before constructing a
    manifest.
    """

    def __init__(self, kittify_dir: Path, *, mission_key: str | None = None):
        self.kittify_dir = kittify_dir
        self.mission_dir = (
            ProjectMissionPaths.from_kittify(kittify_dir).mission_dir_for(
                MissionType.with_name(mission_key)
            )
            if mission_key
            else None
        )

    def get_expected_files(self) -> dict[str, list[str]]:
        """
        Get a categorized list of expected files for the active mission.

        Returns:
            Dict with categories as keys and file paths as values
        """
        if not self.mission_dir or not self.mission_dir.exists():
            return {}

        manifest = {
            "commands": [],
            "templates": [],
            "scripts": [],
            "mission_files": []
        }

        # Mission config file
        mission_yaml = self.mission_dir / "mission.yaml"
        if mission_yaml.exists():
            manifest["mission_files"].append(str(mission_yaml.relative_to(self.kittify_dir)))

        # Commands
        commands_dir = self.mission_dir / "command-templates"
        if commands_dir.exists():
            for cmd_file in commands_dir.glob("*.md"):
                manifest["commands"].append(str(cmd_file.relative_to(self.kittify_dir)))

        # Templates
        templates_dir = self.mission_dir / "templates"
        if templates_dir.exists():
            for tmpl_file in templates_dir.glob("*.md"):
                manifest["templates"].append(str(tmpl_file.relative_to(self.kittify_dir)))

        # Scripts referenced in commands
        manifest["scripts"] = self._get_referenced_scripts()

        return manifest

    def _get_referenced_scripts(self) -> list[str]:
        """Extract script references from command files, filtered by platform."""
        import platform
        scripts = set()

        if not self.mission_dir:
            return []

        commands_dir = self.mission_dir / "command-templates"
        if not commands_dir.exists():
            return []

        # Determine which script type to look for based on platform
        is_windows = platform.system() == 'Windows'
        script_key = 'ps:' if is_windows else 'sh:'

        # Parse command files for script references
        for cmd_file in commands_dir.glob("*.md"):
            content = cmd_file.read_text(encoding='utf-8-sig')
            lines = content.split('\n')

            # Look for script references in YAML frontmatter
            in_frontmatter = False
            for line in lines:
                if line.strip() == '---':
                    in_frontmatter = not in_frontmatter
                    if not in_frontmatter and not in_frontmatter:
                        break  # End of frontmatter
                elif in_frontmatter:
                    # Only check for scripts relevant to this platform
                    if script_key in line:
                        # Extract script path
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            script_line = parts[1].strip().strip('"').strip("'")
                            # Extract just the script path, not the arguments
                            # Script path is the first part before any spaces or arguments
                            script_parts = script_line.split()
                            if script_parts:
                                script_path = script_parts[0]
                                # Only include actual .kittify/scripts/ files
                                # Skip CLI commands (spec-kitty, git, python, etc.)
                                if script_path.startswith('.kittify/scripts/'):
                                    script_path = script_path.replace('.kittify/', '', 1)
                                    scripts.add(script_path)

        return sorted(scripts)

    def check_files(self) -> dict[str, dict[str, str]]:
        """
        Check which expected files exist and which are missing.

        Returns:
            Dict with 'present', 'missing', and 'extra' keys
        """
        expected = self.get_expected_files()
        result = {
            "present": {},
            "missing": {},
            "modified": {},
            "extra": []
        }

        # Check each category
        for category, files in expected.items():
            for file_path in files:
                full_path = self.kittify_dir / file_path
                if full_path.exists():
                    result["present"][file_path] = category
                else:
                    result["missing"][file_path] = category

        # TODO: Check for modifications using git or checksums
        # TODO: Find extra files not in manifest

        return result


class WorktreeStatus:
    """Manages worktree and mission branch status."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def get_all_missions(self) -> list[str]:
        """Get all mission branches and directories."""
        missions = set()

        # Get missions from branches
        try:
            result = subprocess.run(
                ["git", "branch", "-a"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True
            )
            for line in result.stdout.split('\n'):
                line = line.strip().replace('* ', '')
                # Match mission branch pattern (###-name)
                if line and not line.startswith('remotes/'):
                    parts = line.split('/')
                    branch = parts[-1]
                    if branch and branch[0].isdigit() and '-' in branch:
                        missions.add(branch)
        except subprocess.CalledProcessError:
            pass

        # Get missions from kitty-specs
        kitty_specs = self.repo_root / "kitty-specs"
        if kitty_specs.exists():
            for mission_dir in kitty_specs.iterdir():
                if mission_dir.is_dir() and mission_dir.name[0].isdigit() and '-' in mission_dir.name:
                    missions.add(mission_dir.name)

        return sorted(missions)

    def get_mission_status(self, mission_slug: str) -> dict[str, any]:
        """Get comprehensive status for a mission."""
        status = {
            "name": mission_slug,
            "branch_exists": False,
            "branch_merged": False,
            "worktree_exists": False,
            "worktree_path": None,
            "artifacts_in_main": [],
            "artifacts_in_worktree": [],
            "last_activity": None,
            "state": "unknown"  # not_started, in_development, ready_to_merge, merged, abandoned
        }

        # Check if branch exists
        try:
            result = subprocess.run(
                ["git", "show-ref", f"refs/heads/{mission_slug}"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            status["branch_exists"] = result.returncode == 0
        except subprocess.CalledProcessError:
            pass

        # Check if merged
        if status["branch_exists"]:
            try:
                from specify_cli.core.git_ops import resolve_primary_branch
                primary = resolve_primary_branch(self.repo_root)
                result = subprocess.run(
                    ["git", "branch", "--merged", primary],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=True
                )
                status["branch_merged"] = mission_slug in result.stdout
            except subprocess.CalledProcessError:
                pass

        # Check worktree
        worktree_path = self.repo_root / ".worktrees" / mission_slug
        if worktree_path.exists():
            status["worktree_exists"] = True
            status["worktree_path"] = str(worktree_path)

        # Check artifacts in main
        main_artifacts_path = self.repo_root / "kitty-specs" / mission_slug
        if main_artifacts_path.exists():
            for artifact in main_artifacts_path.glob("*.md"):
                status["artifacts_in_main"].append(artifact.name)

        # Check artifacts in worktree
        if status["worktree_exists"]:
            worktree_artifacts_path = worktree_path / "kitty-specs" / mission_slug
            if worktree_artifacts_path.exists():
                for artifact in worktree_artifacts_path.glob("*.md"):
                    status["artifacts_in_worktree"].append(artifact.name)

        # Determine state
        if not status["branch_exists"] and not status["artifacts_in_main"]:
            status["state"] = "not_started"
        elif status["branch_merged"] and status["artifacts_in_main"]:
            status["state"] = "merged"
        elif status["worktree_exists"] or status["artifacts_in_worktree"]:
            status["state"] = "in_development"
        elif status["branch_exists"] and not status["worktree_exists"]:
            status["state"] = "ready_to_merge"
        elif not status["branch_exists"] and status["artifacts_in_main"]:
            status["state"] = "merged"  # Branch was deleted after merge

        return status

    def get_worktree_summary(self) -> dict[str, int]:
        """Get summary counts of worktree states."""
        missions = self.get_all_missions()
        summary = {
            "total_missions": len(missions),
            "active_worktrees": 0,
            "merged_missions": 0,
            "in_development": 0,
            "not_started": 0
        }

        for mission_slug in missions:
            status = self.get_mission_status(mission_slug)
            if status["worktree_exists"]:
                summary["active_worktrees"] += 1
            if status["state"] == "merged":
                summary["merged_missions"] += 1
            elif status["state"] == "in_development":
                summary["in_development"] += 1
            elif status["state"] == "not_started":
                summary["not_started"] += 1

        return summary

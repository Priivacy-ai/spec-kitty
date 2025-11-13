"""
Manifest system for spec-kitty file verification.
This module generates and checks expected files based on the active mission.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import yaml
import subprocess


class FileManifest:
    """Manages the expected file manifest for spec-kitty missions."""

    def __init__(self, kittify_dir: Path):
        self.kittify_dir = kittify_dir
        self.active_mission = self._detect_active_mission()
        self.mission_dir = kittify_dir / "missions" / self.active_mission if self.active_mission else None

    def _detect_active_mission(self) -> Optional[str]:
        """Detect the active mission from the symlink or file."""
        active_mission_path = self.kittify_dir / "active-mission"
        if active_mission_path.exists():
            if active_mission_path.is_symlink():
                # It's a symlink, resolve it
                target = active_mission_path.resolve()
                return target.name
            elif active_mission_path.is_file():
                # It's a file with the mission name
                return active_mission_path.read_text().strip()

        # Default to software-dev if no active mission
        return "software-dev"

    def get_expected_files(self) -> Dict[str, List[str]]:
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
            "constitution": [],
            "mission_files": []
        }

        # Mission config file
        mission_yaml = self.mission_dir / "mission.yaml"
        if mission_yaml.exists():
            manifest["mission_files"].append(str(mission_yaml.relative_to(self.kittify_dir)))

        # Commands
        commands_dir = self.mission_dir / "commands"
        if commands_dir.exists():
            for cmd_file in commands_dir.glob("*.md"):
                manifest["commands"].append(str(cmd_file.relative_to(self.kittify_dir)))

        # Templates
        templates_dir = self.mission_dir / "templates"
        if templates_dir.exists():
            for tmpl_file in templates_dir.glob("*.md"):
                manifest["templates"].append(str(tmpl_file.relative_to(self.kittify_dir)))

        # Constitution
        constitution_dir = self.mission_dir / "constitution"
        if constitution_dir.exists():
            for const_file in constitution_dir.glob("*.md"):
                manifest["constitution"].append(str(const_file.relative_to(self.kittify_dir)))

        # Scripts referenced in commands
        manifest["scripts"] = self._get_referenced_scripts()

        return manifest

    def _get_referenced_scripts(self) -> List[str]:
        """Extract script references from command files, filtered by platform."""
        import platform
        scripts = set()

        if not self.mission_dir:
            return []

        commands_dir = self.mission_dir / "commands"
        if not commands_dir.exists():
            return []

        # Determine which script type to look for based on platform
        is_windows = platform.system() == 'Windows'
        script_key = 'ps:' if is_windows else 'sh:'

        # Parse command files for script references
        for cmd_file in commands_dir.glob("*.md"):
            content = cmd_file.read_text()
            lines = content.split('\n')

            # Look for script references in YAML frontmatter
            in_frontmatter = False
            for line in lines:
                if line.strip() == '---':
                    in_frontmatter = not in_frontmatter
                    if not in_frontmatter and in_frontmatter == False:
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
                                if script_path.startswith('.kittify/'):
                                    script_path = script_path.replace('.kittify/', '')
                                scripts.add(script_path)

        return sorted(list(scripts))

    def check_files(self) -> Dict[str, Dict[str, str]]:
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
    """Manages worktree and feature branch status."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def get_all_features(self) -> List[str]:
        """Get all feature branches and directories."""
        features = set()

        # Get features from branches
        try:
            result = subprocess.run(
                ["git", "branch", "-a"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            for line in result.stdout.split('\n'):
                line = line.strip().replace('* ', '')
                # Match feature branch pattern (###-name)
                if line and not line.startswith('remotes/'):
                    parts = line.split('/')
                    branch = parts[-1]
                    if branch and branch[0].isdigit() and '-' in branch:
                        features.add(branch)
        except subprocess.CalledProcessError:
            pass

        # Get features from kitty-specs
        kitty_specs = self.repo_root / "kitty-specs"
        if kitty_specs.exists():
            for feature_dir in kitty_specs.iterdir():
                if feature_dir.is_dir() and feature_dir.name[0].isdigit() and '-' in feature_dir.name:
                    features.add(feature_dir.name)

        return sorted(list(features))

    def get_feature_status(self, feature: str) -> Dict[str, any]:
        """Get comprehensive status for a feature."""
        status = {
            "name": feature,
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
                ["git", "show-ref", f"refs/heads/{feature}"],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            status["branch_exists"] = result.returncode == 0
        except subprocess.CalledProcessError:
            pass

        # Check if merged
        if status["branch_exists"]:
            try:
                result = subprocess.run(
                    ["git", "branch", "--merged", "main"],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=True
                )
                status["branch_merged"] = feature in result.stdout
            except subprocess.CalledProcessError:
                pass

        # Check worktree
        worktree_path = self.repo_root / ".worktrees" / feature
        if worktree_path.exists():
            status["worktree_exists"] = True
            status["worktree_path"] = str(worktree_path)

        # Check artifacts in main
        main_artifacts_path = self.repo_root / "kitty-specs" / feature
        if main_artifacts_path.exists():
            for artifact in main_artifacts_path.glob("*.md"):
                status["artifacts_in_main"].append(artifact.name)

        # Check artifacts in worktree
        if status["worktree_exists"]:
            worktree_artifacts_path = worktree_path / "kitty-specs" / feature
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

    def get_worktree_summary(self) -> Dict[str, int]:
        """Get summary counts of worktree states."""
        features = self.get_all_features()
        summary = {
            "total_features": len(features),
            "active_worktrees": 0,
            "merged_features": 0,
            "in_development": 0,
            "not_started": 0
        }

        for feature in features:
            status = self.get_feature_status(feature)
            if status["worktree_exists"]:
                summary["active_worktrees"] += 1
            if status["state"] == "merged":
                summary["merged_features"] += 1
            elif status["state"] == "in_development":
                summary["in_development"] += 1
            elif status["state"] == "not_started":
                summary["not_started"] += 1

        return summary
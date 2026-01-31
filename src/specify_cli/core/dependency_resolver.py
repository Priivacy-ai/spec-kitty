"""Dependency resolution and merge strategy recommendation.

This module provides logic to detect when multi-parent dependencies should be
merged to main before implementing a dependent WP, avoiding auto-merge conflicts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from specify_cli.frontmatter import read_frontmatter


@dataclass
class DependencyStatus:
    """Status of a WP's dependencies.

    Attributes:
        wp_id: Work package ID (e.g., "WP04")
        dependencies: List of dependency WP IDs (e.g., ["WP01", "WP02", "WP03"])
        all_done: True if all dependencies in "done" lane
        lanes: Dict mapping dependency WP ID to lane status
        is_multi_parent: True if more than one dependency
    """

    wp_id: str
    dependencies: list[str]
    all_done: bool
    lanes: dict[str, str]
    is_multi_parent: bool

    @property
    def should_suggest_merge_first(self) -> bool:
        """Return True if we should suggest merging dependencies before implement.

        Logic:
        - Multi-parent (2+ dependencies) AND
        - All dependencies in "done" lane
        → Suggest merging to main first
        """
        return self.is_multi_parent and self.all_done

    def get_recommendation(self) -> str:
        """Get recommended workflow for implementing this WP.

        Returns:
            Recommendation string (user/agent guidance)
        """
        if not self.dependencies:
            return "No dependencies - implement directly from main"

        if not self.all_done:
            not_done = [dep for dep, lane in self.lanes.items() if lane != "done"]
            return f"Cannot implement - dependencies not complete: {', '.join(not_done)}"

        if len(self.dependencies) == 1:
            dep = self.dependencies[0]
            return f"Single dependency ({dep}) - use --base {dep}"

        # Multi-parent, all done
        deps_str = ", ".join(self.dependencies)
        return (
            f"Multi-parent dependencies ({deps_str}) all done.\n"
            f"\n"
            f"RECOMMENDED: Merge dependencies to main first (avoids conflicts)\n"
            f"  1. spec-kitty merge --feature <feature-slug>\n"
            f"  2. spec-kitty implement {self.wp_id}\n"
            f"\n"
            f"ALTERNATIVE: Attempt auto-merge (may conflict)\n"
            f"  spec-kitty implement {self.wp_id} --force\n"
            f"\n"
            f"Auto-merge works if WPs don't conflict on shared files\n"
            f"(.gitignore, package.json, etc.)"
        )


def check_dependency_status(
    feature_dir: Path, wp_id: str, dependencies: list[str]
) -> DependencyStatus:
    """Check status of a WP's dependencies.

    Args:
        feature_dir: Path to feature directory (kitty-specs/###-feature/)
        wp_id: Work package ID to check (e.g., "WP04")
        dependencies: List of dependency WP IDs (e.g., ["WP01", "WP02", "WP03"])

    Returns:
        DependencyStatus with analysis and recommendation
    """
    tasks_dir = feature_dir / "tasks"
    lanes = {}

    # Read lane status for each dependency
    for dep_id in dependencies:
        # Find WP file (may have slug suffix)
        wp_files = list(tasks_dir.glob(f"{dep_id}-*.md"))
        if not wp_files:
            # Dependency file not found - cannot determine status
            lanes[dep_id] = "unknown"
            continue

        wp_file = wp_files[0]
        try:
            frontmatter, _ = read_frontmatter(wp_file)
            lanes[dep_id] = frontmatter.get("lane", "unknown")
        except Exception:
            lanes[dep_id] = "unknown"

    # Determine if all done
    all_done = all(lane == "done" for lane in lanes.values())

    return DependencyStatus(
        wp_id=wp_id,
        dependencies=dependencies,
        all_done=all_done,
        lanes=lanes,
        is_multi_parent=len(dependencies) > 1,
    )


def predict_merge_conflicts(
    repo_root: Path, branches: list[str], target: str = "main"
) -> dict[str, list[str]]:
    """Predict which files will conflict when merging branches.

    Uses git merge-tree to simulate merge without touching working directory.

    Args:
        repo_root: Repository root path
        branches: List of branches to merge (e.g., ["WP01", "WP02", "WP03"])
        target: Target branch to merge into (default: "main")

    Returns:
        Dict mapping file paths to list of conflicting branches
        Example: {".gitignore": ["WP01", "WP02", "WP03"]}
    """
    import subprocess

    conflicts = {}

    # Check each branch against target
    for branch in branches:
        try:
            # git merge-tree: simulate merge without touching working tree
            result = subprocess.run(
                ["git", "merge-tree", target, branch],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )

            # Parse output for conflict markers
            if result.returncode != 0 or "<<<<<<<" in result.stdout:
                # Has conflicts - parse which files
                for line in result.stdout.split("\n"):
                    if line.startswith("CONFLICT"):
                        # Example: "CONFLICT (add/add): Merge conflict in .gitignore"
                        if " in " in line:
                            file_path = line.split(" in ")[-1].strip()
                            if file_path not in conflicts:
                                conflicts[file_path] = []
                            conflicts[file_path].append(branch)

        except Exception:
            # merge-tree failed or not available - skip prediction
            pass

    return conflicts


def get_merge_strategy_recommendation(status: DependencyStatus) -> dict:
    """Get recommended merge strategy for dependencies.

    Args:
        status: DependencyStatus from check_dependency_status()

    Returns:
        Dict with recommendation details:
        {
            "strategy": "merge_first" | "auto_merge" | "use_base" | "wait",
            "reason": "...",
            "command": "...",
            "warnings": [...]
        }
    """
    if not status.dependencies:
        return {
            "strategy": "no_dependencies",
            "reason": "No dependencies to resolve",
            "command": f"spec-kitty implement {status.wp_id}",
            "warnings": [],
        }

    if not status.all_done:
        not_done = [dep for dep, lane in status.lanes.items() if lane != "done"]
        return {
            "strategy": "wait",
            "reason": f"Dependencies not complete: {', '.join(not_done)}",
            "command": None,
            "warnings": [f"Complete {', '.join(not_done)} before implementing {status.wp_id}"],
        }

    if len(status.dependencies) == 1:
        dep = status.dependencies[0]
        return {
            "strategy": "use_base",
            "reason": f"Single dependency ({dep}) - use --base flag",
            "command": f"spec-kitty implement {status.wp_id} --base {dep}",
            "warnings": [],
        }

    # Multi-parent, all done
    return {
        "strategy": "merge_first",
        "reason": f"Multi-parent dependencies ({', '.join(status.dependencies)}) all done",
        "command": "spec-kitty merge --feature <feature-slug>",
        "warnings": [
            "Auto-merge may conflict on shared files (.gitignore, package.json)",
            "Merging dependencies to main first is safer",
        ],
    }

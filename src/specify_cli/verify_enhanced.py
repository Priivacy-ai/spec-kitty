"""
Enhanced verify_setup implementation for spec-kitty.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .manifest import FileManifest, WorktreeStatus


def run_enhanced_verify(
    repo_root: Path,
    project_root: Path,
    cwd: Path,
    feature: Optional[str],
    json_output: bool,
    check_files: bool,
    console: Console
) -> Dict:
    """
    Run the enhanced verification with manifest checking and worktree status.

    Returns a dict suitable for JSON output if needed.
    """
    output_data = {
        "environment": {},
        "feature_detection": {},
        "worktree_status": {},
        "file_integrity": {},
        "feature_analysis": {},
        "recommendations": []
    }

    # Initialize helpers
    kittify_dir = project_root / ".kittify"
    manifest = FileManifest(kittify_dir)
    worktree_status = WorktreeStatus(repo_root)

    # 1. Environment Information
    in_worktree = '.worktrees' in str(cwd)

    try:
        current_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
    except subprocess.CalledProcessError:
        current_branch = None

    output_data["environment"] = {
        "working_directory": str(cwd),
        "repo_root": str(repo_root),
        "project_root": str(project_root),
        "in_worktree": in_worktree,
        "current_branch": current_branch,
        "active_mission": manifest.active_mission
    }

    if not json_output:
        console.print("\n[bold]System Integrity Check[/bold]\n")

        # Environment section
        console.print("[cyan]1. Environment[/cyan]")
        console.print(f"   Working directory: {cwd}")
        console.print(f"   Repository root: {repo_root}")

        if in_worktree:
            console.print(f"   [green]✓[/green] In worktree")
        else:
            console.print(f"   [dim]○[/dim] Not in worktree")

        if current_branch:
            console.print(f"   Current branch: {current_branch}")
            if current_branch == "main":
                console.print(f"   [yellow]⚠[/yellow] On main branch")
        else:
            console.print(f"   [yellow]⚠[/yellow] Could not detect branch")

    # 2. File Integrity Check
    if check_files:
        file_check = manifest.check_files()
        expected_files = manifest.get_expected_files()

        total_expected = sum(len(files) for files in expected_files.values())
        total_present = len(file_check["present"])
        total_missing = len(file_check["missing"])

        output_data["file_integrity"] = {
            "active_mission": manifest.active_mission,
            "total_expected": total_expected,
            "total_present": total_present,
            "total_missing": total_missing,
            "missing_files": file_check["missing"],
            "categories": {}
        }

        # Count by category
        for category, files in expected_files.items():
            present_in_category = sum(1 for f in files if f in file_check["present"])
            output_data["file_integrity"]["categories"][category] = {
                "expected": len(files),
                "present": present_in_category,
                "missing": len(files) - present_in_category
            }

        if not json_output:
            console.print("\n[cyan]2. Mission File Integrity[/cyan]")
            console.print(f"   Active mission: {manifest.active_mission}")

            if total_missing == 0:
                console.print(f"   [green]✓[/green] All {total_expected} expected files present")
            else:
                console.print(f"   [yellow]⚠[/yellow] {total_missing} of {total_expected} files missing")

                # Show missing by category
                for category in ["commands", "templates", "scripts"]:
                    cat_missing = [f for f, c in file_check["missing"].items() if c == category]
                    if cat_missing:
                        console.print(f"   Missing {category}:")
                        for file in cat_missing[:3]:  # Show first 3
                            console.print(f"     - {file}")
                        if len(cat_missing) > 3:
                            console.print(f"     ... and {len(cat_missing) - 3} more")

    # 3. Worktree Status Overview
    worktree_summary = worktree_status.get_worktree_summary()
    output_data["worktree_status"] = worktree_summary

    if not json_output:
        console.print("\n[cyan]3. Worktree Overview[/cyan]")
        console.print(f"   Total features: {worktree_summary['total_features']}")
        console.print(f"   Active worktrees: {worktree_summary['active_worktrees']}")
        console.print(f"   Merged features: {worktree_summary['merged_features']}")
        console.print(f"   In development: {worktree_summary['in_development']}")

    # 4. Feature Detection and Analysis
    try:
        from .acceptance import detect_feature_slug, AcceptanceError
        feature_slug = (feature or detect_feature_slug(repo_root, cwd=cwd)).strip()

        output_data["feature_detection"] = {
            "detected": True,
            "feature": feature_slug
        }

        # Get detailed status for this feature
        feature_status = worktree_status.get_feature_status(feature_slug)
        output_data["feature_analysis"] = feature_status

        if not json_output:
            console.print("\n[cyan]4. Current Feature Status[/cyan]")
            console.print(f"   Feature: {feature_slug}")
            console.print(f"   State: {feature_status['state'].upper()}")

            # Status indicators
            if feature_status["branch_exists"]:
                status_text = "merged" if feature_status["branch_merged"] else "active"
                console.print(f"   [green]✓[/green] Branch exists ({status_text})")
            else:
                console.print(f"   [dim]○[/dim] No branch")

            if feature_status["worktree_exists"]:
                console.print(f"   [green]✓[/green] Worktree at: {feature_status['worktree_path']}")
            else:
                console.print(f"   [dim]○[/dim] No worktree")

            # Artifacts
            if feature_status["artifacts_in_main"]:
                console.print(f"   Artifacts in main: {', '.join(feature_status['artifacts_in_main'])}")
            if feature_status["artifacts_in_worktree"]:
                console.print(f"   Artifacts in worktree: {', '.join(feature_status['artifacts_in_worktree'])}")

            # State-based observations
            if feature_status["state"] == "merged":
                console.print("   [green]✓[/green] Feature appears to be merged")
            elif feature_status["state"] == "in_development":
                console.print("   [blue]●[/blue] Feature is in active development")
            elif feature_status["state"] == "not_started":
                console.print("   [dim]○[/dim] Feature not yet started")

    except AcceptanceError as exc:
        output_data["feature_detection"] = {
            "detected": False,
            "error": str(exc)
        }

        if not json_output:
            console.print("\n[cyan]4. Feature Detection[/cyan]")
            console.print(f"   [yellow]⚠[/yellow] Could not detect feature: {exc}")

    # 5. All Features Status Table
    all_features = worktree_status.get_all_features()

    if not json_output and all_features:
        console.print("\n[cyan]5. All Features Status[/cyan]")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Feature", style="cyan")
        table.add_column("State", style="white")
        table.add_column("Branch", style="white")
        table.add_column("Worktree", style="white")
        table.add_column("Artifacts", style="white")

        for feat in all_features[:10]:  # Show first 10
            feat_status = worktree_status.get_feature_status(feat)

            # Determine display values
            state_display = {
                "merged": "[green]MERGED[/green]",
                "in_development": "[yellow]ACTIVE[/yellow]",
                "ready_to_merge": "[blue]READY[/blue]",
                "not_started": "[dim]NOT STARTED[/dim]",
                "unknown": "[dim]?[/dim]"
            }.get(feat_status["state"], feat_status["state"])

            branch_display = "✓" if feat_status["branch_exists"] else "-"
            if feat_status["branch_merged"]:
                branch_display = "merged"

            worktree_display = "✓" if feat_status["worktree_exists"] else "-"

            artifact_count = len(feat_status["artifacts_in_main"]) + len(feat_status["artifacts_in_worktree"])
            artifacts_display = str(artifact_count) if artifact_count > 0 else "-"

            table.add_row(
                feat,
                state_display,
                branch_display,
                worktree_display,
                artifacts_display
            )

        console.print(table)

        if len(all_features) > 10:
            console.print(f"   [dim]... and {len(all_features) - 10} more features[/dim]")

    # 6. Observations (not recommendations)
    observations = []

    if current_branch == "main" and in_worktree:
        observations.append("Unusual: In worktree but on main branch")

    if output_data.get("feature_analysis", {}).get("state") == "in_development":
        if not output_data["feature_analysis"].get("worktree_exists"):
            observations.append(f"Feature {feature_slug} has no worktree but has development artifacts")

    if total_missing > 0 and check_files:
        observations.append(f"Mission integrity: {total_missing} expected files not found")

    output_data["observations"] = observations

    if not json_output and observations:
        console.print("\n[cyan]6. Observations[/cyan]")
        for obs in observations:
            console.print(f"   • {obs}")

    # Final summary
    if not json_output:
        console.print("\n[bold green]✓ Verification complete[/bold green]\n")

    return output_data
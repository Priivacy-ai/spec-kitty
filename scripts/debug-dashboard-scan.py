#!/usr/bin/env python3
"""Debug script to test dashboard mission scanning."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from specify_cli.dashboard.scanner import scan_all_missions, gather_mission_paths

def main():
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1]).resolve()
    else:
        project_dir = Path.cwd()

    print(f"Scanning project directory: {project_dir}")
    print()

    # Test gather_mission_paths
    print("=== Mission Paths ===")
    mission_paths = gather_mission_paths(project_dir)
    if not mission_paths:
        print("  No missions found!")
        print()
        print("Checking directories:")
        print(f"  Main specs: {project_dir / 'kitty-specs'} exists: {(project_dir / 'kitty-specs').exists()}")
        print(f"  Worktrees: {project_dir / '.worktrees'} exists: {(project_dir / '.worktrees').exists()}")

        if (project_dir / '.worktrees').exists():
            for wt_dir in (project_dir / '.worktrees').iterdir():
                if wt_dir.is_dir():
                    wt_specs = wt_dir / 'kitty-specs'
                    print(f"    {wt_dir.name}/kitty-specs exists: {wt_specs.exists()}")
                    if wt_specs.exists():
                        for mission_dir in wt_specs.iterdir():
                            if mission_dir.is_dir():
                                print(f"      Mission: {mission_dir.name}")
    else:
        for mission_id, mission_path in mission_paths.items():
            print(f"  {mission_id}: {mission_path}")
    print()

    # Test scan_all_missions
    print("=== Scanned Missions ===")
    missions = scan_all_missions(project_dir)
    if not missions:
        print("  No missions scanned!")
    else:
        for mission in missions:
            print(f"  ID: {mission['id']}")
            print(f"    Name: {mission['name']}")
            print(f"    Path: {mission['path']}")
            print(f"    Artifacts: {mission['artifacts']}")
            print(f"    Workflow: {mission['workflow']}")
            print(f"    Kanban: {mission['kanban_stats']}")
            print()

if __name__ == "__main__":
    main()

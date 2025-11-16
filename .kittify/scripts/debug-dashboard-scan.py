#!/usr/bin/env python3
"""Debug script to test dashboard feature scanning."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from specify_cli.dashboard.scanner import scan_all_features, gather_feature_paths

def main():
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1]).resolve()
    else:
        project_dir = Path.cwd()

    print(f"Scanning project directory: {project_dir}")
    print()

    # Test gather_feature_paths
    print("=== Feature Paths ===")
    feature_paths = gather_feature_paths(project_dir)
    if not feature_paths:
        print("  No features found!")
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
                        for feat_dir in wt_specs.iterdir():
                            if feat_dir.is_dir():
                                print(f"      Feature: {feat_dir.name}")
    else:
        for feature_id, feature_path in feature_paths.items():
            print(f"  {feature_id}: {feature_path}")
    print()

    # Test scan_all_features
    print("=== Scanned Features ===")
    features = scan_all_features(project_dir)
    if not features:
        print("  No features scanned!")
    else:
        for feature in features:
            print(f"  ID: {feature['id']}")
            print(f"    Name: {feature['name']}")
            print(f"    Path: {feature['path']}")
            print(f"    Artifacts: {feature['artifacts']}")
            print(f"    Workflow: {feature['workflow']}")
            print(f"    Kanban: {feature['kanban_stats']}")
            print()

if __name__ == "__main__":
    main()

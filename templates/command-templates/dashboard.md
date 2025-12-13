---
description: Open the Spec Kitty dashboard in your browser.
---
**⚠️ CRITICAL: Read [.kittify/AGENTS.md](.kittify/AGENTS.md) for universal rules (paths, UTF-8 encoding, context management, quality expectations).**

*Path: [templates/commands/dashboard.md](templates/commands/dashboard.md)*


## Context: Dashboard Overview

**What is the dashboard?**
A real-time, read-only web interface showing the health and status of all features in your project.

**Key characteristics**:
- ✅ Read-only (for viewing/monitoring only)
- ✅ Project-wide view (shows ALL features)
- ✅ Live updates (refreshes as you work)
- ✅ No configuration needed (just run the command)

**Run from**: Main repository root (dashboard automatically detects if you're in a worktree)

---

## When to Use Dashboard

- **Project overview**: See all features, their statuses, and progress
- **Debugging workflow**: Check if features are properly detected
- **Monitoring**: Track which features are in progress, review, or complete
- **Status reports**: Show stakeholders real-time feature status

---

## Workflow Context

**Where it fits**: This is a utility command, not part of the sequential workflow

**You can run this**:
- From main repository root
- From inside a feature worktree (dashboard still shows all projects)
- At any point during feature development
- Multiple times (each run can start/reuse the dashboard)

**What it shows**:
- All features and their branches
- Current status (in development, reviewed, accepted, merged)
- File integrity checks
- Worktree status
- Missing or problematic artifacts

---

## Dashboard Access

The dashboard shows ALL features across the project and runs from the **main repository**, not from individual feature worktrees.

## Important: Worktree Handling

**If you're in a feature worktree**, the dashboard file is in the main repo, not in your worktree.

The dashboard is project-wide (shows all features), so it must be accessed from the main repository location.

## Implementation

```python
import webbrowser
import subprocess
import argparse
import sys
from pathlib import Path

from specify_cli.dashboard import ensure_dashboard_running, stop_dashboard

# CRITICAL: Find the main repository root, not worktree
current_dir = Path.cwd()

# Check if we're in a worktree
try:
    # Get git worktree list to find main worktree
    result = subprocess.run(
        ['git', 'worktree', 'list', '--porcelain'],
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode == 0:
        # Parse worktree list to find the main worktree
        main_repo = None
        for line in result.stdout.split('\n'):
            if line.startswith('worktree '):
                path = line.split('worktree ')[1]
                # First worktree in list is usually main
                if main_repo is None:
                    main_repo = Path(path)
                    break

        if main_repo and main_repo != current_dir:
            print(f"📍 Note: You're in a worktree. Dashboard is in main repo at {main_repo}")
            project_root = main_repo
        else:
            project_root = current_dir
    else:
        # Not a git repo or git not available
        project_root = current_dir
except Exception:
    # Fallback to current directory
    project_root = current_dir

# Parse optional CLI arguments
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--port", type=int, help="Preferred port for the dashboard.")
parser.add_argument("--kill", action="store_true", help="Stop the dashboard for this project.")
args, _ = parser.parse_known_args()

if args.kill:
    stopped, message = stop_dashboard(project_root)
    if stopped:
        print(f"✅ {message}")
    else:
        print(f"⚠️  {message}")
    sys.exit(0)

if args.port is not None and (args.port <= 0 or args.port > 65535):
    print("❌ Invalid port specified. Use a value between 1 and 65535.")
    sys.exit(1)

# Ensure the dashboard is running for this project
try:
    dashboard_url, port, started = ensure_dashboard_running(project_root, preferred_port=args.port)
except Exception as exc:
    print("❌ Unable to start or locate the dashboard")
    print(f"   {exc}")
    print()
    print("To bootstrap it manually, run:")
    print(f"  cd {project_root}")
    print("  spec-kitty init .")
    print()
else:
    print()
    print("Spec Kitty Dashboard")
    print("=" * 60)
    print()
    print(f"  Project Root: {project_root}")
    print(f"  URL: {dashboard_url}")
    print(f"  Port: {port}")
    print()
    if started:
        print(f"  ✅ Status: Started new dashboard instance on port {port}")
    else:
        print(f"  ✅ Status: Dashboard already running on port {port}")
    if args.port is not None and args.port != port:
        print(f"  ⚠️  Requested port {args.port} was unavailable; using {port} instead.")

    print()
    print("=" * 60)
    print()

    try:
        webbrowser.open(dashboard_url)
        print("✅ Opening dashboard in your browser...")
        print()
    except Exception:
        print("⚠️  Could not automatically open browser")
        print(f"   Please open this URL manually: {dashboard_url}")
        print()
```

## Success Criteria

- User sees the dashboard URL clearly displayed
- Browser opens automatically to the dashboard
- If browser doesn't open, user gets clear instructions
- Error messages are helpful and actionable

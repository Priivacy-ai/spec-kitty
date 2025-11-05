---
description: Open the Spec Kitty dashboard in your browser.
---
**⚠️ CRITICAL: Read [.kittify/AGENTS.md](.kittify/AGENTS.md) for universal rules (paths, UTF-8 encoding, context management, quality expectations).**

*Path: [templates/commands/dashboard.md](templates/commands/dashboard.md)*


## Dashboard Access

The dashboard shows ALL features across the project and runs from the **main repository**, not from individual feature worktrees.

## Important: Worktree Handling

**If you're in a feature worktree**, the dashboard file is in the main repo, not in your worktree.

The dashboard is project-wide (shows all features), so it must be accessed from the main repository location.

## Implementation

```python
import webbrowser
import socket
import subprocess
from pathlib import Path

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

# Look for dashboard file in main repo
dashboard_file = project_root / '.kittify' / '.dashboard'

if not dashboard_file.exists():
    print("❌ No dashboard information found")
    print()
    print("To start the dashboard, run:")
    print("  spec-kitty init .")
    print()
else:
    # Read dashboard URL
    content = dashboard_file.read_text().strip().split('\n')
    dashboard_url = content[0] if content else None
    port_str = content[1] if len(content) > 1 else None

    if not dashboard_url or not port_str:
        print("❌ Dashboard file is invalid or empty")
        print("   Try running: spec-kitty init .")
        print()
    else:
        # Verify dashboard is actually running on this port
        port = int(port_str)
        is_running = False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            is_running = (result == 0)
        except:
            is_running = False

        print()
        print("Spec Kitty Dashboard")
        print("=" * 60)
        print()
        print(f"  URL: {dashboard_url}")

        if not is_running:
            print()
            print("  ⚠️  Status: Dashboard appears to be stopped")
            print(f"             (Port {port} is not responding)")
        else:
            print()
            print(f"  ✅ Status: Running on port {port}")

        print()
        print("=" * 60)
        print()

        if is_running:
            # Try to open in browser
            try:
                webbrowser.open(dashboard_url)
                print("✅ Opening dashboard in your browser...")
                print()
            except Exception as e:
                print("⚠️  Could not automatically open browser")
                print(f"   Please open this URL manually: {dashboard_url}")
                print()
        else:
            print("💡 To start the dashboard, run: spec-kitty init .")
            print()
```

## Success Criteria

- User sees the dashboard URL clearly displayed
- Browser opens automatically to the dashboard
- If browser doesn't open, user gets clear instructions
- Error messages are helpful and actionable

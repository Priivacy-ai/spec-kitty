---
description: Open the Spec Kitty dashboard in your browser.
---

## Dashboard Access

This command helps you access the Spec Kitty dashboard that was started when you ran `spec-kitty init`.

## What to do

1. **Check if dashboard is running**: Look for the `.kittify/.dashboard` file which contains the dashboard URL and port.

2. **If dashboard file exists**:
   - Read the URL from the first line of `.kittify/.dashboard`
   - Display the URL to the user in a prominent, easy-to-copy format
   - Attempt to open the URL in the user's default web browser using Python's `webbrowser` module
   - If browser opening fails, show instructions on how to manually open it

3. **If dashboard file does not exist**:
   - Inform the user that no dashboard is currently running
   - Explain that they need to run `spec-kitty init` to start the dashboard
   - Provide clear instructions

## Implementation

```python
import webbrowser
import socket
from pathlib import Path

# Check for dashboard info file
dashboard_file = Path('.kittify/.dashboard')

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

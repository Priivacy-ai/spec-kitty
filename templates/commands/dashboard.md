---
description: Open the Spec Kitty dashboard in your browser.
---

## Dashboard Access

This command helps you access the Spec Kitty dashboard that was started when you ran `speckitty init`.

## What to do

1. **Check if dashboard is running**: Look for the `.specify/.dashboard` file which contains the dashboard URL and port.

2. **If dashboard file exists**:
   - Read the URL from the first line of `.specify/.dashboard`
   - Display the URL to the user in a prominent, easy-to-copy format
   - Attempt to open the URL in the user's default web browser using Python's `webbrowser` module
   - If browser opening fails, show instructions on how to manually open it

3. **If dashboard file does not exist**:
   - Inform the user that no dashboard is currently running
   - Explain that they need to run `speckitty init` to start the dashboard
   - Provide clear instructions

## Implementation

```python
import webbrowser
from pathlib import Path

# Check for dashboard info file
dashboard_file = Path('.specify/.dashboard')

if not dashboard_file.exists():
    print("❌ No dashboard is currently running")
    print()
    print("To start the dashboard, run:")
    print("  speckitty init .")
    print()
else:
    # Read dashboard URL
    content = dashboard_file.read_text().strip().split('\n')
    dashboard_url = content[0] if content else None

    if dashboard_url:
        print()
        print("🌱 Spec Kitty Dashboard")
        print("=" * 50)
        print()
        print(f"  URL: {dashboard_url}")
        print()
        print("=" * 50)
        print()

        # Try to open in browser
        try:
            webbrowser.open(dashboard_url)
            print("✅ Opening dashboard in your browser...")
        except Exception as e:
            print("⚠️  Could not automatically open browser")
            print(f"   Please open this URL manually: {dashboard_url}")
    else:
        print("❌ Dashboard file exists but is empty")
        print("   Try running: speckitty init .")
```

## Success Criteria

- User sees the dashboard URL clearly displayed
- Browser opens automatically to the dashboard
- If browser doesn't open, user gets clear instructions
- Error messages are helpful and actionable

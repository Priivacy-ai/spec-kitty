# Dashboard Diagnostics Page Feature

## Overview
Added a comprehensive diagnostics page to the spec-kitty dashboard that shows real-time environment information, helping users understand and fix artifact location mismatches.

## What the Diagnostics Page Shows

### 1. Current Status
- **Project Path**: Where the project is located
- **Current Directory**: Where commands are being run from
- **Git Branch**: Current branch (highlights if on main)
- **In Worktree**: Whether you're currently in a worktree (✅/❌)
- **Worktrees Exist**: Whether any worktrees exist in the project (✅/❌)

### 2. Issues & Warnings
Red alert box showing critical issues like:
- "On main branch - commands will fail!"
- "Location mismatch detected"
- Git detection failures

### 3. Recommendations
Yellow info box with actionable suggestions:
- "Navigate to worktree: cd .worktrees/001-feature"
- "Create worktree: git worktree add .worktrees/001-feature 001-feature"
- "You are not in a worktree - navigate to .worktrees/<feature>"

### 4. Feature Analysis
For each feature in the project, shows:
- **Feature name** with status indicator (✅ Locations Match / ❌ Location Mismatch)
- **Worktree existence** status
- **Artifact inventory**:
  - Root artifacts (spec.md, plan.md, etc.)
  - Worktree artifacts (what's actually in the worktree)
- **Path comparison** (the key insight!):
  - **Dashboard expects**: Where dashboard looks for artifacts
  - **CLI will create**: Where spec-kitty commands will create artifacts
- **Feature-specific recommendations** if there are issues

### 5. Refresh Button
Allows users to re-run diagnostics after making changes.

## How to Access

1. Start the dashboard: `spec-kitty dashboard`
2. Click on "🔍 Diagnostics" in the sidebar under the "System" section
3. The page loads automatically and shows real-time analysis

## Technical Implementation

### Backend (`dashboard.py`)

1. **New API endpoint** `/api/diagnostics`:
   - Calls `run_diagnostics()` function
   - Returns comprehensive JSON with all diagnostic data

2. **`run_diagnostics()` function** (lines 221-349):
   - Detects git branch and working directory
   - Analyzes all features for:
     - Worktree existence
     - Artifact locations (root vs worktree)
     - Location mismatches
   - Generates recommendations based on detected issues

### Frontend (`dashboard.py` HTML)

1. **Sidebar navigation** (line 1137-1139):
   - Added "System" section with Diagnostics link

2. **Diagnostics page HTML** (lines 1214-1255):
   - Loading state
   - Current status display
   - Issues/recommendations sections
   - Feature analysis cards
   - Error handling

3. **JavaScript functions** (lines 2007-2122):
   - `showDiagnostics()`: Switches to diagnostics page
   - `loadDiagnostics()`: Fetches data from API
   - `displayDiagnostics()`: Renders the diagnostic data
   - `refreshDiagnostics()`: Reloads diagnostics

## Benefits

1. **Self-Service Debugging**: Users can diagnose artifact issues themselves
2. **Visual Clarity**: Clear ✅/❌ indicators and color coding
3. **Actionable Insights**: Exact commands to fix issues
4. **Real-Time Analysis**: Shows current state, not cached
5. **Path Transparency**: Shows exactly where files are expected vs created

## Example Output

```
Current Status:
- Project Path: /Users/robert/Code/spec-kit
- Current Directory: /Users/robert/Code/spec-kit
- Git Branch: main
- In Worktree: ❌ No
- Worktrees Exist: ❌ No

⚠️ Issues Detected:
• On main branch - commands will fail!

💡 Recommendations:
• No worktrees found - create with: spec-kitty specify

Feature: 001-auth-token-storage [❌ Location Mismatch]
- Worktree exists: ❌ No
- Root artifacts: spec.md, plan.md
- Dashboard expects: /Users/robert/Code/spec-kit/kitty-specs/001-auth-token-storage
- CLI will create: /Users/robert/Code/spec-kit/kitty-specs/001-auth-token-storage
Recommendations:
• Create worktree: git worktree add .worktrees/001-auth-token-storage 001-auth-token-storage
```

## Usage Workflow

1. User notices artifacts missing from dashboard
2. Clicks Diagnostics in sidebar
3. Sees "Location Mismatch" for their feature
4. Follows the exact command shown to navigate to worktree
5. Re-runs spec-kitty commands
6. Clicks Refresh to verify fix
7. Sees "✅ Locations Match"
8. Returns to feature pages - artifacts now visible!

## Next Steps to Use

To see the diagnostics page in action:

1. Restart the dashboard with the updated code:
   ```bash
   # Stop current dashboard if running
   # Then from /Users/robert/Code/spec-kit:
   spec-kitty dashboard
   ```

2. Navigate to http://127.0.0.1:9243/
3. Click "🔍 Diagnostics" in the sidebar
4. Review the diagnostic information for your project

The diagnostics page provides the transparency needed to understand exactly what's happening with artifact locations, making the "missing artifacts" problem easy to diagnose and fix!
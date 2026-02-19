---
description: Open the Spec Kitty dashboard in your browser.
---
**⚠️ CRITICAL: Read the project's AGENTS.md for universal rules (paths, UTF-8 encoding, context management, quality expectations).**

**Finding AGENTS.md**: Look for `.kittify/AGENTS.md` in your current directory. If not found (e.g., in a worktree), find the main repo via `git worktree list --porcelain` (first "worktree" entry is the main repo) and read `.kittify/AGENTS.md` from there.

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

The dashboard shows ALL features across the project. This command launches the Spec Kitty dashboard using the spec-kitty CLI.

## Important: Worktree Handling

**If you're in a feature worktree**, the dashboard automatically detects the main repository location.

The dashboard is project-wide (shows all features) and the CLI handles worktree detection automatically.

## Implementation

Simply run the `spec-kitty dashboard` command to:
- Start the dashboard if it's not already running
- Open it in your default web browser
- Display the dashboard URL
- Automatically handle worktree detection

Execute the following terminal command:

```bash
spec-kitty dashboard
```

## Additional Options

- To specify a preferred port: `spec-kitty dashboard --port 8080`
- To stop the dashboard: `spec-kitty dashboard --kill`

## Success Criteria

- User sees the dashboard URL clearly displayed
- Browser opens automatically to the dashboard
- If browser doesn't open, user gets clear instructions
- Error messages are helpful and actionable
# Dashboard-Driven Development

This scenario shows how a product trio (PM, designer, tech lead) drives delivery by treating the Spec Kitty kanban dashboard as the single source of truth.

## Setup
Start the dashboard in your project:
```bash
cd my-project
spec-kitty dashboard
# Dashboard opens at http://localhost:3000 (or next available port)
# Runs in background, auto-starts on system reboot
```

## Team Roles
- **PM** watches the dashboard overview tab in browser, resolving blockers and rebalancing priorities
- **Designer** reviews artifacts linked in the feature cards (spec.md, plan.md, quickstart.md) to ensure UX intent stays intact
- **Tech Lead** keeps an eye on lane distribution and redirects agents if review queues build up

## Daily Loop

### 1. Morning Alignment (9:00 AM)
- **All:** Open dashboard at `http://localhost:3000`
- **PM:** Reviews lane counts per feature, flags work packages stuck in "doing" >24 hours
- **Tech Lead:** Notes which agents are assigned to which tasks (shown in dashboard)

### 2. Assign Work Packages (9:30 AM)
- **Tech Lead:** Runs `.kittify/scripts/bash/tasks-list-lanes.sh FEATURE-SLUG` to spot idle prompts
- **PM:** Assigns owners via Slack/email based on dashboard view
- **Agents:** Move prompts to "doing":
  ```bash
  .kittify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG WP01 doing --note "Starting work"
  ```

### 3. Midday Review (1:00 PM)
- **Designer:** Checks prompts in `for_review/` lane (visible in dashboard)
- **Designer:** Opens work package files, adds feedback as markdown comments
- **Designer:** Moves back to planned or forward to done:
  ```bash
  # If needs rework:
  .kittify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG WP01 planned --note "Needs UX revision"

  # If approved:
  .kittify/scripts/bash/tasks-move-to-lane.sh FEATURE-SLUG WP01 done --note "Approved"
  ```

### 4. Evening Recap (5:00 PM)
- **PM:** Takes dashboard screenshot showing lane distribution
- **PM:** Exports `tasks.md` for async updates to stakeholders
- **Tech Lead:** Uses dashboard API for metrics:
  ```bash
  curl http://localhost:3000/api/features | jq
  ```

## Dashboard Features Used
- **Real-time updates** - Browser auto-refreshes as agents move tasks
- **Lane visualization** - See work distribution: planned (blue), doing (yellow), review (orange), done (green)
- **Agent assignments** - Each work package shows which agent is handling it
- **Completion metrics** - Progress bars show % complete per feature
- **Artifact links** - Click through to spec.md, plan.md from dashboard

## Tips
- Use dashboard search/filter to focus on a single feature when managing multiple
- Dashboard runs in background - access from any browser on the network
- `/spec-kitty.dashboard` command from any agent reopens the dashboard URL
- Refresh is automatic via WebSocket - no manual page reload needed
- Pair dashboard with `docs/kanban-dashboard-guide.md` for advanced features

# Parallel Implementation Tracking

Use this recipe when multiple agents implement a roadmap in parallel and leadership needs continuous visibility.

## Setup
- Project: Priivacy Rust recognizers
- Active worktree: `.worktrees/001-systematic-recognizer-enhancement`
- Dashboard URL: `http://localhost:3000` (or custom port from `spec-kitty dashboard`)

## Steps
1. **Start Dashboard** – Run `spec-kitty dashboard` to launch the real-time kanban view. Dashboard runs in background and auto-refreshes.

2. **Snapshot lane counts** – Dashboard shows items in `planned`, `doing`, `for_review`, `done` with live updates. Take screenshots for hourly reports.

3. **Move prompts via helper scripts** – Always use `.kittify/scripts/bash/tasks-move-to-lane.sh` so the dashboard stays synchronized:
   ```bash
   .kittify/scripts/bash/tasks-move-to-lane.sh 001-systematic-recognizer-enhancement WP01 doing
   ```

4. **Record activity logs** – Agents append ISO 8601 entries to the prompt's "Activity Log" section for auditability:
   ```markdown
   ## Activity Log
   - 2025-01-15T09:30:00Z – claude – shell_pid=12345 – lane=doing – Started implementation
   - 2025-01-15T11:45:00Z – claude – shell_pid=12345 – lane=for_review – Ready for review
   ```

5. **Monitor task completion** – Review `kitty-specs/<feature>/tasks.md` checklist to ensure all subtasks are checked before merge.

6. **Automate alerts** (Optional) – Use dashboard API endpoints for monitoring:
   - `GET /api/features` - List all features and their work packages
   - `GET /api/feature/{slug}` - Get specific feature details
   - Build custom alerts when tasks spend >4 hours in `doing` lane

## Reporting
- Export `tasks.md` and dashboard screenshots at daily stand-up
- Summarize agent throughput using the Activity Log entries in work package files
- Identify bottlenecks by checking lane distribution in dashboard
- Use `/spec-kitty.accept --mode checklist` to generate readiness report
- Use `/spec-kitty.merge --dry-run` to produce merge preview for executives

## Dashboard Features for Tracking
- **Real-time updates** - No refresh needed, WebSocket keeps dashboard live
- **Lane filtering** - Focus on specific lanes (e.g., only "for_review")
- **Agent assignments** - See which agent is working on which task
- **Completion metrics** - Track progress percentages per feature

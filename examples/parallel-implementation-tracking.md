# Parallel Implementation Tracking

Use this recipe when multiple agents implement a roadmap in parallel and leadership needs continuous visibility.

## Setup
- Project: Priivacy Rust recognizers
- Active worktree: `.worktrees/001-systematic-recognizer-enhancement`
- Dashboard URL: output of `spec-kitty dashboard`

## Steps
1. **Snapshot lane counts** – `spec-kitty dashboard` highlights items in `planned`, `doing`, `for_review`. Export metrics hourly.
2. **Move prompts via helper scripts** – Always use `.kittify/scripts/bash/tasks-move-to-lane.sh` so the dashboard stays synchronized.
3. **Record activity logs** – Agents append ISO 8601 entries to the prompt’s “Activity Log” for auditability.
4. **Monitor checklist completion** – Review `kitty-specs/<feature>/checklists/` to ensure no criteria remain unchecked before merge.
5. **Automate alerts** – Subscribe to the dashboard SSE feed and push Slack alerts when a work package spends >4 hours in `doing`.

## Reporting
- Export `tasks.md` and dashboard screenshots at stand-up.
- Summarize agent throughput using the lane history; identify bottlenecks early.
- Use `/spec-kitty.merge --dry-run` to produce merge readiness notes for executives.

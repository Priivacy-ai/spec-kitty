---
title: Kanban Dashboard Guide
description: Deep dive into Spec Kitty’s Kanban dashboard for AI development tracking and real-time progress visibility.
---

# Kanban Dashboard Guide

Spec Kitty ships with a real-time **AI development kanban dashboard** that keeps every agent, reviewer, and stakeholder aligned. This guide explains how to activate the dashboard, what the key visual workflow widgets show, and how to use the telemetry to keep features moving without bottlenecks.

## Why the Dashboard Matters

- **Instant visibility** on every work package, task, and lane—no more guessing who has the next action.
- **Agent coordination** built in; human teammates and AI assistants see precisely where they are needed.
- **Automated alerts** for stalled work so you can rebalance agents before deadlines slip.

## Activating the Dashboard

```bash
spec-kitty init .
spec-kitty dashboard
```

1. Run `spec-kitty init` (or re-run in an existing project) to start the dashboard service.
2. Launch the viewer with `spec-kitty dashboard`; you can also open the URL recorded in `.kittify/.dashboard`.
3. Keep the process running while agents work—the UI updates live as prompts move across lanes.

## Core Dashboard Areas

### 1. Feature Overview
- Shows all active feature branches and their associated worktrees.
- Each card links directly to the `kitty-specs/<feature>/` artifacts.
- Use the filter bar to focus on a specific mission or priority lane.

### 2. Work Package Kanban
- Horizontal lanes (`planned`, `doing`, `for_review`, `done`) mirror the Spec Kitty task workflow.
- Drag-and-drop is intentionally disabled—lane transitions must flow through workflow commands (`spec-kitty agent workflow implement/review`) so the activity log remains authoritative.
- Hovering over a card reveals **real-time progress** statistics, recent agent activity, and checklist compliance.

### 3. Agent Telemetry
- The “Agents” panel highlights what each AI assistant or human is currently executing.
- Use this view to spot idle agents and assign parallel work packages quickly.

## Real-Time Progress Techniques

### Pin the Dashboard During Sprints
Keep the dashboard open in its own monitor window so the team can react to lane changes instantly.

### Monitor Lane Events
Wrap the workflow commands (`spec-kitty agent workflow implement/review`) to emit notifications—each transition prints the feature slug, work package, target lane, and note, which you can forward to Slack, email, or paging tools.

### Integrate With Command Scripts
- Workflow commands push structured events to the dashboard pipeline.
- The **visual workflow** updates in under one second after each lane change, so agents always see fresh data.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Dashboard shows "stopped" | Background process exited | Re-run `spec-kitty dashboard` to restart the service |
| Feature missing from overview | Worktree not initialized | Run `/spec-kitty.specify` for the feature and refresh |
| Lane counts stale | Lane transitions bypassed | Use workflow commands (`spec-kitty agent workflow implement/review`) for all lane changes |

## Next Steps

- Explore multi-agent playbooks in [`/docs/multi-agent-orchestration.md`](multi-agent-orchestration.md).
- Walk through real-world usage scenarios in [`/examples/dashboard-driven-development.md`](../examples/dashboard-driven-development.md).
- Compare dashboards against other SDD tools in the updated README comparison table.

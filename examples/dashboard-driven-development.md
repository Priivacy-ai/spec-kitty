# Dashboard-Driven Development

This scenario shows how a product trio (PM, designer, tech lead) drives delivery by treating the Spec Kitty kanban dashboard as the single source of truth.

## Team Roles
- **PM** watches the dashboard overview tab, resolving blockers and rebalancing priorities.
- **Designer** reviews artifacts linked in the feature cards (spec.md, plan.md, quickstart.md) to ensure UX intent stays intact.
- **Tech Lead** keeps an eye on lane distribution and redirects agents if review queues build up.

## Daily Loop
1. **Morning alignment** – Open the dashboard; PM reviews lane counts and flags packages that need owners.
2. **Assign work packages** – Tech lead runs `tasks-list-lanes.sh` to spot idle prompts, then pings the relevant agent.
3. **Midday review** – Designer checks prompts in `for_review`, adds comments directly in the prompt file, and moves them back via `tasks-move-to-lane.sh`.
4. **Evening recap** – Export dashboard screenshots along with the JSON summary (coming soon) for async updates.

## Tips
- Use the dashboard search to focus on a single mission or feature.
- Keep the terminal dashboard command running so lane changes stream instantly.
- Pair the dashboard with `/docs/kanban-dashboard-guide.md` for deeper analytics.

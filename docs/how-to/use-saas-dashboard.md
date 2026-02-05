# How to Use the SaaS Dashboard

The spec-kitty SaaS dashboard provides a browser-based view of your team's projects, work packages, and activity. Data is synced from CLI users via the sync protocol.

## Prerequisites

- A spec-kitty server account with web login credentials
- At least one project with synced data (see [Server Sync How-To](sync-to-server.md))

## Accessing the Dashboard

Navigate to:

```
https://your-server.example.com/a/<team-slug>/dashboards/
```

Replace `<team-slug>` with your team's identifier. For example, if your team slug is `acme`, the URL would be:

```
https://your-server.example.com/a/acme/dashboards/
```

You must be logged into the web interface to access the dashboard. Web login is separate from CLI authentication -- see the [Authentication How-To](authenticate.md) for details.

---

## Overview

**URL:** `/a/<team>/dashboards/` (the default view)

The overview gives a quick snapshot of team progress across all projects. It displays:

- **Summary counts** -- Total projects, features, and work packages for the team.
- **Status breakdown** -- Work packages grouped by status (planned, doing, for_review, done) with counts for each.
- **Features list** -- All features with their current status.
- **Recent events** -- The latest events across all projects, shown most recent first.

The overview is the landing page when you navigate to the dashboards URL. Use it to get a high-level picture of where things stand before diving into a specific view.

---

## Board View

**URL:** `/a/<team>/dashboards/board/`

The board view presents work packages as a kanban board with columns for each status:

- **Planned** -- Work packages that have not yet started.
- **Doing** -- Work packages currently in progress.
- **For Review** -- Work packages awaiting review.
- **Done** -- Completed work packages.

Each column header shows the count of work packages in that status. Each card displays the work package title and the feature it belongs to.

### Filtering

You can narrow the board to a specific subset of work packages:

- **Project filter** -- Show only work packages belonging to a specific project.
- **Feature filter** -- Show only work packages belonging to a specific feature.

Filters update the board columns dynamically via HTMX, so the page does not fully reload. The board view is the best way to visualize current sprint progress.

---

## Activity Feed

**URL:** `/a/<team>/dashboards/activity/`

The activity feed shows a chronological list of all events, most recent first. Each entry includes:

- **Event type** -- What kind of change occurred.
- **Affected entity** -- The project, feature, or work package that was changed.
- **Timestamp** -- When the event happened.
- **Creator** -- The user or node that created the event.

Events are paginated at 25 per page. As you scroll down, infinite scroll loads the next page of events automatically.

The activity feed is useful for tracking what happened and when, especially for debugging sync issues or auditing changes across the team.

---

## See Also

- [Authentication How-To](authenticate.md) -- Log in to the CLI (separate from web login)
- [Sync Architecture](../explanation/sync-architecture.md) -- How data flows from CLI to dashboard
- [Server Sync How-To](sync-to-server.md) -- Push events so they appear in the dashboard

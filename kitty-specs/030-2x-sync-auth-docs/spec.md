# Feature Specification: Documentation Project - 2.x Sync & Auth Documentation

**Feature Branch**: `030-2x-sync-auth-docs`
**Created**: 2026-02-05
**Status**: Draft
**Mission**: documentation
**Input**: User description: "in a documentation mission, I want to prepare the docs site for the 2.x branch and pre-write the 2.x documentation but not publish it"

## Documentation Scope

**Iteration Mode**: gap-filling
**Target Audience**: CLI developers using spec-kitty to manage projects with server-backed sync and authentication
**Selected Divio Types**: tutorial, how-to, reference, explanation
**Languages Detected**: Python (CLI), JavaScript (SaaS dashboard)
**Generators to Use**: None (all manually written, following existing DocFX site structure)

### Gap Analysis Results

**Existing Documentation**:
- `docs/how-to/sync-workspaces.md` — how-to for worktree rebasing (0.12.x local sync only, not 2.x server sync)
- `docs/reference/cli-commands.md` — reference for all CLI commands (does not include `auth` or new `sync` subcommands)
- `docs/reference/configuration.md` — reference for config files (does not cover server URL or credential storage)
- `docs/tutorials/getting-started.md` — tutorial for first project setup (no server connection steps)
- `docs/how-to/install-spec-kitty.md` — how-to for installation (does not cover 2.x auth setup)

**Identified Gaps**:
1. No tutorial for connecting to a spec-kitty server and authenticating
2. No how-to for `spec-kitty auth login/logout/status` commands
3. No how-to for `spec-kitty sync now` (batch push/pull to server)
4. No how-to for `spec-kitty sync workspace` (register workspace for real-time sync)
5. No how-to for `spec-kitty sync status` (check sync queue and connection)
6. No reference documentation for `auth` subcommands (login, logout, status)
7. No reference documentation for new `sync` subcommands (workspace, now, status)
8. No reference for server URL configuration and credential storage (`~/.spec-kitty/config.toml`, `~/.spec-kitty/credentials.json`)
9. No explanation of the sync architecture (WebSocket real-time, offline SQLite queue, batch REST, event-sourced model)
10. No explanation or how-to for the SaaS dashboard views (overview, board, activity feed)

**Coverage Percentage**: 15% — Only the old local `sync` (worktree rebase) is documented. The entire 2.x authentication system, server sync protocol, and SaaS dashboard are undocumented.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — First-time server connection (Priority: P1)

A developer has spec-kitty 2.x installed and wants to connect to their team's spec-kitty server for the first time. They need to configure the server URL, authenticate, and verify the connection works.

**Why this priority**: Without authentication, no sync features work. This is the entry point for all 2.x server features.

**Independent Test**: A new user with spec-kitty 2.x installed and valid server credentials can follow the tutorial and successfully authenticate, verified by `spec-kitty auth status` showing a valid session.

**Acceptance Scenarios**:

1. **Given** a developer with spec-kitty 2.x installed, **When** they follow the "Connect to a Server" tutorial, **Then** they have a working authenticated session with their team's server.
2. **Given** a developer reading the tutorial, **When** they encounter an authentication error, **Then** the troubleshooting section guides them to a resolution.

---

### User Story 2 — Understanding sync architecture (Priority: P2)

A developer wants to understand how spec-kitty syncs events between the CLI and the server — the difference between real-time WebSocket sync, the offline queue, and batch sync — so they can work confidently in both online and offline scenarios.

**Why this priority**: Understanding the sync model prevents confusion about when changes are visible to teammates and helps debug sync issues.

**Independent Test**: After reading the explanation, the developer can correctly describe the three sync paths (WebSocket real-time, offline SQLite queue, batch REST) and when each is used.

**Acceptance Scenarios**:

1. **Given** a developer who has authenticated, **When** they read the sync architecture explanation, **Then** they understand the event-sourced model and the three data paths.
2. **Given** a developer working offline, **When** they read the explanation, **Then** they understand that events are queued locally and pushed on next `sync now`.

---

### User Story 3 — Using the SaaS dashboard (Priority: P2)

A team lead wants to use the SaaS dashboard to monitor project progress, view the kanban board, and track recent activity across their team's workspaces.

**Why this priority**: The dashboard is the primary visual interface for the synced data. Users need to know what views are available and how to interpret them.

**Independent Test**: A user with a server account can navigate to all three dashboard views (overview, board, activity) and understand what each displays.

**Acceptance Scenarios**:

1. **Given** a team lead logged into the SaaS, **When** they navigate to the dashboard, **Then** they see project/feature/WP counts, status breakdown, and recent events.
2. **Given** a team lead on the board view, **When** they apply project or feature filters, **Then** the kanban columns update to show only matching work packages.

---

### User Story 4 — CLI command reference lookup (Priority: P1)

A developer needs to quickly look up the exact flags, arguments, and behavior of an `auth` or `sync` subcommand while working in the terminal.

**Why this priority**: Reference documentation is the most frequently consulted doc type during active development. Missing reference for new commands blocks effective CLI usage.

**Independent Test**: For every `auth` and `sync` subcommand, the reference page documents all flags, arguments, return codes, and example invocations matching the actual `--help` output.

**Acceptance Scenarios**:

1. **Given** a developer looking up `spec-kitty auth login`, **When** they consult the reference, **Then** they find all flags (`--server`, `--username`, `--password`), expected behavior, and error conditions.
2. **Given** a developer looking up `spec-kitty sync now`, **When** they consult the reference, **Then** they find push/pull behavior, conflict resolution, and offline queue handling.

---

### Edge Cases

- How should documentation reference the SaaS URL? The server URL is team-specific and not hardcoded.
- What happens when the 2.x branch is merged to main? The docs should be ready to publish without modification.
- How do we handle the existing `sync-workspaces.md` which documents the old local sync? It must be preserved alongside the new server sync docs, clearly distinguished.

## Requirements *(mandatory)*

### Functional Requirements

#### Documentation Content

- **FR-001**: Documentation MUST include a tutorial for first-time server connection covering: server URL configuration, `auth login`, verifying with `auth status`.
- **FR-002**: Documentation MUST include a how-to for each `auth` subcommand: `login`, `logout`, `status`.
- **FR-003**: Documentation MUST include a how-to for each new `sync` subcommand: `workspace`, `now`, `status`.
- **FR-004**: Documentation MUST include reference entries for all `auth` subcommands with flags, arguments, and return behavior matching `--help` output.
- **FR-005**: Documentation MUST include reference entries for all new `sync` subcommands with flags, arguments, and return behavior matching `--help` output.
- **FR-006**: Documentation MUST include reference for server configuration (`~/.spec-kitty/config.toml` server_url) and credential storage (`~/.spec-kitty/credentials.json`).
- **FR-007**: Documentation MUST include an explanation of the sync architecture: event-sourced model, WebSocket real-time path, offline SQLite queue, batch REST upload, and how they interact.
- **FR-008**: Documentation MUST include a how-to or tutorial section for the SaaS dashboard views: overview (counts, status breakdown, recent events), board (kanban columns with filters), and activity (paginated event feed).
- **FR-009**: Documentation MUST use proper heading hierarchy, accessible language, and follow the existing DocFX site conventions (YAML front matter, toc.yml entries).
- **FR-010**: Documentation MUST provide working CLI examples for all auth and sync commands.
- **FR-011**: Documentation MUST clearly distinguish between the existing local workspace sync (`spec-kitty sync` for worktree rebasing) and the new server sync commands (`spec-kitty sync now/workspace/status`).
- **FR-012**: All new documentation files MUST be added to the appropriate `toc.yml` files but marked as hidden/unpublished (or placed on a docs branch) so they are not visible in the current published site.
- **FR-013**: Documentation MUST use `gettext`/translation markup patterns consistent with the existing docs site.

### Key Entities

- **Auth Token**: JWT access + refresh token pair stored in `~/.spec-kitty/credentials.json`, obtained via `auth login`, used for API and WebSocket authentication.
- **Event**: The atomic unit of sync — an event-sourced record with `event_id`, `event_type`, `aggregate_id`, `lamport_clock`, `node_id`, and `payload`. Events flow bidirectionally between CLI and server.
- **Offline Queue**: SQLite database storing events created while offline, drained by `sync now` or on next WebSocket connection.
- **WebSocket Token**: Ephemeral token exchanged from JWT, used for real-time WebSocket sync connections. Short-lived, obtained via `POST /api/v1/ws-token/`.
- **SaaS Dashboard**: Server-side rendered views (overview, board, activity) displaying synced project/feature/work-package data for a team.
- **Server URL**: The spec-kitty server endpoint configured in `~/.spec-kitty/config.toml`, e.g., `https://spec-kitty-dev.fly.dev`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every `auth` and `sync` subcommand has a reference entry that matches its `--help` output exactly.
- **SC-002**: A developer new to 2.x can follow the tutorial to authenticate and run their first `sync now` without external help.
- **SC-003**: The sync architecture explanation covers all three data paths and a developer can describe them after reading.
- **SC-004**: All documentation builds with `docfx build` with zero warnings or errors.
- **SC-005**: Documentation files are structured for immediate publication when 2.x merges to main — no placeholder text, no TODOs.

### Quality Gates

- All headings follow proper hierarchy (H1 > H2 > H3, no skipping)
- All CLI examples are tested against the 2.x branch and produce the documented output
- No broken internal links between doc pages
- Existing `sync-workspaces.md` is not modified or broken by new docs
- Each doc page has a "See Also" section linking to related pages

## Assumptions

- **ASM-001**: The spec-kitty server (SaaS) is deployed and accessible at a known URL for testing documentation examples.
- **ASM-002**: The 2.x branch CLI commands (`auth login/logout/status`, `sync workspace/now/status`) are feature-complete and their `--help` output is final.
- **ASM-003**: Documentation will be hosted on the existing DocFX site at `priivacy-ai.github.io/spec-kitty/` and published when 2.x merges to main.
- **ASM-004**: Target audience has basic CLI proficiency and familiarity with git-based project workflows.

## Out of Scope

The following are explicitly NOT included in this documentation project:

- Documentation for SaaS features unrelated to sync and auth (e.g., team management, billing, user admin)
- Self-hosting guide for the SaaS server (Django deployment, Daphne configuration, database setup)
- API reference for the REST endpoints (only CLI-facing behavior is documented)
- Documentation for the spec-kitty-events library internals
- Changes to existing documentation pages (only new pages are added)
- Video tutorials or screencasts
- Translation/localization

## Constraints

- Documentation must be pre-written but not published until 2.x merges to main
- All doc files must follow the existing DocFX site structure and conventions
- The `sync-workspaces.md` how-to for local worktree sync must remain untouched and clearly differentiated from server sync
- CLI examples must be verified against the actual 2.x branch `--help` output
- Documentation must not reference internal API endpoints or implementation details that may change

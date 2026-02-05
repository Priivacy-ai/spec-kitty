# Implementation Plan: 2.x Sync & Auth Documentation

**Branch**: `docs/2x-sync-auth` (off `2.x`) | **Date**: 2026-02-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/030-2x-sync-auth-docs/spec.md`

## Summary

Gap-filling documentation for the 2.x sync and authentication system. Covers CLI auth commands, server sync commands, sync architecture explanation, and SaaS dashboard views. All documentation will be pre-written on a dedicated `docs/2x-sync-auth` branch (off `2.x`) and merged when 2.x ships.

**Critical discovery**: The `auth` and `sync status` CLI commands were implemented (commit `fc0597de`, `90dc9edd~1`) but **deleted from the 2.x mainline** on 2026-02-04 (commit `90dc9edd`, "chore: remove sync module from mainline"). The `sync now` command was never wired as a CLI command, though the `batch.py` infrastructure existed. Documentation will be written based on the deleted source code and working SaaS server endpoints, with the expectation that CLI commands will be re-added before 2.x ships.

## Technical Context

**Language/Version**: Python 3.12 (CLI), Django 6.0 (SaaS)
**Primary Dependencies**: DocFX (docs site), Divio 4-type structure (tutorials, how-to, reference, explanation)
**Storage**: N/A (documentation only)
**Testing**: `docfx build` for zero-warning builds; CLI examples verified against restored commands
**Target Platform**: DocFX static site at `priivacy-ai.github.io/spec-kitty/`
**Project Type**: Documentation (no code changes)
**Constraints**: Docs must be publication-ready when 2.x merges; no placeholder text or TODOs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | N/A | Documentation only, no Python code |
| pytest 90%+ coverage | N/A | No test code produced |
| mypy --strict | N/A | No Python code produced |
| CLI operations < 2s | N/A | No CLI code changes |
| Cross-platform | PASS | Documentation is platform-agnostic |
| Documentation standards | PASS | Following existing DocFX site conventions, clear help text, examples |
| spec-kitty-events dependency | N/A | No dependency changes |
| 2.x branch targeting | PASS | Work happens on `docs/2x-sync-auth` branch off `2.x` |

No constitution violations. This is a pure documentation feature.

## Project Structure

### Documentation (this feature)

```
kitty-specs/030-2x-sync-auth-docs/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: CLI command inventory & server endpoint mapping
├── checklists/
│   └── requirements.md  # Validation checklist
├── research/            # Research artifacts
└── tasks/               # Work package prompts (created by /spec-kitty.tasks)
```

### New Documentation Pages (to be created)

```
docs/
├── tutorials/
│   └── server-connection.md      # FR-001: First-time server setup + auth
├── how-to/
│   ├── authenticate.md           # FR-002: auth login/logout/status
│   ├── sync-to-server.md         # FR-003: sync now/workspace/status (server sync)
│   └── use-saas-dashboard.md     # FR-008: Overview, board, activity views
├── reference/
│   ├── cli-commands.md           # FR-004/005: Updated with auth + sync subcommands
│   └── configuration.md          # FR-006: Updated with server_url + credentials
└── explanations/
    └── sync-architecture.md      # FR-007: Event-sourced model, 3 data paths
```

**Structure Decision**: All new pages follow existing DocFX conventions. No new directories needed except `explanations/` which doesn't exist yet. Reference pages are updated (not new files). Each `toc.yml` gets new entries.

## CLI Command Inventory (from deleted source)

### Auth Commands (deleted in `90dc9edd`, source in `fc0597de`)

| Command | Flags | Behavior |
|---------|-------|----------|
| `auth login` | `--username/-u`, `--password/-p`, `--force/-f` | Prompts for credentials, obtains JWT tokens, stores in `~/.spec-kitty/credentials.json` |
| `auth logout` | (none) | Clears stored credentials |
| `auth status` | (none) | Shows username, server URL, access/refresh token expiry |

### Sync Commands (current + deleted)

| Command | Status | Flags | Behavior |
|---------|--------|-------|----------|
| `sync workspace` | **Exists** | `--repair/-r`, `--verbose/-v` | Rebase workspace on upstream (worktree sync) |
| `sync status` | **Deleted** | `--check/-c` | Shows server URL, config path; `--check` tests WebSocket connectivity |
| `sync now` | **Never wired** | N/A | batch.py had `batch_sync()` and `sync_all_queued_events()` but no CLI command |

### SaaS Server Endpoints (deployed, working)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/token/` | POST | JWT access+refresh token (username/password) |
| `/api/v1/token/refresh/` | POST | Refresh JWT access token |
| `/api/v1/ws-token/` | POST | Exchange JWT for ephemeral WebSocket token |
| `/api/v1/events/batch/` | POST | Batch upload events (up to 1000/request) |
| `/api/v1/sync/projects/` | GET/POST | Project CRUD |
| `/api/v1/sync/features/` | GET/POST | Feature CRUD |
| `/api/v1/sync/work-packages/` | GET/POST | Work package CRUD + dependency management |
| `/api/v1/sync/events/` | GET | Event read-only listing |
| `/ws/v1/events/` | WebSocket | Real-time event stream (CLI or browser auth) |

### SaaS Dashboard Views (deployed, working)

| View | URL Pattern | Features |
|------|-------------|----------|
| Overview | `/a/<team>/dashboards/` | Project/feature/WP counts, status breakdown, recent events |
| Board | `/a/<team>/dashboards/board/` | Kanban columns by WP status, project/feature filters |
| Activity | `/a/<team>/dashboards/activity/` | Paginated event feed (25/page), HTMX infinite scroll |

## Writing Order & Dependencies

```
Phase 1: Reference (foundation for other docs to link to)
  WP01: reference/cli-commands.md updates (auth + sync subcommands)
  WP02: reference/configuration.md updates (server_url, credentials)

Phase 2: Explanation (conceptual foundation)
  WP03: explanations/sync-architecture.md (event model, 3 data paths)

Phase 3: How-to guides (task-oriented, links to reference)
  WP04: how-to/authenticate.md (auth login/logout/status)
  WP05: how-to/sync-to-server.md (sync now/workspace/status)
  WP06: how-to/use-saas-dashboard.md (overview, board, activity)

Phase 4: Tutorial (end-to-end, links to how-to + reference)
  WP07: tutorials/server-connection.md (first-time setup)

Phase 5: Integration (toc.yml updates, cross-linking, build validation)
  WP08: toc.yml updates + cross-linking + docfx build test
```

## Assumptions Validated

- **ASM-001** (Server deployed): Confirmed — SaaS at `spec-kitty-dev.fly.dev` is live, all API endpoints functional
- **ASM-002** (CLI commands final): PARTIALLY — Commands were implemented then deleted. Docs will be written based on the deleted source (`fc0597de`) with the assumption they'll be restored
- **ASM-003** (DocFX hosting): Confirmed — Site at `priivacy-ai.github.io/spec-kitty/` uses DocFX with custom template
- **ASM-004** (Audience proficiency): Confirmed — Users are developers with CLI + git experience

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| CLI commands not restored before 2.x ships | Docs reference non-existent commands | Docs are on a separate branch; won't be published until commands exist |
| `sync now` command interface changes | Reference docs become wrong | Write docs based on batch.py behavior; update when CLI wiring is finalized |
| DocFX `explanations/` directory doesn't exist | Build may break | Create directory with toc.yml in WP08 integration phase |

## Complexity Tracking

No constitution violations to justify. Pure documentation feature, no code complexity.

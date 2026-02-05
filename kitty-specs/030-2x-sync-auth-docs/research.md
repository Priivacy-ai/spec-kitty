# Research: 030-2x-sync-auth-docs

**Date**: 2026-02-05
**Status**: Complete

## Research Question 1: Current State of Auth/Sync CLI Commands

**Decision**: Document based on deleted source code with the expectation commands will be restored.

**Rationale**: The auth commands (`login`, `logout`, `status`) and sync `status` command were fully implemented and working (commit `fc0597de`, Feb 3 2026) but removed from the 2.x mainline in a cleanup commit (`90dc9edd`, Feb 4 2026, "chore: remove sync module from mainline"). The SaaS server endpoints they communicate with are deployed and working. Writing docs now based on the known interface means they'll be ready when CLI commands are re-added.

**Alternatives considered**:
- Wait for commands to be re-added → Delays documentation unnecessarily; interface is already known
- Write docs with placeholder CLI examples → Violates SC-005 (no placeholder text)

**Source references**:
- Auth CLI source: `git show fc0597de:src/specify_cli/cli/commands/auth.py`
- Sync CLI source (pre-cleanup): `git show 90dc9edd~1:src/specify_cli/cli/commands/sync.py`
- Deleted modules: `sync/auth.py` (~414 lines), `sync/batch.py` (~238 lines), `sync/client.py` (~235 lines), `sync/config.py` (~38 lines), `sync/queue.py` (~204 lines)

## Research Question 2: `sync now` Command Interface

**Decision**: Document `sync now` as the CLI surface for batch event sync, with flags inferred from `batch.py` behavior.

**Rationale**: `sync now` was never wired as a CLI command, but `batch.py` provided `batch_sync()` and `sync_all_queued_events()` functions that the command would wrap. The SaaS endpoint (`POST /api/v1/events/batch/`) accepts up to 1000 events per request with gzip compression. The logical CLI interface would be a simple `sync now` command that drains the offline queue.

**Inferred interface**:
```
spec-kitty sync now [--verbose/-v] [--dry-run/-n]
```
- Default: Push all queued events to server, pull new events
- `--verbose`: Show per-event sync status
- `--dry-run`: Show what would be synced without actually syncing

**Risk**: Interface may differ when actually implemented. Mitigation: docs are on a separate branch.

## Research Question 3: DocFX Site Structure & Conventions

**Decision**: Follow existing DocFX conventions exactly.

**Findings**:
- DocFX config: `docs/docfx.json` with `markdig` engine and custom `templates/spec-kitty` template
- Top-level navigation: `docs/toc.yml` with 5 tabs (Home, Tutorials, How-To Guides, Reference, Explanations)
- Each section has its own `toc.yml` for page ordering
- `explanations/` directory does NOT exist yet (tab exists in nav but no directory/content)
- Page format: Standard markdown with optional YAML frontmatter
- Existing pages use `---` horizontal rules as section separators
- "See Also" sections link related pages at the bottom

## Research Question 4: SaaS Server Endpoints Mapping

**Decision**: Document server endpoints only as they relate to CLI commands (not as standalone API reference).

**Findings** (deployed at `spec-kitty-dev.fly.dev`):

### Authentication Flow
1. `POST /api/v1/token/` — Username/password → JWT access + refresh tokens
2. `POST /api/v1/token/refresh/` — Refresh token → new access token
3. `POST /api/v1/ws-token/` — JWT → ephemeral WebSocket token (requires `Authorization: Bearer`)

### Sync Paths
1. **WebSocket real-time**: `ws/v1/events/` — Bidirectional event stream with heartbeat (20s ping/pong)
2. **Batch REST**: `POST /api/v1/events/batch/` — Upload up to 1000 events (gzip-compressed)
3. **REST CRUD**: `/api/v1/sync/{projects,features,work-packages,events}/` — Standard DRF viewsets

### WebSocket Protocol
- CLI auth: `Authorization: Bearer {ws_token}` header during handshake
- Browser auth: First message `{ "type": "auth", "token": "{ws_token}" }`
- Message types: `snapshot`, `event`, `ping`, `pong`, `auth`, `auth_success`, `error`
- Team isolation: Channel groups scoped to `team_{team_id}`

### Dashboard Views (server-side rendered)
- Overview: `/a/<team>/dashboards/` — Counts, status breakdown, recent events
- Board: `/a/<team>/dashboards/board/` — Kanban columns, project/feature filters (HTMX)
- Activity: `/a/<team>/dashboards/activity/` — Paginated feed, 25 events/page (HTMX infinite scroll)

## Research Question 5: Staging Strategy for Unpublished Docs

**Decision**: Use a dedicated `docs/2x-sync-auth` branch off `2.x`.

**Rationale**: User explicitly chose this approach over hidden toc.yml entries or draft frontmatter. This provides the cleanest separation — main's published site is completely untouched, and the docs branch merges alongside the 2.x feature work.

**Workflow**:
1. Create `docs/2x-sync-auth` branch from `2.x`
2. Write all documentation on this branch
3. Each WP creates a worktree from this branch
4. When 2.x merges to main, docs branch merges too

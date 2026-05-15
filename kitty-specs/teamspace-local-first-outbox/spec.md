# Spec: Teamspace local-first lifecycle and readiness

## Mission

Make Spec Kitty CLI lifecycle commands locally durable as events regardless of
sync feature flag, authentication state, or Private Teamspace resolution.
SaaS remote delivery becomes a separate, eventually-consistent step.

Addresses Priivacy-ai/spec-kitty issues #1072, #1073, #1074, #1075, #1076.

## Functional requirements

- **FR-1** Every lifecycle event produced by an emitter API
  (`emit_wp_status_changed`, `emit_mission_created`, `emit_build_registered`, …)
  is appended to the durable on-disk outbox before any auth, ingress, or
  remote-routing decision can drop it.
- **FR-2** When SaaS sync is disabled for the active checkout (feature flag
  off, opt-out, or feature-flag missing), events MUST still be queued
  locally. The remote drain path MUST skip them.
- **FR-3** When the user is not authenticated, events MUST still be queued
  locally. The remote drain path MUST skip them.
- **FR-4** When no Private Teamspace is resolvable for direct ingress, events
  MUST still be queued locally with `team_slug = None`. The remote drain path
  MUST NOT fall back to a shared team — ingress safety is preserved.
- **FR-5** `BuildRegistered` and `BuildHeartbeat` events MUST be emitted with
  only `build_id` (plus optional `project_uuid`); `repo_slug` is optional
  enrichment. Local-only projects without a git remote MUST register.
- **FR-6** `spec-kitty init` MUST emit a first-class build/project-init event
  via the durable outbox after identity exists. Offline/unauthenticated init
  MUST queue the event and later drain when conditions allow.
- **FR-7** `spec-kitty sync status --check` MUST distinguish:
  - local queue depth (events durable on disk)
  - drain blockers (sync-disabled, no-auth, no-team)
  - remote acceptance (ping endpoint)
- **FR-8** Each queued event MUST carry a `drain_blocked_reason` diagnostic
  field captured at emit time so operators can tell why a queue is not
  draining. Drain logic re-evaluates conditions on each pass; the field is
  diagnostic, not load-bearing.

## Non-functional requirements

- **NFR-1** Ingress safety is preserved: no event is shipped remotely with a
  shared or "local" `team_slug`. Direct ingress requires a strict Private
  Teamspace.
- **NFR-2** Emitter never raises on lifecycle events; emission failures
  return `None` and are non-fatal to the calling command.
- **NFR-3** No new external dependencies. No SQLite schema changes (the
  existing queue stores arbitrary JSON envelopes).
- **NFR-4** Backwards-compatible for tests that previously asserted event
  drop — those assertions now check the event is queued with the correct
  `drain_blocked_reason`.

## Acceptance scenarios

- `EventEmitter._emit` produces and queues an event when
  `is_sync_enabled_for_checkout()` returns False.
- `EventEmitter._emit` produces and queues an event when the strict
  resolver returns no Private Teamspace, with `team_slug = None` and
  `drain_blocked_reason = "no_team"`.
- `emit_build_registered()` succeeds for a project with `project_uuid` and
  `build_id` set but `repo_slug = None`.
- `spec-kitty init` produces a `BuildRegistered` event in the outbox even
  when unauthenticated and even without a git remote.
- `spec-kitty sync status --check` reports pending counts grouped by drain
  blocker.

## Out of scope

- SaaS-side projection logic (covered in mission 2).
- Worktree/merge changes.
- Tracker/auth UI redesign.

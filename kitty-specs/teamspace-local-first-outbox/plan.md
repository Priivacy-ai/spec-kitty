# Plan: Teamspace local-first lifecycle and readiness

## Architecture summary

Today, `EventEmitter._emit` evaluates the sync gate, the team ingress
gate, and validation as one funnel: any "not ready" condition silently
drops the event before the durable outbox sees it. This mission separates
**local durability** (always on) from **remote drain eligibility** (gated).

```text
emit_*  ─►  build envelope ─►  validate ─►  queue (always)
                                              │
                              decision at emit time:
                                drain_blocked_reason  =
                                  None              # ready to drain
                                | "sync_disabled"   # checkout opted out
                                | "no_auth"         # no session
                                | "no_team"         # no private teamspace
                                              │
                              drain loop re-resolves on each tick;
                              flag is diagnostic only
```

Identity:
- `project_uuid` (from `.kittify/config.yaml`) is the canonical project key.
- `build_id` (per checkout) identifies the worktree.
- `repo_slug` becomes optional enrichment for git-backed checkouts.

## Code changes

### `src/specify_cli/sync/emitter.py`

- Relax `_PAYLOAD_RULES["BuildRegistered"]` and `_PAYLOAD_RULES["BuildHeartbeat"]`:
  drop `repo_slug` from the required set; keep the validator (string when present).
- In `_emit()`:
  - Replace the two early returns (sync-disabled, team_slug-None) with a
    single `_classify_drain_blocked_reason()` call that returns one of
    {None, "sync_disabled", "no_auth", "no_team"}.
  - Always build the envelope, validate, and queue.
  - WebSocket publish only when reason is None.
- In `_validate_event()`: allow `team_slug = None` (warn-only at debug
  level). Keep all other envelope/payload checks.
- New helper `_classify_drain_blocked_reason()` consolidates routing
  diagnostics.

### `src/specify_cli/sync/runtime.py`

- `attach_emitter()`: drop the `_attached_repo_slug() is not None`
  precondition for the auto `emit_build_registered()`. Identity completion
  (`identity.is_complete`) is sufficient.

### `src/specify_cli/cli/commands/init.py`

- After `_stamp_schema_metadata` / `_save_vcs_config` / `save_agent_config`,
  add `_emit_project_init_event(project_path)`:
  - Run inside a try/except (non-fatal).
  - Ensure identity exists (`ensure_identity(project_path)`).
  - Reset the emitter singleton so it picks up the new project context.
  - Call `get_emitter().emit_build_registered()` — this now goes through
    the durable outbox regardless of auth / team / sync state.

### `src/specify_cli/cli/commands/sync.py`

- `sync status` displays pending counts per `drain_blocked_reason` using
  a new helper on `OfflineQueue`.
- `--check` also reports the most common blocker so operators see WHY
  the queue is stuck (instead of just "queue size 23").

### `src/specify_cli/sync/queue.py`

- Add `get_drain_blocked_counts() -> dict[str, int]` helper that groups
  queued events by their envelope `drain_blocked_reason` field. Implemented
  as a single `SELECT data FROM queue` + JSON scan (queue depths in the
  MVP are bounded, and `sync status` is not on the hot path).

### Tests

- Update `tests/sync/test_events.py::test_team_slug_unresolvable_skips_emission`
  to assert the event is queued with `drain_blocked_reason == "no_team"`.
- Update `tests/sync/test_team_ingress_resolver.py::test_emitter_emit_drops_event_when_no_private_team`
  to assert local durability + no WS send + ingress remains safe.
- Add `tests/sync/test_lifecycle_readiness.py` with five readiness
  scenarios covering FR-2 through FR-6.

## Risks

- Existing tests that pin "event drop" semantics fail — explicitly listed
  and updated in WP02.
- Drain loop must handle empty/None `team_slug` envelopes gracefully —
  existing logic already calls `_current_team_slug()` per drain tick and
  re-stamps the X-Team-Slug header, so envelope value is informational
  only on the server side.

## Sequencing

1. **WP01** Relax `BuildRegistered`/`BuildHeartbeat` payload rules and
   runtime `attach_emitter`.
2. **WP02** Refactor `_emit()` for local-first durability + add
   `_classify_drain_blocked_reason`.
3. **WP03** Emit project-init event during `spec-kitty init`.
4. **WP04** `sync status` surface drain blockers.
5. **WP05** Readiness tests (covers FR-2 through FR-7).

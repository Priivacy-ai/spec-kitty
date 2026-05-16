# Tasks: Teamspace local-first lifecycle and readiness

## WP01 — Relax BuildRegistered/BuildHeartbeat payload contract

- Drop `repo_slug` from required fields in `_PAYLOAD_RULES["BuildRegistered"]`
  and `_PAYLOAD_RULES["BuildHeartbeat"]` (emitter.py).
- Drop the `_attached_repo_slug() is not None` precondition from
  `SyncRuntime.attach_emitter` (runtime.py).
- Add unit test covering BuildRegistered emission with `repo_slug=None`.

## WP02 — Local-first durability in `_emit()`

- Introduce `_classify_drain_blocked_reason()` helper.
- Refactor `EventEmitter._emit()` to:
  1. tick clock + resolve identity + git metadata + team_slug
  2. classify drain blocker
  3. build envelope with `team_slug` (may be None) and `drain_blocked_reason`
  4. validate (allow team_slug=None)
  5. queue
  6. route to WS only when drain_blocked_reason is None
- Update `_validate_event` to accept `team_slug=None`.
- Update `_route_event` to skip WS for blocked events but still queue.

## WP03 — Emit project-init event during `spec-kitty init`

- Add `_emit_project_init_event(project_path: Path)` helper at the end of
  the `init` command, after identity/config are written.
- Reset emitter singleton so it re-resolves project identity for the new
  checkout.
- Wrap in best-effort try/except — never fail init on emission failure.

## WP04 — Surface drain blockers in `sync status`

- Add `OfflineQueue.get_drain_blocked_counts() -> dict[str, int]`.
- Render a "Pending Routing" panel in `sync status` when the queue is
  non-empty and any drain blocker is non-zero.
- Improve `sync status --check`: report whether the queue can drain
  given current local state (auth + team + sync flag).

## WP05 — Readiness tests

- `tests/sync/test_lifecycle_readiness.py`:
  - `test_event_durable_when_sync_disabled`
  - `test_event_durable_when_unauthenticated`
  - `test_event_durable_when_no_private_teamspace`
  - `test_build_registered_succeeds_without_repo_slug`
  - `test_init_emits_project_init_event_offline` (CliRunner)
- Update `tests/sync/test_events.py::test_team_slug_unresolvable_skips_emission`
  to new durability semantics.
- Update `tests/sync/test_team_ingress_resolver.py::test_emitter_emit_drops_event_when_no_private_team`
  to new durability semantics + verify no ingress side-effect.
- Add `tests/cli/commands/test_sync_status_drain_blockers.py` for FR-7.

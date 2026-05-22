# Canonical Producer Refactor — Strict Lifecycle Validation (#1198 / #1200)

## Problem Statement

Multiple CLI producer surfaces still hand-build event-shaped dictionaries.
They are currently protected by a lint baseline (50 lines in
`scripts/canonical_producer_lint_baseline.txt`; 172 violation lines without
baseline). This means the next schema change can again become an RC-canary
failure rather than an emit-time error.

Phase 1 of the program (sibling repo `spec-kitty-events`, PR #39 on branch
`kitty/pr/1198-canonical-producer-contracts`) shipped canonical models for
all seven previously-uncontracted SaaS-bound event types and tightened
`validate_event()` semantic enforcement for `WPStatusChanged` review-
rejection transitions. This mission converts the CLI producers to
construct through those canonical models/builders, replaces
`_validate_lifecycle_payload()`'s permissive behavior with strict
canonical validation for known event types, fixes the `reset_handlers()`
test-order pollution, adds producer conformance tests, and burns down
the lint baseline.

## Mission Scope

### In-scope (this mission)

- `src/specify_cli/status/lifecycle_events.py`
  - `_validate_lifecycle_payload()`: schema violations fatal for known types.
  - `emit_project_initialized()`, `emit_mission_created_local()`,
    `emit_artifact_phase()`, `emit_wp_created_local()`: construct via
    canonical pydantic payload models (`spec_kitty_events.project_lifecycle`).
  - Started/Completed split for `emit_artifact_phase`: refuse Completed-only
    extras on Started events.
- `src/specify_cli/sync/emitter.py`
  - `emit_wp_status_changed`, `emit_wp_created`, `emit_wp_assigned`,
    `emit_build_registered`, `emit_build_heartbeat`, `emit_history_added`,
    `emit_error_logged`, `emit_dependency_resolved`, `emit_mission_origin_bound`,
    `emit_mission_created`, `emit_mission_closed`: construct via canonical
    pydantic payload models.
  - Central `_emit()`: validate payload strictly through `validate_event(..., strict=True)`
    when the event type is in `_EVENT_TYPE_TO_MODEL`.
- `src/specify_cli/status/adapters.py`
  - Fix `reset_handlers()` test-order pollution. The new behavior must let
    tests reset state and have the sync package's lifecycle handler stay
    registered, OR provide a re-registration hook that the conftest can
    pin in module scope.
- `scripts/canonical_producer_lint_baseline.txt` burndown.
- New `tests/status/test_producer_conformance.py` (or similar) that
  enumerates emit paths, captures envelopes, and asserts strict canonical
  validation.

### Out of scope

- Any changes in `spec-kitty-events`, `spec-kitty-saas`,
  `spec-kitty-end-to-end-testing`.
- Bumping `pyproject.toml` to a pinned `spec-kitty-events` version
  (Phase 5 cross-repo bump).
- The 4-run identity-boundary canary on deployed-dev (Phase 4/5).
- `#1038` / `#1112` evidence comments (orchestrator).

## Acceptance Criteria

1. Every SaaS-bound CLI event is constructed through canonical
   `spec-kitty-events` models/builders. All seven previously-uncontracted
   event types (`WPAssigned`, `BuildRegistered`, `BuildHeartbeat`,
   `HistoryAdded`, `ErrorLogged`, `DependencyResolved`,
   `MissionOriginBound`) now flow through their Phase-1 models.
2. No producer hand-builds known SaaS-bound event payloads with ad hoc
   dictionaries.
3. `_validate_lifecycle_payload()` treats schema violations as fatal for
   known event types. Local-only events may keep permissive behavior
   only if explicitly classified.
4. The `emit_artifact_phase()` Started/Completed split rejects
   Completed-only extras on Started variants.
5. `reset_handlers()` test-order pollution is fixed:
   `tests/status/test_emit_backward_transition.py` then
   `tests/status/test_lifecycle_events.py` passes deterministically.
6. New producer conformance tests enumerate the actual `emit_*` paths,
   capture each emitted envelope, and assert it passes strict canonical
   validation via the Phase-1 `validate_event(..., strict=True)`.
7. `scripts/canonical_producer_lint_baseline.txt` is materially reduced.
   Each remaining entry must (a) be in a local-only/internal/test-only
   path, (b) carry an inline `# canonical-producer-exempt: <issue-ref>
   — <one-line reason>` on the violating line, and (c) reference a
   tracker (typically `#1200` or `#1203`).
8. `python scripts/lint_canonical_producers.py --paths src tests scripts`
   (no baseline) reports substantially fewer than the current 172
   violation lines.
9. `python scripts/lint_canonical_producers.py --paths src tests scripts
   --baseline scripts/canonical_producer_lint_baseline.txt` passes.
10. All existing tests stay green; new tests added.
11. `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check
    --json` works end-to-end using an isolated test home.

## Operating Rules

- No SaaS DB / queue / readiness mutations.
- No ingress-limit changes.
- All event producers construct via canonical `spec_kitty_events`
  pydantic models.
- `spec-kitty next` is the only entry point for advancing per-WP state.
- `status.events.jsonl` is append-only; emit only via
  `emit_status_transition`.
- Backward rewinds require `force=True` and non-empty `reason`.
- No new pip deps unless explicit.
- Use isolated test homes (`HOME=$(mktemp -d)` / `tmp_path`); never
  depend on the operator's local home.

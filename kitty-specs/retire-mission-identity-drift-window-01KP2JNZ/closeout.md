# Close-Out: Retire Mission Identity Drift Window

**Mission ID**: `01KP2JNZ7FRXE6PZKJMH790HA5`
**GitHub Issue**: [Priivacy-ai/spec-kitty#557](https://github.com/Priivacy-ai/spec-kitty/issues/557)
**Cross-repo Dependency**: [Priivacy-ai/spec-kitty-saas#66](https://github.com/Priivacy-ai/spec-kitty-saas/issues/66)
**Date**: 2026-04-13

## What Was Removed

### 1. `legacy_aggregate_id` field (WP01)

- **File**: `src/specify_cli/status/models.py`
- `StatusEvent.to_dict()` no longer emits the `legacy_aggregate_id` key. Previously, when a `StatusEvent` carried a `mission_id`, serialization would also emit `legacy_aggregate_id` set to the `mission_slug` as a compatibility shim for SaaS readers that had not yet migrated to ULID-keyed lookups.
- The conditional branch that produced `legacy_aggregate_id` in `to_dict()` was deleted entirely.

### 2. `effective_aggregate_id` fallback (WP02)

- **File**: `src/specify_cli/sync/emitter.py`
- The `mission_id` parameter on `emit_mission_created()`, `emit_mission_closed()`, and `emit_mission_origin_bound()` was changed from `Optional[str] = None` to a mandatory `str` parameter.
- The `effective_aggregate_id` slug-fallback pattern (`mission_id or mission_slug`) was removed from all three methods. `aggregate_id` is now always the ULID `mission_id`, with no fallback path.

### 3. Optional `mission_id` on `emit_status_transition` (WP02)

- **File**: `src/specify_cli/status/emit.py`
- Removed the `feature_slug` fallback assignment to `mission_id` in the emitter pipeline. The emitter now reads `mission_id` from `meta.json` if available and passes `None` otherwise (for legacy missions). There is no synthetic fallback.

### 4. Test assertions for removed fields (WP03)

- **File**: `tests/status/test_event_mission_id.py`
- Tests that previously asserted `legacy_aggregate_id` *presence* were rewritten to assert its *absence*.
- **File**: `tests/contract/test_identity_contract_matrix.py`
- Contract matrix updated: `wp_status_event` surface `identity_locations` no longer includes `legacy_aggregate_id`.
- Added negative assertion confirming `legacy_aggregate_id` is never emitted.
- SaaS emitter surface tests now assert `mission_id` is mandatory (TypeError on omission).

## What Was Preserved

### 1. `mission_id` field on `StatusEvent` dataclass (`str | None`)

- The field remains typed as `str | None` to accommodate legacy events read from disk that were written before the identity migration. These events carry only `mission_slug` and no `mission_id`.
- `to_dict()` conditionally includes `mission_id` only when non-None; legacy events serialize without it.

### 2. `mission_slug` field

- Retained everywhere as a human-readable display field. It is still emitted in status events, sync payloads, snapshots, and merge state.

### 3. Legacy event deserialization

- `StatusEvent.from_dict()` still accepts events without `mission_id`, setting it to `None`.
- `read_events()` enriches legacy events with `mission_id` from `meta.json` when available.
- The reducer processes both legacy and new-format events identically for lane-state computation.

## Grep Audit Results (T018)

All searches executed against `src/specify_cli/` (source code only, excluding `__pycache__`):

| Search | Matches in source | Result |
|--------|-------------------|--------|
| `legacy_aggregate_id` | **0** | PASS |
| `effective_aggregate_id` | **0** | PASS |
| `drift.window` / `drift_window` | **0** | PASS |

Test files (`tests/`) contain references to `legacy_aggregate_id` and "drift window" in assertion messages and docstrings. These are the contract tests that verify the field is *absent* post-removal -- they document the negative contract, not a residual dependency.

## T019 -- Sweep Remaining References

**N/A**. T018 found zero identity-drift-window references in source code. No sweep required.

## Cross-Repo Dependency Note

**spec-kitty-saas#66** tracks the SaaS-side read-switch from slug-keyed aggregate lookup to ULID-keyed (`mission_id`) lookup. This CLI-side retirement was gated on that issue being complete. The SaaS service now reads `mission_id` as the canonical join key; `legacy_aggregate_id` was a bridge field that is no longer consumed.

Closing #557 requires:
1. This PR merged (CLI shim removed) -- this mission
2. `spec-kitty-saas#66` closed (SaaS read-switch confirmed)

## Issue #557 Closure Criteria

| Criterion | Status |
|-----------|--------|
| `spec-kitty-saas#66` closed (SaaS read-switch complete) | Tracked externally |
| `legacy_aggregate_id` absent from `src/specify_cli/` | CONFIRMED (0 matches) |
| `effective_aggregate_id` slug fallback absent from sync emitter | CONFIRMED (0 matches) |
| Tests assert the *absence* of the removed shim | CONFIRMED (WP03) |
| Grep audit confirms no remaining drift-window references in source | CONFIRMED (T018) |
| PR merged, CI green | Pending merge |
| Close #557 with a comment linking the merged PR | After merge |

## Summary

The mission-identity drift window is fully retired on the CLI side. The `mission_id` ULID is the sole machine-facing aggregate identity for all mission-lifecycle events. Legacy events on disk remain readable. The wire format is now unambiguous: new events carry `mission_id` and `mission_slug`; legacy events carry only `mission_slug`. The `legacy_aggregate_id` bridge field and `effective_aggregate_id` fallback pattern are gone.

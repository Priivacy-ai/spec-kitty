# Contract: 7-Lane to 4-Lane Status Collapse

**Feature**: 039-cli-2x-readiness
**Version**: 1.1.0
**Date**: 2026-02-12

## Overview

The spec-kitty CLI uses a 7-lane canonical status model internally (from `specify_cli.status.models.Lane`). When events are synced to the SaaS backend, lane values are collapsed to a 4-lane model for the current SaaS contract.

The authoritative mapping is the `_SYNC_LANE_MAP` dict in `src/specify_cli/status/emit.py`.

## Mapping Table

| 7-Lane (Internal) | 4-Lane (Sync Payload) | Rationale |
|--------------------|-----------------------|-----------|
| planned | planned | Direct mapping -- work not yet started |
| claimed | planned | Claimed but not yet actively working; SaaS sees "not started" |
| in_progress | doing | Direct mapping (alias: "doing" resolves to in_progress) |
| for_review | for_review | Direct mapping |
| done | done | Direct mapping (terminal) |
| blocked | doing | Blocked items have been started; they are "in progress but stuck" |
| canceled | planned | Canceled items revert to "not started" in SaaS vocabulary |

## 4-Lane Values (SaaS Contract)

The SaaS batch endpoint accepts exactly these lane values in `StatusTransitionPayload.from_lane` and `StatusTransitionPayload.to_lane`:

- `planned` -- Work not yet started (includes claimed, canceled)
- `doing` -- Work in progress (includes blocked)
- `for_review` -- Work submitted for review
- `done` -- Work complete

**Unknown lane values MUST be rejected** by the SaaS endpoint with a descriptive error.

## Lossy Collapse Warning

This mapping is intentionally lossy:

- **claimed vs planned**: Both map to `planned`. The SaaS cannot distinguish "claimed but not started" from "not yet claimed."
- **blocked vs in_progress**: Both map to `doing`. The SaaS cannot distinguish "blocked" from "actively working."
- **canceled vs planned**: Both map to `planned`. The SaaS cannot distinguish "canceled" from "not yet started."

If the SaaS requires higher fidelity in the future, the contract should be extended to accept the full 7-lane model. This is a follow-on decision, not in scope for this sprint.

## No-Op Transition Suppression

When a canonical transition maps to identical 4-lane values on both sides, the SaaS fan-out is skipped. For example:

- `planned -> claimed` maps to `planned -> planned` -- no SaaS event emitted
- `planned -> canceled` maps to `planned -> planned` -- no SaaS event emitted

This prevents noise in the SaaS event stream while preserving full fidelity in the canonical event log.

## Implementation Location

The mapping dict lives at:

```
src/specify_cli/status/emit.py :: _SYNC_LANE_MAP
```

This is the **single source of truth** for the 7-to-4 collapse. No other module should define a competing mapping dict. Consumers should import from `specify_cli.status.emit` if they need access.

## Alias Resolution

The CLI accepts `doing` as an alias for `in_progress` via `LANE_ALIASES = {"doing": "in_progress"}` in `specify_cli.status.transitions`. This alias is resolved **before** the 7-to-4 collapse, so:

- User types `--to doing` -> resolved to `in_progress` -> collapsed to `doing` in sync payload

The net effect is transparent: `doing` in, `doing` out.

## Edge Cases

- **None/null from_lane**: Valid for initial transitions (first time a WP gets a lane). Sync payload should send `null` for `from_lane`.
- **Same from_lane and to_lane after collapse**: Suppressed (no SaaS event emitted).
- **Unknown 7-lane value**: The `_SYNC_LANE_MAP.get()` call returns `None`, causing the SaaS fan-out to be skipped with a debug log. The canonical event log is unaffected.

## Verification

Automated tests in `tests/specify_cli/status/test_sync_lane_mapping.py` verify:

1. All 7 canonical lanes have correct 4-lane outputs (parametrized)
2. Invalid lane inputs raise `TransitionError`
3. `_SYNC_LANE_MAP` is centralized in `status/emit.py` with no duplicates
4. This contract document matches the implementation

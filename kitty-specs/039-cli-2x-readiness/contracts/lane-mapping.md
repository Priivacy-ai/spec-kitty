# Contract: 7-Lane to 4-Lane Status Collapse

**Feature**: 039-cli-2x-readiness
**Version**: 1.0.0
**Date**: 2026-02-12

## Overview

The spec-kitty CLI uses a 7-lane canonical status model internally (from `spec_kitty_events.status.Lane`). When events are synced to the SaaS backend, lane values are collapsed to a 4-lane model for the current SaaS contract.

## Mapping Table

| 7-Lane (Internal) | 4-Lane (Sync Payload) | Rationale |
|--------------------|-----------------------|-----------|
| PLANNED | planned | Direct mapping |
| CLAIMED | doing | Claimed = work started, not yet in progress |
| IN_PROGRESS | doing | Direct mapping (alias: "doing" → IN_PROGRESS) |
| FOR_REVIEW | for_review | Direct mapping |
| DONE | done | Direct mapping (terminal) |
| BLOCKED | doing | Blocked items have been started; they are "in progress but stuck" |
| CANCELED | done | Canceled items are terminal; SaaS treats both DONE and CANCELED as complete |

## 4-Lane Values (SaaS Contract)

The SaaS batch endpoint accepts exactly these lane values in `StatusTransitionPayload.from_lane` and `StatusTransitionPayload.to_lane`:

- `planned` — Work not yet started
- `doing` — Work in progress (includes claimed, blocked)
- `for_review` — Work submitted for review
- `done` — Work complete (includes canceled)

**Unknown lane values MUST be rejected** by the SaaS endpoint with a descriptive error.

## Lossy Collapse Warning

This mapping is intentionally lossy:

- **CLAIMED vs IN_PROGRESS**: Both map to `doing`. The SaaS cannot distinguish "claimed but not started" from "actively in progress."
- **BLOCKED vs IN_PROGRESS**: Both map to `doing`. The SaaS cannot distinguish "blocked" from "actively working."
- **DONE vs CANCELED**: Both map to `done`. The SaaS cannot distinguish "successfully completed" from "abandoned."

If the SaaS requires higher fidelity in the future, the contract should be extended to accept the full 7-lane model. This is a follow-on decision, not in scope for this sprint.

## Implementation Location

The mapping function lives at `src/specify_cli/sync/emitter.py` (approximately line 46 on the 2.x branch).

## Alias Resolution

The CLI accepts `doing` as an alias for `IN_PROGRESS` via `LANE_ALIASES = {"doing": IN_PROGRESS}` in `spec_kitty_events.status`. This alias is resolved before the 7→4 collapse, so:

- User types `--to doing` → resolved to `IN_PROGRESS` → collapsed to `doing` in sync payload

The net effect is transparent: `doing` in, `doing` out.

## Edge Cases

- **None/null from_lane**: Valid for initial transitions (first time a WP gets a lane). Sync payload should send `null` for `from_lane`.
- **Same from_lane and to_lane**: Valid (e.g., force-moving within same lane). Sync should still emit the event.
- **Unknown 7-lane value**: The mapping function MUST raise `ValueError` for any lane not in the 7-lane enum. This prevents silent data corruption.

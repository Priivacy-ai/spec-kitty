# Phase 1: Data Model

**Mission**: backward-transition-cli-emit-01KRV8GC
**Scope**: Recap of the existing variables and types this mission consumes. No new types; no wire-shape changes.

## Existing Entities (Unchanged)

### `Lane` enum

**Source**: `spec_kitty_events.status.Lane` (imported in `tasks.py`).
Members consumed by this mission: `PLANNED`, `CLAIMED`, `IN_PROGRESS`, `FOR_REVIEW`, `IN_REVIEW`, `APPROVED`, `DONE` — the canonical forward order. Out-of-family lanes (`BLOCKED`, `CANCELED`) fall through the auto-promotion detector (FR-007).

### `StatusTransitionPayload` (in `spec_kitty_events`)

**Source**: `spec_kitty_events.status.StatusTransitionPayload`.
Not modified. Fields consumed at emit time via `emit_status_transition()`: `wp_id`, `from_lane`, `to_lane`, `actor`, `force`, `reason`, `execution_mode`, `review_ref`, `evidence`, `mission_slug`.

This mission changes the *values* of `force` and `reason` for backward emits. It does not change the *shape* of the payload.

## Existing Local Variables in `move_task()` (Hotspot Scope)

| Variable | Source (line) | Type | Role in this mission |
|---|---|---|---|
| `force` | typer.Option (parameter) | `bool` | User's explicit `--force` flag. Auto-promote fires only when `not force`. |
| `old_lane` | resolved upstream | `str` (Lane value) | Current canonical lane. Used as `from_lane` in emit and as the upper end of the backward direction check. |
| `target_lane` | typer.Option (`--to`) | `str` | Raw user-supplied target. |
| `canonical_lane` | resolved upstream | `str` (Lane value) | Resolved (alias-normalized) target lane. Used as `to_lane` in emit and as the lower end of the backward check. |
| `emit_force` | line 1710 | `bool` | The wire-level `force` value. **Modified by this mission**: set to True for auto-promoted backward emits. |
| `emit_reason` | lines 1650, 1652, 1711 | `str \| None` | The wire-level `reason` value. **Modified by this mission**: set to the canonical shape for auto-promoted backward emits when no upstream branch already set it (FR-002, R-003 decision). |
| `review_feedback_pointer` | line 1538 | `str \| None` | URI-shaped pointer to review feedback artifact. Source of `<feedback-ref>` segment in the canonical reason (R-002 decision). Skip when value is `"force-override"`. |
| `transition_targets` | line 1727 | `list[str]` | The lanes to emit events for. For backward auto-promoted emits, the existing `_lane_targets_for_emit` helper already returns `[canonical_lane]` (single event) — no change needed (R-001 decision). |

## New Helper (Phase 3 Implementation)

### `_is_backward_transition(current_lane: str, target_lane: str) -> bool`

**Visibility**: Private module-level helper in `src/specify_cli/cli/commands/agent/tasks.py`, placed adjacent to the existing closure `_lane_targets_for_emit`. (Alternative: nested closure inside `move_task()`. Choice deferred to implementation; preference is module-level for testability.)

**Behavior**:

```
returns True iff:
  resolve_lane_alias(current_lane) in FORWARD_ORDER
  AND resolve_lane_alias(target_lane) in FORWARD_ORDER
  AND FORWARD_ORDER.index(target) < FORWARD_ORDER.index(current)
```

where `FORWARD_ORDER = [Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS, Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.APPROVED, Lane.DONE]` — the same list literal used in `_lane_targets_for_emit`.

**Returns False** for:
- Non-forward-set lanes (`BLOCKED`, `CANCELED`) — terminal-lane exits and quarantine states preserve explicit-`--force` semantics (FR-007).
- Equal lanes.
- Forward direction.

## Canonical Reason Shape (Phase 3 Construction)

Pseudocode for the new logic at the hotspot:

```python
# AFTER existing line 1710 (emit_force = force) and line 1711-1712 (existing emit_reason fallback)
if not force and _is_backward_transition(old_lane, canonical_lane):
    emit_force = True
    if not emit_reason or emit_reason.startswith("move-task: "):
        # User did not supply --note; the line 1712 fallback set the generic shape.
        # Replace with the canonical backward-rewind shape.
        reason_parts = [f"backward rewind: {old_lane} -> {canonical_lane}"]
        if review_feedback_pointer and review_feedback_pointer != "force-override":
            reason_parts.append(review_feedback_pointer)
        emit_reason = ": ".join(reason_parts)
    # else: respect user-supplied --note (R-003 decision)
```

The `emit_reason.startswith("move-task: ")` heuristic distinguishes the generic fallback from a user-supplied `--note`. A user `--note` whose text happens to start with `"move-task: "` will get rewritten — acceptable trade-off because that's the exact wording the current bug emits, so anyone with such a note is almost certainly seeing the bug's fallback.

## Out-of-Family Behavior (Documented as Distinct)

- **Terminal-lane exits** (`done → *`, `canceled → *`): These already require explicit `--force` from the user. Auto-promotion does not fire (R-001: helper returns `[target]` for any pair involving a non-forward-set lane). Status quo preserved (FR-007).
- **Forward transitions**: Helper returns `forward[current_idx + 1 : target_idx + 1]` for skip-ahead forward moves; the new detector returns False; no change to emit_force or emit_reason. Behavior preserved (FR-004).
- **Equal lane** (`X → X`): Detector returns False; no change.
- **Bootstrap-planned** (forced `* → planned` with `from_lane=None`): Out of scope — this mission only affects backward transitions from a known `old_lane`. Bootstrap events go through a separate code path (the finalize-tasks bootstrap pipeline in `specify_cli.status.bootstrap`).

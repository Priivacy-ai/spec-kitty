# Contract: Auto-Promoted Backward Emit (CLI Wire Shape)

**Audience**: Maintainers of `src/specify_cli/cli/commands/agent/tasks.py:move_task()` and authors of any consumer (SaaS materializer in Mission 3, durable drain, projection engine) that needs to recognize an auto-promoted backward emit on the wire.

**Status**: Normative for this mission. Implements the contract anchored at `spec-kitty-events`'s `status.py` module docstring and `docs/consumer-contract-dossier-v2.4.0.md` §7.

## Inputs (at the hotspot)

| Variable | Provenance | Used as |
|---|---|---|
| `force: bool` | typer.Option `--force` | Branch selector. Auto-promotion fires only when `force is False`. |
| `old_lane: str` | resolved upstream from event log | Source lane in backward-direction check; `from_lane` in emitted event. |
| `canonical_lane: str` | resolved upstream from `--to <target>` | Target lane in backward-direction check; `to_lane` in emitted event. |
| `review_feedback_pointer: str \| None` | resolved upstream from `--review-feedback-file` or `_review_cycle.pointer` | Optional `<feedback-ref>` segment in canonical reason. |
| `emit_reason: str \| None` | already set by upstream branches (`--note`, `--force` fallback, generic fallback) | Preserved if user-supplied; overwritten if it's the generic fallback. |

## Output (wire-level mutations)

| Field | Value when auto-promote fires | Value otherwise (status quo) |
|---|---|---|
| `emit_force` | `True` | unchanged (`force`) |
| `emit_reason` | `"backward rewind: <old_lane> -> <canonical_lane>"` + optional `": <review_feedback_pointer>"` | unchanged (existing fallback or user `--note`) |
| `transition_targets` | `[canonical_lane]` (single event; existing helper behavior) | unchanged |

All other fields of the emitted `StatusTransitionPayload` are unchanged.

## Decision Procedure

```
INPUTS: force, old_lane, canonical_lane, emit_reason, review_feedback_pointer

1. existing path through line 1712 runs as today
   (emit_force = force; emit_reason fallback)

2. backward-detection guard:
   if force:
       return  # explicit-force path preserved (FR-011)
   if NOT _is_backward_transition(old_lane, canonical_lane):
       return  # forward / terminal / equal — preserved (FR-004, FR-007)

3. auto-promote:
   emit_force = True

4. canonical reason rewrite (only if generic fallback):
   if emit_reason is None or emit_reason.startswith("move-task: "):
       reason_parts = [f"backward rewind: {old_lane} -> {canonical_lane}"]
       if review_feedback_pointer is not None
           AND review_feedback_pointer != "force-override":
           reason_parts.append(review_feedback_pointer)
       emit_reason = ": ".join(reason_parts)
   # else: preserve user-supplied --note (R-003 decision)
```

## Backward-Direction Predicate

```
FORWARD_ORDER = [PLANNED, CLAIMED, IN_PROGRESS, FOR_REVIEW, IN_REVIEW, APPROVED, DONE]

_is_backward_transition(current, target):
    c = resolve_lane_alias(current)
    t = resolve_lane_alias(target)
    if c not in FORWARD_ORDER or t not in FORWARD_ORDER:
        return False
    return FORWARD_ORDER.index(t) < FORWARD_ORDER.index(c)
```

## Behaviors That Do NOT Change

- **`--force` explicit**: behavior identical to today. `emit_force = True` via the existing path; `emit_reason = "Force move to <to>"` via the existing fallback (or user `--note`).
- **Forward `move-task`**: behavior identical. `emit_force = False`; `_lane_targets_for_emit` expands skip-ahead forward moves into per-lane events.
- **Terminal-lane exit attempts** (`done → *`, `canceled → *`) without `--force`: detector returns False (lanes outside `FORWARD_ORDER`); existing terminal-lane guard in `validate_transition` (upstream of CLI) rejects the call.
- **Equal lane** (`X → X`): detector returns False; existing no-op or guard logic preserved.

## Conformance Surface

| Property | Verification path |
|---|---|
| `force == True` on auto-promoted backward emit | WP02 test `test_in_review_to_planned_auto_promotes_force` (FR-008 a-c) |
| `reason.startswith("backward rewind: <from> -> <to>")` | Same test family |
| `force == False` on forward move (no auto-promotion) | WP02 test `test_planned_to_claimed_does_not_auto_promote` (FR-008 d) |
| `transition_targets` expansion preserved on forward skip-ahead | WP02 test `test_in_progress_to_for_review_expands_intermediate` (FR-008 e) |
| Backward emit with `--review-feedback-file` includes pointer in reason | WP02 test `test_backward_emit_includes_feedback_ref` (FR-008 f) |
| Wire shape matches Mission 1 fixture `wp-status-changed-approved-rewind-valid` | WP02 test `test_approved_to_planned_matches_mission1_fixture` (FR-009) |

## Anti-Patterns to Avoid

- **Do NOT** mutate `emit_reason` when it's a non-generic user `--note`. User intent wins (R-003).
- **Do NOT** synthesize a fresh feedback URI when `review_feedback_pointer` is None — emit the bare `"backward rewind: <from> -> <to>"` form instead. Synthesizing a URI from `now()` is non-deterministic; better to omit the segment.
- **Do NOT** auto-promote for terminal-lane exits or equal-lane no-ops — those have explicit semantics elsewhere.
- **Do NOT** expand backward jumps into a sequence of intermediate events. The existing helper already returns `[target]` for backward pairs; the test guards this.

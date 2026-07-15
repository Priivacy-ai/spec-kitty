# Data Model: Observable Pre-Review Gate

This Mission adds no persisted schema. It defines transient orchestration concepts and reuses existing authoritative state.

## Transient concepts

### Gate observation

| Field | Type | Meaning |
|---|---|---|
| `started_at` | monotonic timestamp | Start of the observed gate phase. |
| `heartbeat_interval` | positive duration | Maximum intended gap between human liveness indications; production value must be at most 30 seconds. |
| `progress_sink` | callable or protocol | Human-mode liveness receiver; no-op in JSON mode. |
| `progress_callback` | callable | Presentation-only liveness callback supplied by the CLI; no-op in JSON mode. |
| `completion` | completed, timed_out, cancelled, launch_failed, incomplete | Typed terminal state owned by the canonical gate runner. |
| `transition_applied` | boolean | Always `false` in timeout/cancellation command results. |

Invariants:

- Timeout and cancellation remain typed through verdict composition and are never inferred from an error string.
- Liveness is never interpreted as a passing verdict.
- JSON mode does not emit progress prose to stdout.
- The runner terminates and reaps its child before timeout/cancellation returns to command orchestration.
- Applicable recovery writes, including deliverable auto-commit, occur only after the gate permits progress.

### Pre-review gate metadata

The existing `pre_review_gate_metadata` dictionary remains the local structured result. Existing fields (`outcome`, `reason`, failure counts, scope, block flags) remain compatible. Typed terminal classification and `transition_applied` are additive and local to this entry point.

## Existing authoritative state

| Authority | Clean interruption invariant |
|---|---|
| `status.events.jsonl` | No appended transition event. |
| Materialized Mission status | WP lane remains unchanged. |
| WP tracking artifact | Content and placement remain unchanged. |
| Git history | No placement or transition commit is created. |
| Planning checkout | No new Spec Kitty-owned dirty path from the attempted move. |
| Coordination checkout | No new Spec Kitty-owned dirty path from the attempted move. |
| Lane checkout | No new Spec Kitty-owned dirty path from the attempted move. Test-owned writes are preserved and surfaced. |

## State flow

```text
guards passed
  -> gate_observing
       -> gate_completed(verdict) -> existing block policy -> transition planning
       -> gate_timed_out(typed) -> nonzero local result -> no recovery/transition mutation
       -> gate_cancelled(typed) -> child reaped -> nonzero local result -> no recovery/transition mutation
       -> gate_exception -> existing truthful degrade/report policy -> no fabricated pass
```

An uncatchable termination has no transient terminal record. Recovery reads the existing event authority; absence of a new transition event means the prior WP lane remains authoritative.

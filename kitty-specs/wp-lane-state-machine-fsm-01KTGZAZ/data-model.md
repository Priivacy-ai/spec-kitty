# Phase 1 Data Model — WP Lane Finite State Machine

## Lane (enum) — 10 members; 9 active/display + 1 non-display genesis

| Lane | Display? | Weight | Terminal | Role |
|------|----------|--------|----------|------|
| `genesis` | **No** | 0.0 | No | Pre-finalize; created-but-unseeded; `from_lane`-only seed source |
| `planned` | Yes | 0.0 | No | Finalized, claimable |
| `claimed` | Yes | 0.05 | No | Claimed by an actor |
| `in_progress` | Yes | 0.3 | No | Implementation underway |
| `for_review` | Yes | 0.6 | No | Queued for review |
| `in_review` | Yes | 0.7 | No | Under active review |
| `approved` | Yes | 0.8 | No | Review-approved |
| `done` | Yes | 1.0 | **Yes** | Complete |
| `blocked` | Yes | 0.0 | No | Blocked (reachable from active lanes) |
| `canceled` | Yes | 0.0 | **Yes** | Canceled |

`CANONICAL_LANES` = the 9 display lanes (excludes `genesis`). `genesis` is a valid
`from_lane` for event validation but never a `to_lane` and never a current lane.

## WPState (State pattern) — the FSM authority

Each lane is a frozen `WPState` subclass owning its full behavior:

```
WPState (ABC)
  current_lane: Lane                         # the lane this state represents
  may_transition_to(target) -> bool          # structural edge check (guard-free)
  transition_to(target, ctx) -> WPState      # FULL transition: edge + guard + force; raises on reject
  allowed_targets() -> frozenset[Lane]        # outbound edges (derives ALLOWED_TRANSITIONS)
  is_terminal / is_blocked / is_run_affecting
  progress_bucket() / display_category()
```

**Full-ownership change (DM-01KTH03G):** `transition_to` evaluates the guard +
force-override that previously lived in `validate_transition`. `validate_transition`
becomes a thin delegator returning `(ok, error_message)` from the state.

### Edges + guards + force per state

| State | allowed_targets | Guards owned (entry condition) | Force-exit |
|-------|-----------------|-------------------------------|-----------|
| GenesisState | planned, canceled | none (seed) | n/a |
| PlannedState | claimed, blocked, canceled | claimed: actor required | — |
| ClaimedState | in_progress, blocked, canceled | in_progress: workspace_context | — |
| InProgressState | for_review, approved, planned, blocked, canceled | for_review: subtasks_complete_or_force; approved: reviewer_approval | — |
| ForReviewState | in_review, blocked, canceled | in_review: reviewer claim | — |
| InReviewState | approved, done, in_progress, planned, blocked, canceled | all outbound require ReviewResult | — |
| ApprovedState | done, in_progress, planned, blocked, canceled | done: done-evidence | — |
| DoneState | ∅ | terminal | force + actor + reason → any lane |
| BlockedState | in_progress, canceled | — | — |
| CanceledState | ∅ | terminal | force + actor + reason → any lane |

`ALLOWED_TRANSITIONS` is derived: `{(s.current_lane, t) for s in all states for t in s.allowed_targets()}` (29 edges). Force-exit of terminal states is NOT an `allowed_targets` edge — it is the force path, owned by `transition_to` (DoneState/CanceledState), reaching parity with the old `validate_transition` force branch.

## Invariants

- **I1 (single source)**: the only transition-edge truth is `WPState.allowed_targets()`; `ALLOWED_TRANSITIONS` is derived; no parallel `(from,to)` table or lane-adjacency map exists in `src/`.
- **I2 (genesis non-display)**: `genesis ∉ CANONICAL_LANES`; absent from every materialized summary, board, kanban, discovery candidate list, and frontmatter validity message; never a `to_lane`.
- **I3 (read/write parity)**: every lane reader returns `GENESIS` for a WP with no lane events.
- **I4 (full ownership)**: a guarded or forced transition produces the same decision through `wp_state_for(from).transition_to(to, ctx)` as the historical `validate_transition` did.
- **I5 (behavior preservation)**: the 9 pre-existing lanes' edges + guards are unchanged.

## Event model (unchanged)

`status.events.jsonl` append-only event log is the sole authority; `status.json` is a
materialized snapshot. The genesis seed is a real `genesis → planned` event. The SaaS
fan-out (after DM-01KTH03H) emits genesis as a `spec_kitty_events.Lane.genesis` value.

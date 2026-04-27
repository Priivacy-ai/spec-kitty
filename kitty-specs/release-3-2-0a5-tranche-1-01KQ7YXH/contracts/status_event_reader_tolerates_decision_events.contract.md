# Contract: `read_events()` tolerates non-lane-transition events

**Traces to**: FR-010, NFR-010, SC-008

## Stimulus

Any caller of `specify_cli.status.store.read_events(feature_dir)` against a
`status.events.jsonl` file that contains a mix of:

- Zero or more lane-transition events (`StatusEvent`-shaped, with `wp_id`,
  `from_lane`, `to_lane`, etc.).
- Zero or more mission-level events written by sibling subsystems —
  `DecisionPointOpened`, `DecisionPointResolved`, `DecisionPointDeferred`,
  `DecisionPointCanceled`, `DecisionPointWidened`, retrospective events
  (already handled), and any future event-type with no `wp_id`.

## Required behavior

1. `read_events()` returns a `list[StatusEvent]` containing **exactly** the
   lane-transition events (in file order). Mission-level events are
   silently skipped.
2. `read_events()` MUST NOT raise `KeyError` for missing `wp_id`,
   `from_lane`, `to_lane`, `actor`, `force`, or `execution_mode` on any
   event that lacks the lane-transition shape.
3. Existing behavior preserved:
   - Empty files return `[]`.
   - Blank lines are silently skipped.
   - Invalid JSON still raises `StoreError("Invalid JSON on line N: …")`.
   - Lane-transition events with malformed lane fields still raise
     `StoreError("Invalid event structure on line N: …")`.

## Forbidden behavior

- Returning a `list` containing non-`StatusEvent` instances.
- Silently dropping a malformed lane-transition event (one that has
  `wp_id` but a bad `from_lane`).
- Logging a warning for every skipped mission-level event (would flood
  legitimate event logs).

## Implementation hint (informative, not normative)

Add a duck-type guard at the top of `read_events()`'s per-line loop, right
after the `event_name.startswith("retrospective.")` skip:

```python
# Skip mission-level events (DecisionPointOpened, DecisionPointResolved,
# etc.) that share status.events.jsonl with lane-transition events. These
# events have a top-level `event_type` field and no `wp_id`. The duck-type
# check on `wp_id` is preferred over an event_type allowlist so the reader
# stays correct as new mission-level event types are introduced. See
# FR-010.
if "wp_id" not in obj:
    continue
```

## Verifying tests

- New test in `tests/status/test_store.py` (or a sibling new file
  `tests/status/test_read_events_tolerates_decision_events.py`):
  1. Construct a tmp `feature_dir` with a `status.events.jsonl` containing,
     in order: a `DecisionPointOpened` event, a lane-transition event, a
     `DecisionPointResolved` event, a second lane-transition event.
  2. Call `read_events(feature_dir)`.
  3. Assert the result has exactly 2 elements (both `StatusEvent`
     instances), in the same order they appeared in the file, with the
     correct `wp_id` values.
- Existing failure mode (regression):
  - The current tranche's own
    `kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/status.events.jsonl`
    starts with a `DecisionPointOpened` event. Running
    `spec-kitty agent mission finalize-tasks --mission release-3-2-0a5-tranche-1-01KQ7YXH --json`
    fails on `main` and succeeds after the fix. Cite this in the PR
    description as the live evidence.

## Out-of-scope

- Splitting `status.events.jsonl` into separate files for separate event
  schemas (rejected as too large a blast radius — see research.md R9
  Alternative 1).
- Promoting `wp_id` to `Optional[str]` on `StatusEvent` (rejected — see
  research.md R9 Alternative 2).
- Adding a generic event-type registry (out of scope for this stabilization
  tranche).

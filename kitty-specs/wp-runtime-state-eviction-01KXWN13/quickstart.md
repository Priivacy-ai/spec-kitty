# Quickstart: verifying the WP runtime-state eviction

How each success criterion is exercised. Every stability/parity check carries a **proof-of-drive** so
"unchanged" can never mean "untouched".

## SC-001 / SC-005 — no false drift (AC-1 / AC-5)

Drive the mandatory action set on a real WP: `claim → mark-subtask-done → add note →
tracker_ref append → review-reject → review-approve → history append`. Assert:
1. a persisted event exists for **each** action (proof the action fired), and
2. the `tasks/WP##.md` content hash is **byte-identical** from `claimed` to `done`.
mtime is informational only.

## SC-002 — claim-liveness from the snapshot (AC-2), two-sided

Empty frontmatter + live PID in the snapshot → liveness = live. Then mutate the **snapshot** PID to a
dead value → liveness flips to stale. (Pins the snapshot, not the frontmatter, as the decision source.)

## SC-003 — subtask completion is event-sourced (AC-3)

`tests/regression/test_issue_2684_subtask_completion_event_sourced.py` (already merged, red today):
record completion in the log, leave `tasks.md` checkboxes unchecked, `move-task --to for_review`
succeeds; a genuinely-incomplete WP is refused. Add: assert the resolution source is the snapshot
`subtasks` slot (not a `HistoryAdded` read).

## SC-004 — render from events (AC-4)

Drive notes + a review cycle; assert the rendered Activity Log / History / review **matches a golden of
the legacy file-sourced render** for the same event sequence, non-empty, all content classes present.

## SC-006 — migration idempotency (AC-6)

Fixture whose pre-state carries evictable frontmatter+checkbox state: run #1 seeds **N>0** events and
the snapshot equals the OLD reader's; run #2 seeds **0**; a corrupted seed makes verify **abort before
cutover** (fail-closed).

## SC-007 — honest force provenance (FR-015)

Through the **real** `move-task` entry point, reject a WP across each of the five evidence-gated edges;
assert the **persisted** `StatusEvent.force` (read off `status.events.jsonl`) is falsy for all five and
truthy for a retained genuine-force edge (positive control). Re-point the enumerated existing tests.

## SC-008 — #2647 cwd invariant

Run an off-axis `InnerStateChanged` emit from a cwd **different** from the mission root; assert the write
lands at the stored-topology target branch, never a `Path.cwd()`-derived location.

## Architectural invariants (FR-013)

- No consumer reads a dynamic frontmatter field as authority (#2093).
- No field appears in both the static schema and the event-sourced slot set.
- An `InnerStateChanged` can never be reduced as a lane transition.
- `history[]` / `progress` have zero readers before deletion (`test_no_dead_symbols` reconciled).

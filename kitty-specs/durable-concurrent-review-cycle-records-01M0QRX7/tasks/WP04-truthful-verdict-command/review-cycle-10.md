---
affected_files: []
cycle_number: 10
mission_slug: durable-concurrent-review-cycle-records-01M0QRX7
reproduction_command:
reviewed_at: '2026-08-24T16:02:36Z'
reviewer_agent: reviewer-mission-audit
wp_id: WP04
---

# Mission-review hard-gate correction

The cross-repository `dependent_wp_planning_lane_lifecycle_smoke` scenario now
completes all four implementation/review cycles, but `accept` fails because the
last automatic approval leaves authoritative status state dirty.

## Blocking defect

For a modern `topology: lanes` mission with no explicit coordination branch,
`_transaction_topology_available(...)` is true and the approval transition is
committed to the mission target branch. The following runtime-state annotation
diverges: `emit_inner_state_changed_transactional()` tests only
`coordination_branch is None`, falls back to the uncommitted primary emitter,
and leaves `status.events.jsonl` plus `status.json` dirty. The committed ref has
the approval transition but not the trailing note.

## Required correction

- Make automatic annotations for stored `topology: lanes` use the same
  target-branch transaction availability as the transition.
- Preserve the intentional uncommitted parity for `topology: single_branch`
  and genuinely flat/legacy missions.
- Add a real Git regression proving the target ref contains both the approval
  transition and trailing annotation and the authoritative status files are
  clean after the command.
- Do not commit dossier snapshots as part of the status transaction; they are
  derived/ephemeral and separately excluded by preflight policy.
- Run focused tests, Ruff, strict mypy, and the relevant cross-repository E2E
  scenario before returning WP04 to review.

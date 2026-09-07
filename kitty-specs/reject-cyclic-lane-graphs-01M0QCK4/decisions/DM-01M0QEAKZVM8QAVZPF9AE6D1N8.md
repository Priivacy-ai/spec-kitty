# Decision Moment `01M0QEAKZVM8QAVZPF9AE6D1N8`

- **Mission:** `reject-cyclic-lane-graphs-01M0QCK4`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.cycle-validation-authority`
- **Input key:** `cycle_validation_authority`
- **Status:** `resolved`
- **Created:** `2026-08-23T13:52:55.291132+00:00`
- **Resolved:** `2026-08-23T13:58:39.652959+00:00`
- **Resolved by:** `robertDouglass`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Where should the single authoritative post-collapse cycle rejection live so mutating and --validate-only mission finalization cannot diverge?

## Options

- Inside compute_lanes after lane dependencies are built and before depths/manifests are accepted, returning a structured cycle error
- In a separate validator that every caller must invoke around compute_lanes
- Other

## Final answer

Place the authoritative post-collapse cycle rejection inside compute_lanes after lane dependencies are built and before depth calculation or manifest acceptance.

## Rationale

Both mutating and --validate-only finalization already call compute_lanes. Enforcing the invariant there prevents caller divergence and guarantees invalid manifests cannot reach lanes.json persistence. A pure internal detector will provide deterministic structured cycle facts, while the CLI owns human and JSON rendering.

## Change log

- `2026-08-23T13:52:55.291132+00:00` — opened
- `2026-08-23T13:58:39.652959+00:00` — resolved (final_answer="Place the authoritative post-collapse cycle rejection inside compute_lanes after lane dependencies are built and before depth calculation or manifest acceptance.")

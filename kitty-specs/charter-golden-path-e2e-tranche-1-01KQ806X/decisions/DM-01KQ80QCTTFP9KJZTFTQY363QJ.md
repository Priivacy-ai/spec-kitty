# Decision Moment `01KQ80QCTTFP9KJZTFTQY363QJ`

- **Mission:** `charter-golden-path-e2e-tranche-1-01KQ806X`
- **Origin flow:** `plan`
- **Slot key:** `plan.mission-strategy.choice`
- **Input key:** `composed_mission_strategy`
- **Status:** `resolved`
- **Created:** `2026-04-27T17:45:20.987691+00:00`
- **Resolved:** `2026-04-27T17:58:54.870154+00:00`
- **Other answer:** `false`

## Question

Should research commit to ONE composed mission (validated during Phase 0 against the live public CLI) and pin the test to it, or should the test implement a runtime fallback chain (software-dev → documentation → custom)?

## Options

- Pin to one mission chosen during research
- Runtime fallback chain
- Other

## Final answer

Pin to one mission chosen during research. Rationale: a golden-path E2E should be a stable product contract, not a runtime fallback harness. If the chosen mission later breaks, the test should fail loudly rather than pass via fallback and hide the regression. Resilience is next's job, not the test's.

## Rationale

_(none)_

## Change log

- `2026-04-27T17:45:20.987691+00:00` — opened
- `2026-04-27T17:58:54.870154+00:00` — resolved (final_answer="Pin to one mission chosen during research. Rationale: a golden-path E2E should be a stable product contract, not a runtime fallback harness. If the chosen mission later breaks, the test should fail loudly rather than pass via fallback and hide the regression. Resilience is next's job, not the test's.")

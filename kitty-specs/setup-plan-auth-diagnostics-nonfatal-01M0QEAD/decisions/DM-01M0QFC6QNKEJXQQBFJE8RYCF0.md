# Decision Moment `01M0QFC6QNKEJXQQBFJE8RYCF0`

- **Mission:** `setup-plan-auth-diagnostics-nonfatal-01M0QEAD`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.preflight-severity-boundary`
- **Input key:** `preflight_severity_boundary`
- **Status:** `resolved`
- **Created:** `2026-08-23T14:11:15.829157+00:00`
- **Resolved:** `2026-08-23T14:11:57.001366+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Should the nonfatal downgrade apply only to missing-auth outcomes, while all unrelated sync-boundary and preflight failures keep their existing severity?

## Options

- Yes, auth only
- Downgrade all sync preflight failures
- Other

## Final answer

Yes. Downgrade only missing-auth outcomes; retain the existing severity of unrelated sync-boundary and preflight failures.

## Rationale

_(none)_

## Change log

- `2026-08-23T14:11:15.829157+00:00` — opened
- `2026-08-23T14:11:57.001366+00:00` — resolved (final_answer="Yes. Downgrade only missing-auth outcomes; retain the existing severity of unrelated sync-boundary and preflight failures.")

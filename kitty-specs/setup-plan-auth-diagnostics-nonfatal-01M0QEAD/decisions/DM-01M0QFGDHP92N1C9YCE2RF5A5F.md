# Decision Moment `01M0QFGDHP92N1C9YCE2RF5A5F`

- **Mission:** `setup-plan-auth-diagnostics-nonfatal-01M0QEAD`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.structural-preflight-severity`
- **Input key:** `structural_preflight_severity`
- **Status:** `resolved`
- **Created:** `2026-08-23T14:13:33.878883+00:00`
- **Resolved:** `2026-08-23T15:24:12.619300+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

When setup-plan finds non-auth structural sync-boundary incoherence, should it still complete and return local verification while refusing only the hosted-sync side effect, or should the whole command retain its current exit-2 refusal?

## Options

- Complete local work; refuse only hosted sync
- Retain whole-command exit 2
- Other

## Final answer

Adopt the broader separation: setup-plan always completes local verification; only unsafe hosted-sync side effects are refused; structural sync-boundary problems are returned as separate structured diagnostics; the local verification result remains authoritative.

## Rationale

_(none)_

## Change log

- `2026-08-23T14:13:33.878883+00:00` — opened
- `2026-08-23T15:24:12.619300+00:00` — resolved (final_answer="Adopt the broader separation: setup-plan always completes local verification; only unsafe hosted-sync side effects are refused; structural sync-boundary problems are returned as separate structured diagnostics; the local verification result remains authoritative.")

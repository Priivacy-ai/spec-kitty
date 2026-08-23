# Decision Moment `01M0QKMB5KMS0SJWBQ8H8MDK91`

- **Mission:** `setup-plan-auth-diagnostics-nonfatal-01M0QEAD`
- **Origin flow:** `plan`
- **Slot key:** `plan.diagnostics.auth-unknown-v2`
- **Input key:** `auth_unknown_diagnostic_v2`
- **Status:** `resolved`
- **Created:** `2026-08-23T15:25:36.819283+00:00`
- **Resolved:** `2026-08-23T15:58:17.416822+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

If the canonical auth/session authority cannot determine auth state because its local store is unreadable or inconsistent, should setup-plan emit a distinct nonfatal SAAS_SYNC_AUTH_UNKNOWN diagnostic rather than label the operator unauthenticated?

## Options

- Distinct auth-unknown diagnostic
- Reuse unauthenticated diagnostic
- Other

## Final answer

Unknown and logged out are different states. Emit a distinct nonfatal SAAS_SYNC_AUTH_UNKNOWN diagnostic when the canonical authority cannot determine auth state.

## Rationale

_(none)_

## Change log

- `2026-08-23T15:25:36.819283+00:00` — opened
- `2026-08-23T15:58:17.416822+00:00` — resolved (final_answer="Unknown and logged out are different states. Emit a distinct nonfatal SAAS_SYNC_AUTH_UNKNOWN diagnostic when the canonical authority cannot determine auth state.")

# Decision Moment `01M0QF4S8QJH5407ERW4AMCSCM`

- **Mission:** `setup-plan-auth-diagnostics-nonfatal-01M0QEAD`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.auth-authority`
- **Input key:** `auth_authority`
- **Status:** `resolved`
- **Created:** `2026-08-23T14:07:12.663823+00:00`
- **Resolved:** `2026-08-23T14:11:14.682886+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Which authority should setup-plan use to distinguish a valid SaaS login from a genuinely logged-out state before emitting the nonfatal warning?

## Options

- Canonical local auth/session authority
- Actual hosted-sync delivery attempt
- Other

## Final answer

Use the canonical local auth/session authority. There is no other authentication authority; queue scope and hosted delivery attempts must not be used as substitutes.

## Rationale

_(none)_

## Change log

- `2026-08-23T14:07:12.663823+00:00` — opened
- `2026-08-23T14:11:14.682886+00:00` — resolved (final_answer="Use the canonical local auth/session authority. There is no other authentication authority; queue scope and hosted delivery attempts must not be used as substitutes.")

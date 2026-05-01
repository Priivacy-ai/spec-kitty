# Decision Moment `01KQEKE6CD6724DQY7FNXGB5ER`

- **Mission:** `auth-tranche-2-5-cli-contract-consumption-01KQEJZK`
- **Origin flow:** `plan`
- **Slot key:** `plan.revoke.client_structure`
- **Input key:** `revoke_client_structure`
- **Status:** `resolved`
- **Created:** `2026-04-30T07:07:49.006273+00:00`
- **Resolved:** `2026-04-30T07:11:19.089717+00:00`
- **Other answer:** `false`

## Question

Where should the revoke HTTP call live?

## Options

- RevokeFlow class in auth/flows/revoke.py
- Inline helper in _auth_logout.py

## Final answer

RevokeFlow class in auth/flows/revoke.py

## Rationale

_(none)_

## Change log

- `2026-04-30T07:07:49.006273+00:00` — opened
- `2026-04-30T07:11:19.089717+00:00` — resolved (final_answer="RevokeFlow class in auth/flows/revoke.py")

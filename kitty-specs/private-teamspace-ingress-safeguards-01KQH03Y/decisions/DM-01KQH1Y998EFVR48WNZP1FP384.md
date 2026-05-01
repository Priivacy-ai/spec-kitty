# Decision Moment `01KQH1Y998EFVR48WNZP1FP384`

- **Mission:** `private-teamspace-ingress-safeguards-01KQH03Y`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.rehydrate-module-location`
- **Input key:** `rehydrate_module_location`
- **Status:** `resolved`
- **Created:** `2026-05-01T05:59:45.193036+00:00`
- **Resolved:** `2026-05-01T06:22:45.711193+00:00`
- **Other answer:** `false`

## Question

Where should the /api/v1/me rehydrate function live?

## Options

- new_dedicated_module:auth/session_rehydrate.py
- extend:auth/http/transport.py
- method_on:auth/manager.AuthManager
- Other

## Final answer

Method on TokenManager (e.g. await token_manager.rehydrate_membership_if_needed()). Raw /api/v1/me HTTP fetch lives as a small private helper/module so transport and state mutation stay separable; TokenManager owns lock semantics, single-flight, negative cache, and StoredSession persistence.

## Rationale

_(none)_

## Change log

- `2026-05-01T05:59:45.193036+00:00` — opened
- `2026-05-01T06:22:45.711193+00:00` — resolved (final_answer="Method on TokenManager (e.g. await token_manager.rehydrate_membership_if_needed()). Raw /api/v1/me HTTP fetch lives as a small private helper/module so transport and state mutation stay separable; TokenManager owns lock semantics, single-flight, negative cache, and StoredSession persistence.")

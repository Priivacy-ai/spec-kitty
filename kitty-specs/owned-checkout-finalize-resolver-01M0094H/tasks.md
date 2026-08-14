# Work Packages: Finalize owned-checkout mission resolver

| ID | Work package | Depends on | Acceptance gate |
| --- | --- | --- | --- |
| WP01 | Red-first operation-context and topology tests | — | Caller-owned selection and conflict refusal are executable tests |
| WP02 | Shared anchor propagation and `finalize-tasks` integration | WP01 | Validate-only reads owned surface and preserves primary |
| WP03 | Architectural census, compatibility tests, and canary validation | WP02 | Covered consumers use one resolver and targeted suite is green |

## Delivery order

WP01 must fail before implementation. WP02 may change production code only after
the red result is recorded. WP03 is the final review and verification gate; no
wrapper switch or downstream mission acceptance is allowed before it passes.

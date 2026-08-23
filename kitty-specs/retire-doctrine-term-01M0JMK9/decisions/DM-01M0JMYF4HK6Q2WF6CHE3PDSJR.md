# Decision Moment `01M0JMYF4HK6Q2WF6CHE3PDSJR`

- **Mission:** `retire-doctrine-term-01M0JMK9`
- **Origin flow:** `specify`
- **Slot key:** `specify.scope.internal-identifiers`
- **Input key:** `scope_internal_identifiers`
- **Status:** `resolved`
- **Created:** `2026-08-21T17:12:24.977397+00:00`
- **Resolved:** `2026-08-21T17:13:29.483685+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Does the retirement of 'doctrine' cover internal code identifiers (src/doctrine/ package, module names, import paths), or only user/operator-facing language?

## Options

- User/operator-facing language only
- Full retirement including internal identifiers with shims
- Full retirement, hard break, no shims

## Final answer

User/operator-facing language only. Internal identifiers (src/doctrine/ package, module names, import paths) are out of scope for the retirement.

## Rationale

_(none)_

## Change log

- `2026-08-21T17:12:24.977397+00:00` — opened
- `2026-08-21T17:13:29.483685+00:00` — resolved (final_answer="User/operator-facing language only. Internal identifiers (src/doctrine/ package, module names, import paths) are out of scope for the retirement.")

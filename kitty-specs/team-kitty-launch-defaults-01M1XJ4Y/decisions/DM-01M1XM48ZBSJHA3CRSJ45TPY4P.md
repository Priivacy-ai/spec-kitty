# Decision Moment `01M1XM48ZBSJHA3CRSJ45TPY4P`

- **Mission:** `team-kitty-launch-defaults-01M1XJ4Y`
- **Origin flow:** `specify`
- **Slot key:** `specify.scope.sync-flag-disposition`
- **Input key:** `sync_flag_disposition`
- **Status:** `resolved`
- **Created:** `2026-09-07T09:45:27.275167+00:00`
- **Resolved:** `2026-09-07T09:46:11.985869+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

What happens to SPEC_KITTY_ENABLE_SAAS_SYNC and the SYNC_* names at launch: the four leftover gates (readiness nag, tracker commands, --from-ticket, owned-checkout guard) and the two opt-outs (pre-review gate skip, moment-handler import gate)?

## Options

- Delete the flag; hosted features are always available and auth decides. Add one explicit offline kill switch (e.g. SPEC_KITTY_OFFLINE=1) that suppresses all hosted egress incl. moments. Split the two opt-outs into their own explicitly named variables.
- Keep SPEC_KITTY_ENABLE_SAAS_SYNC as a =0 escape hatch only; everything else as in the first option
- Other

## Final answer

Delete SPEC_KITTY_ENABLE_SAAS_SYNC; hosted features always available, auth decides; add one explicit offline kill switch (working name SPEC_KITTY_OFFLINE=1) suppressing all hosted egress incl. moments; split the pre-review-gate skip and the moment-handler import gate into their own explicitly named variables.

## Rationale

_(none)_

## Change log

- `2026-09-07T09:45:27.275167+00:00` — opened
- `2026-09-07T09:46:11.985869+00:00` — resolved (final_answer="Delete SPEC_KITTY_ENABLE_SAAS_SYNC; hosted features always available, auth decides; add one explicit offline kill switch (working name SPEC_KITTY_OFFLINE=1) suppressing all hosted egress incl. moments; split the pre-review-gate skip and the moment-handler import gate into their own explicitly named variables.")

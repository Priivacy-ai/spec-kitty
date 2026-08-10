# Decision Moment `01KZJV6H7TW63M6ZGNM05XKM2S`

- **Mission:** `charter-synthesize-reconciliation-01KZJQN6`
- **Origin flow:** `specify`
- **Slot key:** `specify.reconciliation.drop-semantics-revised`
- **Input key:** `drop_semantics_revised`
- **Status:** `resolved`
- **Created:** `2026-08-09T08:45:58.906025+00:00`
- **Resolved:** `2026-08-09T08:45:59.972079+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Post-spec squad revision: default semantics for a synthesize rebuild that would drop still-backed on-disk graph/manifest content?

## Options

- preserve-and-warn
- refuse-with-prune

## Final answer

preserve-and-warn (supersedes 01KZJQP5K4C0VGNB53GZZT3QWP): library seam preserves-and-succeeds (never silent-drops, exit 0, warns); auto_refresh & activate consume it; --prune removes explicitly; non-zero refuse narrowed to manual CLI for genuinely-unpreservable removals (orphaned/backing-deleted without --prune, or unparseable overlay). Re-anchor to ADR 2026-07-26-3 + drg/merge.py conflict model (warn-not-block).

## Rationale

_(none)_

## Change log

- `2026-08-09T08:45:58.906025+00:00` — opened
- `2026-08-09T08:45:59.972079+00:00` — resolved (final_answer="preserve-and-warn (supersedes 01KZJQP5K4C0VGNB53GZZT3QWP): library seam preserves-and-succeeds (never silent-drops, exit 0, warns); auto_refresh & activate consume it; --prune removes explicitly; non-zero refuse narrowed to manual CLI for genuinely-unpreservable removals (orphaned/backing-deleted without --prune, or unparseable overlay). Re-anchor to ADR 2026-07-26-3 + drg/merge.py conflict model (warn-not-block).")

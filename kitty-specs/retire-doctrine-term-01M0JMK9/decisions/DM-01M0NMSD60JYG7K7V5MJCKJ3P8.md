# Decision Moment `01M0NMSD60JYG7K7V5MJCKJ3P8`

- **Mission:** `retire-doctrine-term-01M0JMK9`
- **Origin flow:** `plan`
- **Slot key:** `plan.inventory.manifest-persistence`
- **Input key:** `inventory_manifest_persistence`
- **Status:** `resolved`
- **Created:** `2026-08-22T21:07:22.432562+00:00`
- **Resolved:** `2026-08-22T21:07:24.277834+00:00`
- **Resolved by:** `operator`
- **Opened by:** `operator`
- **Other answer:** `false`

## Question

Is the per-hit manifest inventory-hits.tsv a committed repository artifact, or ephemeral evidence reproducible from the frozen base?

## Options

- Ephemeral evidence: generated and hash-pinned in inventory.md, reproducible from the frozen base, not committed (mission-local .gitignore); may be attached to the PR as an artifact
- Committed artifact under kitty-specs/

## Final answer

Ephemeral evidence: generated and hash-pinned in inventory.md, reproducible from the frozen base, not committed (mission-local .gitignore); may be attached to the PR as an artifact

## Rationale

Operator 2026-08-22: a ~90k-row TSV need not live in the repo; set-equality is proven by deterministic regeneration and recorded SHA-256/row counts in inventory.md, and WP05 re-derives it.

## Change log

- `2026-08-22T21:07:22.432562+00:00` — opened
- `2026-08-22T21:07:24.277834+00:00` — resolved (final_answer="Ephemeral evidence: generated and hash-pinned in inventory.md, reproducible from the frozen base, not committed (mission-local .gitignore); may be attached to the PR as an artifact")

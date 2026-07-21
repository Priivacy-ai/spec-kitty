# Decision Moment `01KY239G8EAZD7D1K37N5NM7NX`

- **Mission:** `doctrine-tension-edges-01KY1WPC`
- **Origin flow:** `plan`
- **Slot key:** `plan.migration.fr015-mechanism`
- **Input key:** `fr015_migration_mechanism`
- **Status:** `resolved`
- **Created:** `2026-07-21T10:24:37.646749+00:00`
- **Resolved:** `2026-07-21T10:30:33.796085+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

FR-015 requires shipping a downstream opposed_by compatibility path (D1 decided a migration/deprecation path is needed, not the mechanism). Which concrete approach should the plan commit to?

## Options

- New spec-kitty migrate subcommand that rewrites opposed_by -> edges (backfill-identity precedent), no deprecation window (immediate removal)
- Same migrate subcommand, but with a deprecation window (warn for N releases before hard removal)
- Upgrade-time diagnostic/warning only - no auto-rewrite command
- Other

## Final answer

New spec-kitty migrate subcommand (rewrite_opposed_by-style, modeled on backfill-identity) that rewrites org-pack YAML opposed_by usages -> in_tension_with/rejects edges. No deprecation window: schema drops opposed_by from additionalProperties:false in the same release; consumers run the migration once before/at upgrade time.

## Rationale

_(none)_

## Change log

- `2026-07-21T10:24:37.646749+00:00` — opened
- `2026-07-21T10:30:33.796085+00:00` — resolved (final_answer="New spec-kitty migrate subcommand (rewrite_opposed_by-style, modeled on backfill-identity) that rewrites org-pack YAML opposed_by usages -> in_tension_with/rejects edges. No deprecation window: schema drops opposed_by from additionalProperties:false in the same release; consumers run the migration once before/at upgrade time.")

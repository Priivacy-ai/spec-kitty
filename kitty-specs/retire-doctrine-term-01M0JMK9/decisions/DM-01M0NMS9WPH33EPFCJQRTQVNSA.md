# Decision Moment `01M0NMS9WPH33EPFCJQRTQVNSA`

- **Mission:** `retire-doctrine-term-01M0JMK9`
- **Origin flow:** `plan`
- **Slot key:** `plan.operator-override.historical-mission-archive`
- **Input key:** `historical_mission_archive_immutability`
- **Status:** `resolved`
- **Created:** `2026-08-22T21:07:19.062939+00:00`
- **Resolved:** `2026-08-22T21:07:20.765392+00:00`
- **Resolved by:** `operator`
- **Opened by:** `operator`
- **Other answer:** `false`

## Question

Does the extinction program rewrite or rename historical mission artifacts under kitty-specs/ (mission slugs, directory names, .md planning/evidence files) to reach the M6 zero gate?

## Options

- No: kitty-specs/ is an immutable historical archive; it is excluded from M5 rewrite and is the single fixed, enumerated exclusion root of the I6 audits alongside Git object history
- Yes: M5 rewrites/renames kitty-specs mission artifacts so all of HEAD reaches zero

## Final answer

No: kitty-specs/ is an immutable historical archive; it is excluded from M5 rewrite and is the single fixed, enumerated exclusion root of the I6 audits alongside Git object history

## Rationale

Operator decision 2026-08-22 (PR #3664 review): historical mission slugs and .md files under kitty-specs/ are never renamed or edited. Both inventory and terminal audits apply the fixed pathspec exclusion of kitty-specs/ (content and tracked pathnames); all other current-tree history (ADRs, docs, kitty-ops, research-outputs) remains M5 work as planned. This amends DM-01M0NDJ33GCKATG3H4BK4PAMNG's 'only Git object history excluded' wording.

## Change log

- `2026-08-22T21:07:19.062939+00:00` — opened
- `2026-08-22T21:07:20.765392+00:00` — resolved (final_answer="No: kitty-specs/ is an immutable historical archive; it is excluded from M5 rewrite and is the single fixed, enumerated exclusion root of the I6 audits alongside Git object history")

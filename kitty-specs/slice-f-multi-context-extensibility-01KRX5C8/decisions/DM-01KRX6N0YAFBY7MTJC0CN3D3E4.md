# Decision Moment `01KRX6N0YAFBY7MTJC0CN3D3E4`

- **Mission:** `slice-f-multi-context-extensibility-01KRX5C8`
- **Origin flow:** `plan`
- **Slot key:** `plan.cat7-orphans.glossary-prompts-rendering`
- **Input key:** `glossary_prompts_rendering_disposition`
- **Status:** `resolved`
- **Created:** `2026-05-18T09:28:39.627083+00:00`
- **Resolved:** `2026-05-18T09:33:11.990736+00:00`
- **Other answer:** `false`

## Question

Cat-7 orphans #8 + #9 (specify_cli.glossary.prompts + specify_cli.glossary.rendering) ship as dead code. Disposition for Mission C: WIRE (audit conflict-resolution pipeline + integrate), DELETE (remove the modules + their tests), or KEEP-WITH-RATIONALE (allowlist with a stronger justification + sunset date)?

## Options

- WIRE
- DELETE
- KEEP
- Other

## Final answer

DELETE — remove specify_cli.glossary.prompts and specify_cli.glossary.rendering modules and their tests. Rationale: 3+ years orphaned without operator demand for interactive conflict resolution; cleanest Cat-7 burn-down; mirrors HiC §5a.1 'no eventual deprecation' stance. This contributes 2 entries to the FR-113 Cat-7 shrinkage (from 10 → at most 7), letting the burn-down PR ship with 3 entries removed: doctrine.templates.repository + glossary.prompts + glossary.rendering = 10 → 7.

## Rationale

_(none)_

## Change log

- `2026-05-18T09:28:39.627083+00:00` — opened
- `2026-05-18T09:33:11.990736+00:00` — resolved (final_answer="DELETE — remove specify_cli.glossary.prompts and specify_cli.glossary.rendering modules and their tests. Rationale: 3+ years orphaned without operator demand for interactive conflict resolution; cleanest Cat-7 burn-down; mirrors HiC §5a.1 'no eventual deprecation' stance. This contributes 2 entries to the FR-113 Cat-7 shrinkage (from 10 → at most 7), letting the burn-down PR ship with 3 entries removed: doctrine.templates.repository + glossary.prompts + glossary.rendering = 10 → 7.")

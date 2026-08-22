# Decision Moment `01M0JWDEMKXQ5CMAE9PFEK8GF9`

- **Mission:** `retire-doctrine-term-01M0JMK9`
- **Origin flow:** `plan`
- **Slot key:** `plan.stack.shape`
- **Input key:** `stack_shape`
- **Status:** `resolved`
- **Created:** `2026-08-21T19:22:56.019764+00:00`
- **Resolved:** `2026-08-21T19:46:09.232301+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should the stacked retirement plan be shaped? The spec prescribes ordering (canonical authority first, then executable CLI surfaces with 3.x aliases, then prose/docs/prompts) but not granularity. Evidence-grounded recommendation: one mission per surface wave — (1) guard wave 0, (2) glossary + charter-bundle authority rewrite, (3) CLI executable surfaces with hidden aliases, (4) packs source rename, (5) skills/agent artifacts, (6) docs prose — plus a 7th mission explicitly deferred to the 4.0 milestone (alias removal + zero-doctrine audit). Alternative: coarser grouping into ~3 missions. Which shape do you want?

## Options

- Per-wave: 6 active missions + deferred 4.0 removal (recommended)
- Coarser: ~3 grouped missions + deferred 4.0 removal
- Other

## Final answer

Per-wave stack with atomic authority flip: M1 = glossary rewrite + charter-bundle update + guard arming in one mission/PR (closes the catfooding conflict where the guard would forbid 'doctrine' before replacement terms are canonical); M2 = CLI executable surfaces with hidden aliases + same-wave CI consumer updates; M3 = packs source rename; M4 = skills/agent artifacts with legacy alias skills; M5 = docs prose + AGENTS.md (ADR titles stay legacy); M6 = deferred to 4.0 milestone (alias removal + NFR-001 zero-doctrine audit). 5 active missions + 1 deferred. Operator approved 2026-08-21.

## Rationale

_(none)_

## Change log

- `2026-08-21T19:22:56.019764+00:00` — opened
- `2026-08-21T19:46:09.232301+00:00` — resolved (final_answer="Per-wave stack with atomic authority flip: M1 = glossary rewrite + charter-bundle update + guard arming in one mission/PR (closes the catfooding conflict where the guard would forbid 'doctrine' before replacement terms are canonical); M2 = CLI executable surfaces with hidden aliases + same-wave CI consumer updates; M3 = packs source rename; M4 = skills/agent artifacts with legacy alias skills; M5 = docs prose + AGENTS.md (ADR titles stay legacy); M6 = deferred to 4.0 milestone (alias removal + NFR-001 zero-doctrine audit). 5 active missions + 1 deferred. Operator approved 2026-08-21.")

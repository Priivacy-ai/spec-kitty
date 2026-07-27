# Decision Moment `01KY7AKYGKZFK202NQ37094T34`

- **Mission:** `lifecycle-gate-execution-context-01KY72GQ`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.primary-fallback-scope`
- **Input key:** `primary_fallback_scope`
- **Status:** `resolved`
- **Created:** `2026-07-23T11:08:52.115479+00:00`
- **Resolved:** `2026-07-23T11:14:55.080227+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Does the existing acceptance-matrix read fallback to feature_dir become fail-loud, or is it the legitimate flat-topology leg?

## Options

- keep as flat-topology leg, scope NFR-001 to coord-resolved
- convert to fail-loud
- Other

## Final answer

Fail loud, implemented by making the resolver TOTAL rather than fallback-based. The declared home for a flat/SINGLE_BRANCH/LANES topology is the primary feature_dir returned affirmatively; None then means only 'a coord home was declared but is unresolvable' and raises. Operator directive: 'flattened' is pre-topology residue and must be steadily removed as a load-bearing property, not reinforced -- do not strengthen ducttape. This mission adds no new dependence on 'flattened' and makes every resolver it touches total; full de-ducttaping of the ~66 'flattened' sites is a separate track.

## Rationale

_(none)_

## Change log

- `2026-07-23T11:08:52.115479+00:00` — opened
- `2026-07-23T11:14:55.080227+00:00` — resolved (final_answer="Fail loud, implemented by making the resolver TOTAL rather than fallback-based. The declared home for a flat/SINGLE_BRANCH/LANES topology is the primary feature_dir returned affirmatively; None then means only 'a coord home was declared but is unresolvable' and raises. Operator directive: 'flattened' is pre-topology residue and must be steadily removed as a load-bearing property, not reinforced -- do not strengthen ducttape. This mission adds no new dependence on 'flattened' and makes every resolver it touches total; full de-ducttaping of the ~66 'flattened' sites is a separate track.")

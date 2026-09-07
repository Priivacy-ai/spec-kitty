# Decision Moment `01M1VAHGZM8HE72QPHEGP6DS24`

- **Mission:** `dead-port-disposition-01M1TZVN`
- **Origin flow:** `plan`
- **Slot key:** `plan.dsl.pack-blocks`
- **Input key:** `pack_dsl_blocks`
- **Status:** `resolved`
- **Created:** `2026-09-06T12:19:26.836855+00:00`
- **Resolved:** `2026-09-06T12:20:15.701503+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

OD3: Delete the orphan states:/transitions: blocks from the three built-in mission.yaml files, or keep with an uninterpreted comment? MISSION_COMPAT_IGNORED_FIELDS stays either way.

## Options

- Delete blocks; keep compat tolerance
- Keep with comment
- Other

## Final answer

Delete the orphan states:/transitions: blocks from packs/built-in/missions/{software-dev,plan,research}/mission.yaml; MISSION_COMPAT_IGNORED_FIELDS (mission.py:59-67, :260-261) stays as third-party tolerance with a comment naming the retired DSL. Rationale: after FULL the blocks have no interpreter anywhere; shipped templates must not imply one; consumer overrides that still carry them remain tolerated.

## Rationale

_(none)_

## Change log

- `2026-09-06T12:19:26.836855+00:00` — opened
- `2026-09-06T12:20:15.701503+00:00` — resolved (final_answer="Delete the orphan states:/transitions: blocks from packs/built-in/missions/{software-dev,plan,research}/mission.yaml; MISSION_COMPAT_IGNORED_FIELDS (mission.py:59-67, :260-261) stays as third-party tolerance with a comment naming the retired DSL. Rationale: after FULL the blocks have no interpreter anywhere; shipped templates must not imply one; consumer overrides that still carry them remain tolerated.")

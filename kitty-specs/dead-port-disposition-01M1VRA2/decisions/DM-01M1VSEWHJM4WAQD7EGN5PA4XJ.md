# Decision Moment `01M1VSEWHJM4WAQD7EGN5PA4XJ`

- **Mission:** `dead-port-disposition-01M1VRA2`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.factory-substitution-seam`
- **Input key:** `factory_substitution_seam`
- **Status:** `resolved`
- **Created:** `2026-09-06T16:40:09.010634+00:00`
- **Resolved:** `2026-09-06T16:41:15.141247+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

The bridge will obtain the emitter from a factory instead of a concrete class. Fourteen test sites currently patch the class on the bridge module. What is the substitution seam for tests and for the future E3 producer?

## Options

- Named factory on the bridge module + registry hook
- Registry-only (no bridge-module patch point)
- Keep a class-shaped attribute for patch compatibility
- Other

## Final answer

Named factory on the bridge module + registry hook: runtime_emitter_for_mission() beside the Protocol/NullEmitter; register_runtime_emitter_factory()/reset pair for E3; minimal-import env gate forces NullEmitter; tests patch the factory name on the bridge module

## Rationale

_(none)_

## Change log

- `2026-09-06T16:40:09.010634+00:00` — opened
- `2026-09-06T16:41:15.141247+00:00` — resolved (final_answer="Named factory on the bridge module + registry hook: runtime_emitter_for_mission() beside the Protocol/NullEmitter; register_runtime_emitter_factory()/reset pair for E3; minimal-import env gate forces NullEmitter; tests patch the factory name on the bridge module")

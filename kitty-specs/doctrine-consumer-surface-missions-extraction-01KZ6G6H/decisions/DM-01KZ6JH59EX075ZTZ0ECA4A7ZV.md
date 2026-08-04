# Decision Moment `01KZ6JH59EX075ZTZ0ECA4A7ZV`

- **Mission:** `doctrine-consumer-surface-missions-extraction-01KZ6G6H`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.kernel-primitive-convergence`
- **Input key:** `kernel_primitive_convergence`
- **Status:** `resolved`
- **Created:** `2026-08-04T14:23:36.750437+00:00`
- **Resolved:** `2026-08-04T14:25:03.702360+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

FR-004's new kernel-owned sibling-path-resolution primitive and doctrine's existing pack_paths.py::_resolve_built_in implement a near-identical algorithm. Should this mission make doctrine's pack_paths.py delegate to the new kernel primitive (one canonical implementation, more surface area touched now), or ship the kernel primitive standalone and leave the convergence as a named follow-up (smaller diff now, two implementations survive a bit longer)?

## Options

- Converge now (doctrine delegates to kernel)
- Standalone now, converge later (named follow-up)

## Final answer

Converge now: doctrine's pack_paths.py::_resolve_built_in will delegate to the new kernel-owned primitive as part of this mission, one canonical implementation.

## Rationale

_(none)_

## Change log

- `2026-08-04T14:23:36.750437+00:00` — opened
- `2026-08-04T14:25:03.702360+00:00` — resolved (final_answer="Converge now: doctrine's pack_paths.py::_resolve_built_in will delegate to the new kernel-owned primitive as part of this mission, one canonical implementation.")

# Decision Moment `01KZ3VBAWZ1B5XC25EDGN99BJP`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `plan.constraints.c003-module-move`
- **Input key:** `c003_module_move_ruling`
- **Status:** `resolved`
- **Created:** `2026-08-03T12:59:59.775756+00:00`
- **Resolved:** `2026-08-03T13:00:44.770670+00:00`
- **Resolved by:** `operator (stijn-dejongh)`
- **Opened by:** `operator`
- **Other answer:** `false`

## Question

Does C-003 (no identifier renames in this mission) forbid WP06's extraction of four verdict-relevant bodies from tasks_move_task.py into a new tasks_verdict_persistence.py?

## Options

- permitted-conditionally
- forbidden

## Final answer

permitted-conditionally

## Rationale

C-003 permits WP06's module move, on two conditions. Grounds: (1) C-003's mechanism concern is the bulk_edit occurrence-map gate, which freezes a map over tokens the mission rewrites; a move that changes no token spelling produces no occurrence to map, so that gate never engages. (2) C-003's deferral target is the naming debt in #3158 items 1-2; WP06 proposes no new name, only a new home. (3) Direct repo precedent: tasks_move_task.py is itself the output of this exact operation (mission tasks-py-degod-wave2-01KWH9EQ), and its module docstring records the sanctioned mechanism - a lazy in-function 'from ...agent import tasks as _tasks' bridge so historical @patch('...agent.tasks.<sym>') sites keep intercepting, explicit 'as' re-exports in tasks.py, and a per-symbol seam checklist. CONDITION 1: the compat surface may not shrink. tasks.py re-exports _mt_gather_review_facts, _mt_fire_override_persist and _run_arbiter_override in explicit 'as' form, and test_tasks_compat_surface.py pins the latter two by name; every moved symbol must stay reachable as a tasks.<name> module attribute, or the move is an effective rename of the public path and becomes a genuine C-003 violation. CONDITION 2: _persist_approved_review_cycle (tasks_move_task.py:1712-1757) is a NESTED CLOSURE inside _mt_finalize_plan (1688-1802), not a top-level function. De-nesting it requires threading its captured locals into an explicit parameter list, which is a new signature and therefore a new identifier surface; it must be recorded as the INTRODUCTION of a new module-level function with the closure deleted, not waved through as a pure move. It is also referenced by name in tasks_transition_core.py:380 (the C-001 guard site) in explanatory prose, which goes stale unless updated in the same change. Conservative fallback if a strict move is preferred: leave that closure in place and move only the three top-level bodies, accepting that WP11/WP12 still reach back into tasks_move_task.py for it.

## Change log

- `2026-08-03T12:59:59.775756+00:00` — opened
- `2026-08-03T13:00:44.770670+00:00` — resolved (final_answer="permitted-conditionally")

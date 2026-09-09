# Decision Moment `01M20NNCDGD7T7WP3XYX256P4F`

- **Mission:** `upgrade-no-migrations-provisioning-fix-01M20NK8`
- **Origin flow:** `specify`
- **Slot key:** `specify.scope.deferred-followup-disposition`
- **Input key:** `deferred_followup_disposition`
- **Status:** `resolved`
- **Created:** `2026-09-08T14:09:59.728447+00:00`
- **Resolved:** `2026-09-08T14:19:02.953076+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

The 'true create-from-absent' fix (relax guard + extend recheck so upgrade bootstraps config.yaml on a never-init'd bare dir) is deferred. Should this mission (A) file a NEW tracked issue for it now as a deliverable, or (B) only note it as a deferred scope boundary in the spec?

## Options

- A: file a new tracked follow-up issue
- B: note-only in spec
- Other

## Final answer

A: file a new tracked follow-up issue — created #4047 on milestone 4.0.0, assigned to operator, with a note that pulling it forward may be needed for stability.

## Rationale

_(none)_

## Change log

- `2026-09-08T14:09:59.728447+00:00` — opened
- `2026-09-08T14:19:02.953076+00:00` — resolved (final_answer="A: file a new tracked follow-up issue — created #4047 on milestone 4.0.0, assigned to operator, with a note that pulling it forward may be needed for stability.")

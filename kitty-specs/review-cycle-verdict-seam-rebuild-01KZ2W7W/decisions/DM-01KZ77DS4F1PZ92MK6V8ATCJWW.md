# Decision Moment `01KZ77DS4F1PZ92MK6V8ATCJWW`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `fr007_residual_routing`
- **Input key:** `fr007_residual_routing`
- **Status:** `resolved`
- **Created:** `2026-08-04T20:28:46.095956+00:00`
- **Resolved:** `2026-08-04T20:28:49.333271+00:00`
- **Resolved by:** `Stijn Dejongh (operator)`
- **Opened by:** `claude-opus-5`
- **Other answer:** `false`

## Question

WP13 routed 8 of 13 FR-007 consumer sites through the single owner function. Four remain: three in files no WP owns (workflow.py::review, workflow_cores.py::has_prior_rejection, workflow_executor.py::implement_try_render_fix_mode_prompt -- all flagged by WP04 as residual), and one, resolve_review_verdict_facts, in tasks_verdict_persistence.py which WP13 now owns (granted for the revert bug) and which uses the exact bare wp_path.parent/wp_path.stem slug-divergence join T057 fixes. Route the owned one now, leave all four, or route all four?

## Options

- route-the-owned-one-now-record-the-three-as-residual
- leave-all-four-as-residual
- route-all-four-widening-ownership

## Final answer

route-the-owned-one-now-record-the-three-as-residual

## Rationale

OPERATOR-CONFIRMED. resolve_review_verdict_facts sits in tasks_verdict_persistence.py, which WP13 already owns, and its bare wp_path.parent/wp_path.stem join is the exact slug-divergence defect T057 fixes everywhere else -- so it is both a genuine FR-007 gap and a latent bug in an owned file, and closing it now is in-scope rather than scope creep. Route it through _resolve_wp_slug + _review_cycle_wp_dir like the other consumers; add a regression test proving it resolves a slug directory a bare-id join would miss. The three remaining sites (workflow.py, workflow_cores.py, workflow_executor.py) stay unrouted and are recorded as a bounded FR-007 residual: WP04 already named them, none is in any live WP's owned_files, and granting three more unowned files this late would be a large speculative scope expansion for no correctness gain today (they are readers whose divergence is the same class WP14's declared-reader-polarity work will revisit). WP17 must carry the three-site residual explicitly, not imply FR-007 is fully closed.

## Change log

- `2026-08-04T20:28:46.095956+00:00` — opened
- `2026-08-04T20:28:49.333271+00:00` — resolved (final_answer="route-the-owned-one-now-record-the-three-as-residual")

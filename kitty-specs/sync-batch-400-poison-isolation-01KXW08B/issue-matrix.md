# Issue matrix — sync-batch-400-poison-isolation-01KXW08B

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2736 | P0: one invalid event poisons its whole sync batch (innocents don't deliver) | fixed | WP02 (receiver bisection, release-blocker) + WP04 (live offline-queue disposition) + R1 post-review clamp (`_bisect_send` same-wp_id termination); anchor `tests/delivery/test_poison_batch_2736.py` green |
| #2755 | Batch-split de-dup — bisection is a 3rd `//2` split site | fixed | WP05 (rewire `_shrink_events_for_retry` onto shared `core.batch_partition.split_in_half` + behavioral/AST guard); mission #185 merged |
| #509 | SaaS transition-matrix alignment (accept `in_progress → planned` un-forced) | deferred-with-followup | spec-kitty-saas#509 (cross-repo; CLI FSM authoritative per WP03/C-003) |
| #510 | SaaS `wp_status_event_without_create` reducer semantics + orphan backfill | deferred-with-followup | spec-kitty-saas#510 (cross-repo; settle-vs-recompute tracked as risk) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

> **Note:** `#2736` and `#2755` reached terminal `fixed` at mission #185 merge — #2736 via WP02 (P0 bisection) +
> WP04 (live queue disposition) + the R1 post-mission-review clamp (same-wp_id termination), #2755 via WP05's
> SSOT retrofit. The two SaaS issues are genuinely cross-repo and stay `deferred-with-followup` (repo boundary =
> deferral boundary).

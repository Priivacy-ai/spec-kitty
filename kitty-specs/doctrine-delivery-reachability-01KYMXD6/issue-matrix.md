# Issue matrix — doctrine-delivery-reachability-01KYMXD6

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #3007 | Doctrine silence guards — predecessor mission (PR) | verified-already-fixed | merged `ed470756e` (this mission is its successor; not re-touched) |
| #3038 | Project-tier kind-mapping drift (`_PROJECT_KIND_DIRS` / `_KIND_TO_NODE_KIND`) | in-mission | WP03 fixes the `_PROJECT_KIND_DIRS` half; `_KIND_TO_NODE_KIND` remainder deferred to "#3038 proper" (plan issue ledger). Must resolve to terminal before mission `done` |
| #2981 | Kind-vocabulary consolidation (8-site drift) | deferred-with-followup | Only the project-tier mapping is touched (WP03); the headline `_activation_render.py` 8-vs-10 drift is out of scope under C-004. Follow-up tracked by #2981 |
| #2986 | Runtime→doctrine ratchet widening (61 function-local imports) | deferred-with-followup | Cited, not touched (plan issue ledger). Follow-up tracked by #2986 |
| #2994 | `operating-procedures` field-vs-edge decision | deferred-with-followup | Cited, not touched (plan issue ledger). Follow-up tracked by #2994 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

<!-- Verdicts sourced from plan.md "Issue ledger" (Closes / Advances-does-not-close / Cited-not-touched). #3038 is `in-mission` while WP03 is in flight; revisit to a terminal verdict at mission-done (expected: deferred-with-followup for the `_KIND_TO_NODE_KIND` remainder). -->


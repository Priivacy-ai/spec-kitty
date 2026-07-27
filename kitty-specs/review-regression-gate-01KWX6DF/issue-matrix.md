# Issue matrix — review-regression-gate-01KWX6DF

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #572 | Review-time regression gate | fixed | WP01 `63bbd8e8` (scope+runner+verdict engine) + WP02 `7d1f1a21` (for_review gate hook, warn-default/opt-in-block) — closes #572 |
| #1979 | Per-WP review blind spot (facet) | in-mission | This mission closes the review-time-blind-spot facet (WP01 engine + WP02 hook); the stale_assertions ownership facet is Phase 2 (out of scope, overlaps M3) |
| #2283 | Auto-scoped regression coverage (Phase 1) | in-mission | This mission is **Phase 1** (the review gate); #2283 stays OPEN for Phase 2 (stale_assertions ownership) + Phase 3 (CI dorny routing + venv) — separate later missions |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

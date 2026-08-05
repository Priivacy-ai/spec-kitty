# Decision Moment `01KZ7ZRVGA0J6PRA4FCC06YQ1C`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `wp16_census_check_ownership`
- **Input key:** `wp16_census_check_ownership`
- **Status:** `resolved`
- **Created:** `2026-08-05T03:34:14.794160+00:00`
- **Resolved:** `2026-08-05T03:34:17.843489+00:00`
- **Resolved by:** `Stijn Dejongh (operator)`
- **Opened by:** `claude-opus-5`
- **Other answer:** `false`

## Question

WP16's census fold (T071, FR-020) must re-point tests/architectural/test_verdict_seam_census.py from the hardcoded IC01/IC08 fragments to the folded verdict_seam_census.yaml, and deleting the fragments (T071 step 5) breaks the check outright. WP16 owns the fold target and the new name-truthfulness check but NOT test_verdict_seam_census.py, which WP01 and WP08 own -- both approved and closed. Sixth instance of the ownership-deadlock pattern. Widen WP16, keep fragments as a superset, or split the re-point to WP17?

## Options

- widen-WP16-to-own-test_verdict_seam_census.py
- keep-fragments-fold-as-superset
- defer-repoint-to-WP17

## Final answer

widen-WP16-to-own-test_verdict_seam_census.py

## Rationale

OPERATOR-CONFIRMED. FR-020's whole point is that the census check reads the ONE folded canonical document; leaving the check pinned to IC01/IC08 while a separate folded file exists is exactly the 'a document nothing consults' failure the fold exists to end, and deleting the fragments without re-pointing breaks the gate. So the re-point is intrinsic to the fold, not separable -- ruling out both the superset-without-repoint and the split-to-WP17 options (the latter also lands the fold half-wired across two WPs). Widening is the established, operator-confirmed pattern (WP11/WP12/WP13 owned_files widenings, WP18 authoring); no live WP owned the check, so no dependency-unordered overlap is created. WP16 already depends on WP08 (a co-owner of the check) via the dependency graph, and WP01 is a root every WP transitively follows, so the co-ownership is dependency-ordered. Added to create_intent as well because the check does not exist on the PRIMARY checkout (WP01 created it in its lane), the same mechanism WP06/WP11/WP12/WP13 use for tasks_verdict_persistence.py. finalize-tasks --validate-only passes at 18 WPs / 0 modified. Scope: re-point _CENSUS_FIXTURE_RELPATH to the folded file, fold IC01/IC04/IC08 rows in with provenance preserved, remove or re-point the IC08-specific loads, and confirm the check still reds on an unregistered member and still requires every retire row to name its FR -- NOT a rewrite of the check's invariants. SIXTH structural instance of the planning-time ownership assignment omitting a surface a WP must edit (test files pinning retired surfaces, cross-module compensators, generated/pinned-gate surfaces, and now the census GATE the fold re-sources); WP17 carries this as a systemic planning finding.

## Change log

- `2026-08-05T03:34:14.794160+00:00` — opened
- `2026-08-05T03:34:17.843489+00:00` — resolved (final_answer="widen-WP16-to-own-test_verdict_seam_census.py")

# Issue matrix — merge-squash-provenance-and-rollback-coherence-01KXRRB7

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2709 | Mission squash merge overwrites target-newer artifacts + drops acceptance provenance | in-mission | Red repro approved (lane-a `de68f9314`); fix owned by WP03 |
| #2711 | Merge rollback/resume leave committed done events opposed to reverted working status | in-mission | Red repro approved (lane-b `8578c050e`); fix owned by WP04 |
| #2658 | Mission where #2709/#2711 were observed (TF-046/049/066) | verified-already-fixed | Context only — observing mission, merged; this mission fixes the general defect, not #2658 |
| #1732 | `-X theirs` squash authority for planning artifacts (regression source) | verified-already-fixed | Context only — origin of the `-X theirs` clobber; merged. Its intent is preserved by C-002 (planning artifacts stay mission-authoritative) |
| #1827 | INV-5 merge-phase ordering ratchet | verified-already-fixed | Context only — Option A verified NON-violating (post-plan squad, code-verified against test_executor_phase_boundary.py); not modified |
| #2057 | Merge-core god-module decomposition | verified-already-fixed | Context only — merged refactor; referenced for symbol re-resolution (C-003), not modified |
| #2764 | Red-first reproductions for open P0 release-blockers | verified-already-fixed | Context only — merged; confirmed it did NOT already cover #2709/#2711 (WP01/WP02 not redundant) |
| #2770 | Shipped DRG left stale after activating a built-in procedure | verified-already-fixed | UNRELATED DRG/doctrine P0 — verified zero merge-core overlap (post-plan squad); fixed by dedicated session (`#2519` charter-freshness seam), now merged to upstream/main and rebased into this mission (charter gate clears) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

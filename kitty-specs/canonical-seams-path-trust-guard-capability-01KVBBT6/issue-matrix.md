# Issue matrix — canonical-seams-path-trust-guard-capability-01KVBBT6

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2022 | Consolidate merge.py path-trust into two canonical seams (Goals A+B) | fixed | WP01 `3b6a6dbcd` + WP03 (ensure_within_any) + WP04 `ea8ab33ad` + WP02; all opus/reviewer-renata approved; merged (mission #142) |
| #2017 | Workflow-guard friction umbrella — facet **B8** (line-pinned ratchets + maskable architectural CI gate) | deferred-with-followup | B8 delivered by WP05 `1d867635b` + WP06 `3fed379eb`; umbrella's other facets (A1–A4,B5–B7) remain — Follow-up: #2023 + #2017 |
| #1868 | Epic: canonical seams exist in name only — bind authority to type/owner | deferred-with-followup | this mission is one #1868 increment (#2022 native sub-issue); epic continues — followup #1868 |
| #2019 | Guard merge bookkeeping mission slug paths (point-fix) | verified-already-fixed | merged to main (`a35eb86a0`); FR-003 structurally covers its unguarded sibling-seam gap |
| #1931 | EPIC: Test quality & suite hygiene | deferred-with-followup | epic home for #2023 (B8 fix child); epic continues — followup #1931/#2023 |
| #1914 | no-op-stable gates umbrella | deferred-with-followup | C-staple-fallback cross-ref (plan C-003); not addressed here — followup #1914 |
| #1970 | Fix-don't-litigate directive (DIRECTIVE_025) | verified-already-fixed | standing directive (no bug to fix); honored as C-008 in every WP prompt — reference only |
| #1716 | Coordination topology authority (write-side) | deferred-with-followup | deferred topology (C-007 out-of-scope; `status_transition.py:295` pin untouched) — followup #1716 topology mission |
| #1796 | safe-commit / protected-branch guard coherence (epic) | verified-already-fixed | CLOSED on tracker; cross-ref / do-not-parent only |
| #1479 | META-TRACKER: P1 verified stabilization follow-through | deferred-with-followup | meta rollup, reference-only (never canonical parent); no direct action — followup #1479 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

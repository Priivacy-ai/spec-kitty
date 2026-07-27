# Issue matrix — sync-strict-json-auth-01KWA6KN

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2254 | integration-tests-sync test fails on main (auth-flow), hidden by sync path-filter | fixed | commit 708fb8d97 (re-pin seeding via production resolver + classify benign ingress skip); live-verified green via genuine path, 3/3 deterministic; reviewer-renata APPROVE |
| #2034 | gate-selection blind spots hide failing committed tests | deferred-with-followup | Deferred per decision DM-01KWA6Q7SPH9ZN20CH6EW68QDM; research.md recommends folding the CI-trigger broadening into #2034 rather than ballooning this mission. #2034 remains open as the follow-up. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

# Issue matrix — doc-quality-hardening-2245-01KW9AKV

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2245 | Doc-quality hardening: single authoritative inline-body-link gate + Common Docs residual debt | fixed | All seven #2245 items closed across WP01-WP08; gate green full-tree (0 dead links); PR #2272 |
| #2165 | Common Docs adoption (parent epic) | deferred-with-followup | This mission closes the doc-quality residual slice; parent epic remains open. Follow-up tooling gaps filed: #2273/#2274/#2275 |
| #651 | Common Docs (root epic) | deferred-with-followup | Root epic; this mission is one contribution (via #2245). Remains open. |
| #2225 | Common Docs structural move (Mission B) | fixed | Residual broken links left by PR #2225 repaired (27 ADR + 5 changelog); #2225 itself already merged. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

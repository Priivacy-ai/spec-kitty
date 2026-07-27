# Issue matrix — common-docs-consolidation-01KW3Q6M

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #651 | Public Site and Documentation Experience (epic) | deferred-with-followup | Follow-up: #651 — parent epic; continues beyond Mission A (the 3-ship split lives under it). |
| #2165 | Full Common Docs adoption (umbrella) | deferred-with-followup | Follow-up: #2192 — Mission A delivers the governed foundation (ADR + doctrine + report-only rulers); Mission B (#2192) closes #2165 on merge. |
| #2153 | charter generate discards documentation_policy answer | deferred-with-followup | Follow-up: #2153 — coordination flag; WP02 authors doctrine directly and AVOIDS the buggy documentation_policy codegen path (not claimed fixed). |
| #1652 | SEO audit for GitHub Pages docs site | deferred-with-followup | Follow-up: #1652 — sequenced AFTER Mission B (its titles/meta/canonical sit on FR-004 + NFR-002/003); Mission A must not regress it. |
| #1755 | DRG generator / freshness gaps | verified-already-fixed | CLOSED upstream; required reading for WP02's DRG wiring (the regenerate-graph footgun). Not re-opened by this mission. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

# Issue matrix — doctrine-glossary-architecture-consolidation-01KTNWFC

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1799 | Epic: Charter & Doctrine (umbrella) | deferred-with-followup | Follow-up: #1799 — umbrella epic stays open upstream; this mission delivers its doctrine-consolidation slice (all 10 WPs approved) |
| #1811 | Author planning/ticketing procedure, tactics, styleguide, toolguide | fixed | WP04 (procedure tracker-organisation-workflow + 2 tactics) + WP05 (styleguide planning-and-tracking + toolguide github-tracker), both approved; validated end-to-end by WP11 dogfood (SC-1 PASS) |
| #1805 | Restructure architecture/ vs docs/ split, refresh C4 drilldowns | fixed | WP02 (living layout, approved — review: 'the delivered layout IS the #1805 restructure') + WP03 (C4 refresh, 12 diagrams, approved) |
| #1397 | org-charter.yaml `extends:` additive multi-org config | fixed | WP08 (approved): canonical charter.org_extends resolver, fail-closed cycles/missing-base, parallel DFS deleted; contract round-tripped against shipped model |
| #1755 | Close DRG generator/freshness gaps + sanitize DRG/profiles | fixed | WP09 (regenerate-graph CLI + symmetric profile-edge validation, approved) + WP10 (5 new artifacts wired, graph 561 edges, approved). Residual: extractor styleguide/toolguide walk gap flagged for upstream ticket |
| #1418 | Defer runtime GlossaryScope for planning-and-tracking subset | deferred-with-followup | FR-011 resolved by WP01: defer recorded in `.kittify/glossaries/planning-and-tracking.yaml` header + `glossary/contexts/planning-and-tracking.md` (lane commit 3c74f7686); reassess under #1418 |
| #1804 | Ops ADR — pre/post-mission lifecycle (Op shape) | fixed | WP06 (approved): ADR 2026-06-11-1 op-as-first-class-execution-artifact ratifies the Op tier; #1804 gap marked CLOSED (SC-2) in the correlation matrix |
| #1802 | Ops ADR — shared Op shape | fixed | WP06 (approved): pre/post-mission lifecycle bound into the Op as intake/correction Ops (one abstraction, C-005) |
| #391 | Dogfood: split #391 dumping-ground epic using new doctrine | fixed | WP11 (approved): #391 organized per doctrine (6 type fixes, 5 provisional priorities, deferrals respected, #391 stays OPEN per operator decision 2026-06-11 / amended SC-6); SC-1+SC-6 PASS, 3 doctrine gaps fed back |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

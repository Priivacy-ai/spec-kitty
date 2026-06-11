# Issue matrix — doctrine-glossary-architecture-consolidation-01KTNWFC

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1799 | Epic: Charter & Doctrine (umbrella) | in-mission | umbrella epic for the mission; closes when child FRs land across WPs |
| #1811 | Author planning/ticketing procedure, tactics, styleguide, toolguide | in-mission | FR-001..004 — later WP (doctrine authoring) |
| #1805 | Restructure architecture/ vs docs/ split, refresh C4 drilldowns | in-mission | FR (WP02/WP03) — folded as source FR |
| #1397 | org-charter.yaml `extends:` additive multi-org config | in-mission | FR-008 — later WP |
| #1755 | Close DRG generator/freshness gaps + sanitize DRG/profiles | in-mission | FR-009 — later WP |
| #1418 | Defer runtime GlossaryScope for planning-and-tracking subset | deferred-with-followup | FR-011 resolved by WP01: defer recorded in `.kittify/glossaries/planning-and-tracking.yaml` header + `glossary/contexts/planning-and-tracking.md` (lane commit 3c74f7686); reassess under #1418 |
| #1804 | Ops ADR — pre/post-mission lifecycle (Op shape) | in-mission | FR-007 — later WP |
| #1802 | Ops ADR — shared Op shape | in-mission | FR-007 — later WP |
| #391 | Dogfood: split #391 dumping-ground epic using new doctrine | in-mission | FR-012 — later WP |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

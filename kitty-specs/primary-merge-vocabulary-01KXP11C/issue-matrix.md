# Issue matrix — primary-merge-vocabulary-01KXP11C

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2653 | Epic: disambiguate overloaded "primary"/"merge" terms | in-mission | spec.md Traceability; Track 1 partial (WP01 seeds the 7 sense entries), full epic spans Track 2 (#2730) |
| #1418 | Blocks glossary-pkg removal (#2727) | deferred-with-followup | spec C-003 — `src/glossary/` removal is OUT of scope. Follow-up: #2727 |
| #1629 | Epic parent of glossary-pkg removal | deferred-with-followup | spec C-003 — out of scope; bounded-context #2 under this epic |
| #1341 | Event-log SoT downstream of `glossary/` surface | deferred-with-followup | spec FR-006 note — downstream consumer flagged, not resolved in Track 1. Follow-up: #1341 |
| #648 | Static-site gen downstream of `glossary/` surface | deferred-with-followup | spec FR-006 note — downstream consumer flagged, not resolved in Track 1. Follow-up: #648 |
| #2701 | Terminology guard-skip risk | in-mission | spec FR-010/NFR-003 — guard proven to execute (WP01 review re-ran test_no_legacy_terminology.py green over new entries) |
| #2727 | Remove runtime glossary package `src/glossary/` | deferred-with-followup | spec C-003 — explicitly OUT of scope; blocked-by #1418, epic #1629 |
| #2729 | Track 1 mission tracking issue | in-mission | spec Traceability — this mission; WP01 lands FR-001/002/004 (glossary sense entries) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

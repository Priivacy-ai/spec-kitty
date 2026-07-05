# Issue matrix — bind-occurrence-map-guard-finalize-01KWQ4WC

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2345 | Bind occurrence_map_complete at plan/tasks-finalize so bulk-edit schema errors fail before implement | fixed | WP01 (`finalize-tasks` command gate) + WP02 (live `next`-loop `tasks_finalize` guard), both reusing `ensure_occurrence_classification_ready` |
| #1347 | Codify + validate bulk-edit occurrence-map schema at plan time (parent) | verified-already-fixed | Part (a) schema/template/skill shipped in #1347; part (b) residual finalize-time gate delivered by this mission (WP01/WP02) |
| #1790 | occurrence_map.yaml validated only at implement-claim, not at plan/finalize | fixed | Finalize/pre-implement gate delivered here; the additional rich-`occurrences` schema example remains out of scope and tracked on #1790 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

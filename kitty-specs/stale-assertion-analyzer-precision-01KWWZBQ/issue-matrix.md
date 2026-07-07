# Issue matrix — stale-assertion-analyzer-precision-01KWWZBQ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2031 | Stale-assertion analyzer: cross-file relocation false-positive storm | fixed | WP01 `117411ca` — head-importability suppression (origin-file-scoped, not bare-name); reviewer mutation-proved the collision guard; extraction storm 16.4→0 findings |
| #2343 | Stale-assertion: suppress generic removed literals | fixed | WP01 `117411ca` — genuineness-not-length rule (59-token pinned set); `"E001"`/1-char literals still emitted |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

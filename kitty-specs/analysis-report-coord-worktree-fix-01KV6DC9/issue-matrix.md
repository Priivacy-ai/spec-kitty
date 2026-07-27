# Issue matrix — analysis-report-coord-worktree-fix-01KV6DC9

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1989 | record-analysis writes outer-wrapper but manual analysis-report.md uses carrier format; implement gate rejects with cryptic error | in-mission | WP01 write-path anchor + read-side gate fix (commits on fix/analysis-report-coord-worktree-fix); WP02–WP04 complete the carrier reason code, recovery messages, and skill caution |
| #1981 | map-requirements resolves spec.md against coord worktree instead of main checkout | deferred-with-followup | Out of scope per spec.md "Out of Scope" (no broad resolve_mission_read_path refactor); tracked as open issue #1981; related new finding filed as #1991 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

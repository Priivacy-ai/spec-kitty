# Issue matrix — task-workflow-bug-fixes-01KV69BZ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1981 | map-requirements fails "spec.md not found" when coord worktree exists | fixed | commit 05fa959410de0ec6b0443eca686daface2219ac5 |
| #1982 | finalize-tasks --validate-only gives unhelpful error for planned-new-file | fixed | WP02 (lane-b) — YAML create_intent fragment added to validate_glob_matches error |
| #1983 | Host-CLI ⇄ source provenance contract | deferred-with-followup | Follow-up: #1983 out of scope per spec — requires separate design |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

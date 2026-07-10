# Issue matrix — merge-base-diff-ssot-01KX44SD

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2450 | SSOT: consolidate the duplicated git merge-base + diff --name-only idiom (4 sites) | fixed | WP01 delivered the canonical surface (git_merge_base/git_diff_names/merge_base_changed_files in core/vcs/git.py); WP02/WP03/WP04 repointed all **5** call sites (the count was 4→5: acceptance/_changed_workflow_files was the stranded 5th copy). All 4 WPs approved. One documented behaviour-required exception: tasks_dependency_graph keeps a direct `git diff` call because its fail-closed semantics (diff-failure→False) are unexpressible via the shared surface (see spec Out-of-scope / NFR-002 note). |
| #2438 | feat(review): auto-scoped review-time regression gate at move-task --to for_review | verified-already-fixed | Not closed by this mission — #2438 already shipped via its own PR; it is only the landing follow-up that surfaced #2450 (spec `Closes` names #2450 alone). Referenced for lineage, no code owed here. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

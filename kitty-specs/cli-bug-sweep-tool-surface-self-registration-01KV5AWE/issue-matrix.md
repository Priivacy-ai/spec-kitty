# Issue matrix — cli-bug-sweep-tool-surface-self-registration-01KV5AWE

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1947 | charter bundle validate + gitignored artifacts | in-mission | WP02 commit a635fc03f |
| #1949 | branch_naming mid8 test coverage gap | in-mission | WP01 |
| #1950 | tool_surface provider-discovery seam | in-mission | WP03/WP04 |
| #1951 | host-CLI source provenance contract | deferred-with-followup | Closed on GitHub as won't-fix per spec.md |
| #1953 | stale xfail in test_distribution | in-mission | WP01 |
| #1981 | map-requirements resolves spec.md from coord worktree instead of main checkout | fixed | WP05 (T020): resolve_feature_dir_for_slug replaces resolve_feature_dir_for_mission in map_requirements |
| #1982 | finalize-tasks --validate-only gives no hint for create_intent on planned-new-files | fixed | WP05 (T021): create_intent hint appended unconditionally after nearest-match suggestion in ownership/validation.py |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

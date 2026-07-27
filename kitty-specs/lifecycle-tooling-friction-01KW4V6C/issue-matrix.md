# Issue matrix — lifecycle-tooling-friction-01KW4V6C

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in
spec.md. `in-mission` rows must reach a terminal verdict before mission `done`.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2217 | Retrospect generator ignores tracer files | fixed | WP04 (Lane D) APPROVED — `_load_traces` extends `_build_ingestor_findings` seam; data-model gap entity-gated; commit `90e73c818` |
| #2218 | `specify` forces topology:coord (no flag) | fixed | WP03 (Lane C) APPROVED — `--topology` 4-value enum + conditional coord-branch mint + e2e single_branch implement+merge proof; commit `9bf529107` |
| #2219 | `backfill-topology` repo-global | verified-already-fixed | Fixed upstream `0e270b10a`/`5b8e317aa` (#2070/#1814); WP06 (Lane F) APPROVED — non-vacuous scope regression added. Follow-up: #2219 |
| #2220 | `owned_files` absolute-vs-relative mismatch | fixed | WP01 (Lane A) APPROVED — both `tasks/guidelines.md` copies → repo-relative + golden round-trip ratchet; commit `81212fe35` |
| #2221 | task-prompt-template missing frontmatter | fixed | WP01 (Lane A) APPROVED — template frontmatter completed (4 keys) + round-trip ratchet; commit `81212fe35` |
| #2222 | parallel-claim vcs-lock friction | fixed | WP02 (Lane B) APPROVED — exclude vcs-lock self-write from dirty-tree guard (lock-field-only); commit `cafaf6b56` |
| #2223 | issue-matrix guard strict/under-documented | fixed | WP05 (Lane E) APPROVED — finalize-tasks advisory lint reusing `validate_issue_matrix` engine; commit `20b15435b` |
| #1138 | Retrospective epic (parent of #2217) | deferred-with-followup | Parent epic; #2217 addressed in-mission. Follow-up: #1138 |
| #1619 | Mission runtime/state epic (parent of #2218/#2219) | deferred-with-followup | Parent epic; #2218 in-mission, #2219 verified-already-fixed. Follow-up: #1619 |
| #1676 | Tasks-authoring/ownership epic (parent of #2220/#2221) | deferred-with-followup | Parent epic; #2220/#2221 addressed in-mission. Follow-up: #1676 |
| #1795 | Implement/vcs epic (parent of #2222) | deferred-with-followup | Parent epic; #2222 addressed in-mission. Follow-up: #1795 |
| #2017 | Guard-friction epic (parent of #2223) | deferred-with-followup | Parent epic; #2223 addressed in-mission. Follow-up: #2017 |
| #2070 | Topology single-authority (upstream fix for #2219) | verified-already-fixed | Provided the `--mission` scope; cross-link as the landing change |
| #1814 | Pure read_topology (upstream fix for #2219) | verified-already-fixed | Provided the non-persisting read path; cross-link |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`,
`in-mission` (must reach a terminal verdict before mission `done`).

## Disposition notes (non-table)

- **Fixed** (#2217/#2218/#2220/#2221/#2222/#2223): all six WPs landed + independently reviewed (reviewer-renata) and APPROVED; resolved to `fixed` (terminal) ahead of merge.
- **#2219**: `verified-already-fixed` — the fix shipped upstream (#2070/#1814); WP06's non-vacuous
  scope regression now guards it. Close #2219 at merge.
- **Parents** (#1138/#1619/#1676/#1795/#2017): context only; remain open.
- **Upstream-fix refs** (#2070/#1814): cross-linked as the changes that already fixed #2219.

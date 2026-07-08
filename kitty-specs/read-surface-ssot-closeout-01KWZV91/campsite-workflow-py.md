# Campsite Cleaning — `workflow.py` (IC-04 opening)

Scout output (2026-07-08). `workflow.py` is a 2907-line god-module (46 top-level defs). IC-04 edits `implement`
(716 lines, Sonar cognitive complexity **109**) and `review` (560 lines, complexity **102**) — the file's two
worst offenders. Per DIRECTIVE_025 (tidy-first campsite-open), the SAFE items below are the **opening subtasks
of the IC-04 WP(s)**, done + tested *before* the routing edits. Source of Sonar findings: live SonarCloud REST
(`scripts/ci/sonarcloud_branch_review.sh`) — no file-scoped inventory markdown exists.

> **Caveat:** `ruff check --select C901` reports 0 offenders (cyclomatic); Sonar S3776 (cognitive, nesting-
> weighted) flags 6 functions. A clean `ruff` run is NOT proof this file is under the Sonar ceiling.

## Open Sonar issues (current-branch line refs)

| Rule | Sev | Line | Function |
|------|-----|------|----------|
| S3626 redundant return | MINOR | 1281 | `_ensure_workspace_materialized` |
| S1192 duplicated literal ×9 | CRIT | 1811/1816/1821/1899/1906/1910/2640/2644/2649 | spans `implement` + `review` |
| S3776 complexity 23 | CRIT | 537 | `_commit_workflow_change` |
| S3776 complexity 21 | CRIT | 2191 | `_find_first_for_review_wp` |
| S3776 complexity 18 | CRIT | 2270 | `_prepare_review_workspace` |
| S3776 complexity 66 | CRIT | 2000 | `_resolve_review_context` |
| S3776 complexity 109 | CRIT | 1284 | `implement` (IC-04 site) |
| S3776 complexity 102 | CRIT | 2347 | `review` (IC-04 site) |

## SAFE — WP-opening cleanup (inside/adjacent to the IC-04 sites, behavior-preserving + tested)

1. **Delete redundant `return` @1281** (`_ensure_workspace_materialized`, S3626). Zero risk, no new test.
2. **Extract `_render_isolation_banner(wp_id, mode)`** from `implement`(1807–1824)/`review`(2636–2652) — resolves
   S1192 (the 9× duplicated blank box line), shrinks both target functions ~35–40 lines combined *before* IC-04
   touches them. 2 pure-function tests (one per mode).
3. **Extract `_render_wp_prompt_wrapper(wp_text)`** from `implement`(1916–1924)/`review`(2795–2803) — byte-identical
   9-line block. 1 pure-function test.

## ADJACENT — boy-scout while here (optional, low-risk)

4. **Split `_commit_workflow_change`** (@537, complexity 23→15) into resolve/build/emit phases (transaction-vs-legacy
   selector extracted + focused tests). Not an IC-04 site but sits between the write-side seam helper and `implement`.

## Note-only (do NOT "fix")

5. **§3e — leave `review`'s two `resolve_feature_dir_for_mission` calls @2710/@2747 un-deduped.** They *look* redundant
   but IC-04 splits them: `@2710` → `read_dir` (baseline-test read), `@2747` → `write_target` (review-cycle write).
   Document in the WP that the divergence is intentional so a reviewer doesn't flag "accidental duplication."
6. **IC-04 routing is the crux, not cleanup:** introducing a `_resolve_workflow_read_dir` wrapper (mirroring the
   landed `_resolve_workflow_placement`) requires the `MissionArtifactKind` decision per site — it belongs in
   IC-04's first *routing* commit, not the campsite pass.

## OUT — track as separate issues (too large / unrelated to the 4 IC-04 sites)

7. **Full `implement`(109)/`review`(102) degodding** — even after SAFE 1–3 they're far above ceiling; a phase-split
   (dependency-gate / workspace-materialize / prompt-build / commit) is a dedicated degodding mission. → **filed #2464**
   (first pass in-mission, full cleanup deferred until after this mission lands).
8. **Resolver proliferation in this module** — `resolve_feature_dir_for_mission` vs `candidate_feature_dir_for_mission`
   (@2226) vs `_canonical_status_feature_dir` vs `primary_feature_dir_for_mission` all co-exist. → **filed #2465**
   (consolidate onto `PlacementSeam.read_dir` after this mission's routing lands).
9. `implement`'s @1468 (`main_repo_root`) vs @1663 (`repo_root`) root-arg inconsistency — part of IC-04's routing scope
   (site @1663), give it a targeted look during routing, not a pre-clean item.

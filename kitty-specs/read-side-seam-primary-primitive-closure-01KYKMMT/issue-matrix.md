# Issue matrix — read-side-seam-primary-primitive-closure-01KYKMMT

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

Every verdict below was checked against the live tracker (`gh issue view` / `gh pr view`) on
2026-07-28, not asserted from the spec text.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #3013 | accept does not converge on an unchanged tree: second run rewinds WP01 to 'claimed' | verified-already-fixed | CLOSED/COMPLETED on the tracker. This mission exists to close its *residuals* (#2886, #2824 comments, #3014), not to re-fix it — see spec.md Input. |
| #2886 | Coord-authority residual: route mission_setup_plan::_run_documentation_wiring | fixed | **WP04 CLOSED (approved reviewer-renata).** Both `_run_documentation_wiring` metadata reads + the audit-metadata write now resolve through one `placement_seam(...).read_dir(PRIMARY_METADATA)` (FR-013, SC-007); `test_coord_read_residuals_closeout.py` 11/11 green. |
| #2824 | accept: read_feature_dir resolves via PRIMARY_METADATA, not coord-aware, contradicts comment | verified-already-fixed | CLOSED/COMPLETED. Functional defect landed in `6923d1d40`, regression-green, independently re-verified; its *suggested* fix would have broken `lanes.json` placement (C-001 — `LANE_STATE` **is** PRIMARY). Only the two misleading comments remained; WP05 corrects them (FR-015). |
| #3014 | primary_feature_dir_for_mission is topology-blind and unpoliced (40 sites/21 files) | fixed | CLOSED/COMPLETED by **WP02** with the corrected census posted as a comment — the issue's premise was false (the primitive *is* policed on the anchoring axis; its fail-loud surface is zero; the stale figure was 40 where the live consumer census is 34/19). Confirmed by reviewer-renata in cycle 1. |
| #2906 | Lifecycle gate execution context + tool-artifact owner (retire 11 gate exemptions) | verified-already-fixed | MERGED. Cited by this mission only as *context*: it is the convergence/fold issue at `mission_runtime/resolution.py:1552` that makes the deliberate L2a/L2b divergence load-bearing. WP09 documents that layering and must cite **#2885** (not #2906) for the `surface_cannot_hold` guard. No code change here. |
| #3031 | P0: hosted-sync consent is opt-out and fail-open, recorded outside the project | deferred-with-followup | OPEN, and **deliberately red** — an honest-red P0 pin per ADR `2026-07-17-1`. Out of scope **by surface** (C-010): its surface is `sync/routing.py` / `is_sync_enabled_for_checkout`, the *sync fan-out* sense of "routing", zero overlap with placement. Marked `fast`, so it appears in every lane; recorded in `research/expected-reds.md` as not-ours. Tracked on #3031 itself. |
| #2966 | Write-target authority residuals: finish FR-002's PRIMARY reads, fold the 4th resolver | deferred-with-followup | OPEN. Explicitly out of scope per **C-006** and spec.md "Out of Scope". Remains on #2966. |
| #2964 | Leftover terminology mismatch: migrate feature* identifiers to mission* (canon) | deferred-with-followup | OPEN. Explicitly out of scope per **C-006** and spec.md "Out of Scope". Remains on #2964. Note this mission does *not* rename `get_feature_target_branch`, which is one of its sites. |
| #3007 | doctrine silence guards: close ten classes of declared-but-inert failure | deferred-with-followup | OPEN. Not a surface this mission touches (spec.md Assumptions records it as clear of every surface here). Remains on #3007. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

**Before mission `done`:** the one `in-mission` row (#2886) must reach a terminal verdict. `in-mission`
passes per-WP `approved` so a dependency chain is not blocked on its own downstream WPs, but it is
**rejected on `done`**. WP04 is its owner.

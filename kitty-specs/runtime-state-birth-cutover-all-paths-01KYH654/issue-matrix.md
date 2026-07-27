# Issue matrix — runtime-state-birth-cutover-all-paths-01KYH654

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2917 | Birth-cutover seam leaks non-`spec-kitty merge` landings (dogfood corpus re-drift) | fixed | Delivered by WP01 (anchor-pin da5dff98f) + WP02 (accept-stamp 28cb8670a) + WP03 (guard 30d5cb23e) + WP04 (CI wiring 51fd2ef9d); all approved. GitHub issue closes at mission PR merge. |
| #2920 | Birth-cutover-at-merge seam (merge-path only) | verified-already-fixed | Merged (cc287420b); this mission extends its coverage to all landing paths. |
| #2968 | Mechanical dogfood-corpus re-green hotfix | verified-already-fixed | Merged 4af076bc9 (`Refs #2917`); backlog cleared whole-corpus. |
| #2922 | Read-side placement seam migration | deferred-with-followup | Explicit non-goal (spec C-005); tracked as separate slice mission A (#2922 open). |
| #2966 | Write-target authority residuals | deferred-with-followup | Explicit non-goal (spec C-005); tracked as separate slice missions B/C (#2966 open). |
| #2964 | feature*→mission* terminology bulk edit | deferred-with-followup | Explicit non-goal (spec C-005); tracked as separate slice mission D (#2964 open). |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

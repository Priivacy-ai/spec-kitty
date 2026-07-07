# Issue matrix — landing-hygiene-01KWYRE1

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2439 | Review-prompt files accumulate unbounded within a repo (LC-7 residual) | fixed | WP01 (lane-a, `5793777`): bounded fail-safe prune in `review/prompt_metadata.py`, current-invocation preserved; 5 tests green |
| #2443 | Internal diff-coverage gate `--include` references a phantom module | fixed | WP02 (lane-b, `601da98`): repointed the phantom to `lanes/branch_naming.py` in BOTH authorities + glob-aware existence guard (reds specifically on the phantom) |
| #1931 | EPIC: Test quality & suite hygiene | deferred-with-followup | Parent epic; this mission closes two residual hygiene follow-ups (#2439, #2443). Follow-up: #1931 tracks the remaining epic work |
| #959 | Cross-repo review-prompt collision | verified-already-fixed | Already fixed by #959 (`<repo-id>` = `safe_repo_identifier`); WP01 preserves that isolation unchanged (NFR-001) |
| #2441 | Contract-ownership boundary | deferred-with-followup | Follow-up: #2441 — the separate design-first `contract-ownership-boundary-01KWYRE5` mission (in flight) closes it; explicitly out of scope here |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission`.

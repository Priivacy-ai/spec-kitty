# Issue Matrix — Placement-Port Residuals Closure

Mission `placement-port-residuals-closure-01KYDEF0`. One row per tracked issue (terminal
check maps 1:1). Seeded by the orchestrator at planning (FR-007); verdicts maintained at the
coord/PRIMARY level, never from a lane worktree.

**Parent epic: #2931** — children #2923, #2924, #2926, #2932 are native sub-issues (linked
2026-07-26). The epic/link work was done at the orchestrator/coord level, not from any lane.

| Issue | FR(s) | WP | Verdict | Evidence ref |
|-------|-------|----|---------|--------------|
| #2923 | FR-001, FR-002, FR-003, FR-004 | WP01, WP03 | fixed | Part A birth-cutover port hardening: FR-001/002 in WP01 (`_flip_phase` port-route + `PlacementMismatchError` fail-closed + partition-decouple, approved), FR-003/004 gate-tightening in WP03 (`migration/` prefix dropped from `BOUNDARY_SANCTIONED_PREFIXES` + lockstep pin, red-first proven, approved). |
| #2924 | FR-005, FR-006 | WP04, WP05, WP06 | fixed | Part B degrade/read hygiene: FR-005 WP04 (helper extracted resolve-first, MR-1 lockstep, 0 clones — approved cycle-3) + WP05 (status_transition pre-gate adoption, approved), FR-006 WP06 (one-site deleted-coord guard, red-first — approved). |
| #2926 | FR-008, FR-012 | WP03 | verified-already-fixed | Coord-seed `executor.py` MERGE_BOOKKEEPING allow-list. Census 2026-07-26 + WP03 review: `test_no_write_side_rederivation` + `test_guard_capability_call_sites` already GREEN on base `df19f85ae` (executor delegates to already-allow-listed `bookkeeping_commit.py`); greened by intervening PRs before rebase, verified by WP03. |
| #2932 | FR-009, FR-010, FR-011 | WP07, WP02 | verified-already-fixed | Part C golden-contract/raw-path/merge-committed-set. Census + WP07/WP02 reviews 2026-07-26: `test_no_raw_mission_spec_paths`, `test_mission_cli_golden_contract` (9 cmds), `test_merge_status_commit`, `test_merge_lane_planning_data_loss` all GREEN on base — greened by intervening PRs before rebase, verified in-mission. |
| #2920 | — | — | deferred-with-followup | Parent PR `coord-write-placement-closure` (merged). Its residuals are the scope of THIS mission, tracked/closed under child issues #2923, #2924, #2926, #2932 — not re-fixed as #2920 itself. |
| #2921 | — | — | deferred-with-followup | Out of scope (non-goal, spec.md:295): `repair_lane_mismatch` frontmatter-corruption fix. Remains tracked as its own follow-up #2921 unless a trivial campsite in an already-opened file. |
| #2922 | — | — | deferred-with-followup | Out of scope (non-goal, spec.md:286/294): read-side whack-a-read ~50-module remediation. Follow-up: separate mission #2922; FR-006 is deliberately scoped to one call site to avoid collision. |

## Notes

- **Child-issue scope** (native sub-issues of epic #2931):
  - **#2923** — Part A: birth-cutover placement-port hardening (FR-001/002/003/004 → WP01, WP03).
  - **#2924** — Part B: degrade-path + best-effort-read hygiene (FR-005/006 → WP04, WP05, WP06).
  - **#2926** — arch gate: MERGE_BOOKKEEPING asserted outside its flow at the coord-seed call site (FR-008/012 → WP03).
  - **#2932** — Part C: golden-contract + raw-path + merge-committed-set reds (FR-009/010/011 → WP07, WP02).
- **FR-007** (issue-matrix planning hygiene) has no external tracked issue — satisfied by this matrix being present + correct; WP03 verifies. Not a matrix row.
- **FR-008 rides under #2926** (same coord-seed `executor.py` call site as FR-012) — NOT a separate issue.
- **Part C already-green (rebase reality):** rebasing onto the much-newer `df19f85ae` means the honest-red-main gate/contract reds #2926/#2932 track were greened by intervening PRs; those FRs resolve to `verified-already-fixed` at `done`. The load-bearing Part A+B port-enforcement work (#2923/#2924) is the genuine in-mission deliverable.
- Do NOT ride the Part-C reds (FR-009/010/011) under #2923 (whose body covers A1/A2/A3 only) — they live under **#2932**.

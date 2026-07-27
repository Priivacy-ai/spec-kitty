# Issue matrix — name-vs-authority-remediation-01KTYGTE

One row per issue referenced in spec.md. `in-mission` = fixed by a WP in this mission (non-terminal; must
reach `fixed` / `verified-already-fixed` / `deferred-with-followup` before mission `done`).

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1884 | setup-plan blind to coord-branch commits (P0) | fixed | WP01 T002 (approved, lane-a 081a49ae8): is_committed verifies via resolve_placement_only ref (C-GATE-1); mutation-proofed pin RED-on-revert |
| #1883 | accept never completes under coord topology (P0) | fixed | WP02 (approved, lane-b f37fb2b00): ACCEPT_OWNED exact-relpath exclusion, 3-mode convergence test RED→GREEN; adversarial over-exclusion probe passed |
| #1885 | next returns unusable stub for fully-planned missions (P0) | fixed | Symptom verified fixed by PR #1850 (FR-004 pin, WP01); residual silent-stub hardened to structured QueryModeValidationError (FR-003, WP01 T003, mutation-proofed) |
| #1889 | agent decision crashes when coordination_branch declared, worktree missing (P0) | verified-already-fixed | Fixed by PR #1850 coord_worktree_materialized guard; WP01 T001 real-git pinning regression added; R3 branch-deleted row added by WP03 (CoordinationBranchDeleted) |
| #1860 | move-task mid8 handle fails 'no canonical status' | fixed | WP04 (approved, lane-d 71e8705e4): mission_branch_name_required + BranchIdentityUnresolved; 8 cluster-B sites dual-era migrated; #1860 regression suite (11 tests) |
| #1865 | Doctrine: triage-snapshot label reconciliation (+2 addenda) | fixed | WP06 (approved): triage-snapshot reconciliation + secondary-label coexistence patterns + provisional default in planning-and-tracking styleguide; doctrine validate OK |
| #1866 | Doctrine: canonical-tree carve-out for hygiene mutations | fixed | WP06 (approved): canonical-tree carve-out incl. label-only-mutation permission in tracker-organisation-workflow procedure |
| #1867 | Doctrine: canonical provisional-priority default | fixed | WP06 (approved): pagination rule generalized to all gh list surfaces in github-tracker toolguide + GITHUB_TRACKER.md |
| #1863 | DRG extractor never walks styleguides/toolguides | fixed | WP08 (approved, lane-h 8d4cca929): _resolve_path_ref walk + toolguide schema references field + graph regen (+24 suggests edges, byte-stable); ~20 curation orphans + java-implementer stale ref stay deferred on the ticket |
| #1896 | substantive-plan gate rejects bulleted Technical Context fields | fixed | WP01 T004 (approved): peer-field regex tolerates bullets + describe_technical_context_gap blocked_reason; bulleted-but-real context pin RED-on-revert |
| #1831 | implement prompt files collide across missions | verified-already-fixed | Fixed on this branch (Op-F, commit 0c8db2337); lands via PR #1895 |
| #1880 | typed exceptions for substring control flow | verified-already-fixed | Fixed on this branch (Op-G, f512cb300); lands via PR #1895 |
| #1881 | enum/constant sweep | verified-already-fixed | Fixed on this branch (Op-H b33eace72 + Op-I 358af429a); lands via PR #1895 |
| #1893 | StructuredError base | verified-already-fixed | Fixed on this branch (Op-K, 37bcb0803); lands via PR #1895 |
| #1894 | _fold_policies consolidation | verified-already-fixed | Fixed on this branch (Op-J, 53c0f4798); lands via PR #1895 |
| #1844 | rc42 release pipeline broken (P0) | deferred-with-followup | Follow-up: #1844 — standalone CI fix, out of topology scope (C-004, R-D verdict) |
| #1862 | implement gate hashes tasks.md wholesale | deferred-with-followup | Follow-up: #1862 — separate gate-design fix; not a name-vs-authority defect |
| #1868 | Epic: canonical seams exist in name only | deferred-with-followup | Follow-up: #1868 — parent epic; this mission delivers its topology+branch-identity slice |
| #1666 | Epic: execution-state & context domain-boundary | deferred-with-followup | Follow-up: #1666 — grandparent epic, stays open |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission`.

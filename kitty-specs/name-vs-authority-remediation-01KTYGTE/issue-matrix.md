# Issue matrix — name-vs-authority-remediation-01KTYGTE

One row per issue referenced in spec.md. `in-mission` = fixed by a WP in this mission (non-terminal; must
reach `fixed` / `verified-already-fixed` / `deferred-with-followup` before mission `done`).

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1884 | setup-plan blind to coord-branch commits (P0) | in-mission | FR-001 — verifier routed through resolve_placement_only's ref |
| #1883 | accept never completes under coord topology (P0) | in-mission | FR-002 — accept-gate idempotency seam |
| #1885 | next returns unusable stub for fully-planned missions (P0) | in-mission | FR-003 (residual hardening) + FR-004 (symptom verified fixed by PR #1850 — repro in research-p0-rootcauses) |
| #1889 | agent decision crashes when coordination_branch declared, worktree missing (P0) | in-mission | FR-004 — verified fixed on tree (coord_worktree_materialized guard); pinning test + proof, then close |
| #1860 | move-task mid8 handle fails 'no canonical status' | in-mission | FR-006 — branch-identity authority closes the handle-as-path class |
| #1865 | Doctrine: triage-snapshot label reconciliation (+2 addenda) | in-mission | FR-010 — deltas ready (research-fold-cluster §1) |
| #1866 | Doctrine: canonical-tree carve-out for hygiene mutations | in-mission | FR-010 |
| #1867 | Doctrine: canonical provisional-priority default | in-mission | FR-010 |
| #1863 | DRG extractor never walks styleguides/toolguides | in-mission | FR-012 — walk + toolguide schema field; ~20 orphans needing curation stay deferred on the ticket |
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

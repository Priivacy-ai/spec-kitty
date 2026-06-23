# Issue Matrix — Single-Authority Topology Cleanup & Dedup (01KVRJ6P)

Driver: #2070. This mission is the behavior-neutral cleanup + dedup carve-out
(C-007 of the seam mission `single-planning-surface-authority-01KVPR00`, PR
#2086, merged 2026-06-22). Issues actively implemented across this mission's WPs
carry `in-mission` (non-terminal — passes per-WP `approved`, MUST reach a
terminal verdict before mission `done`). Epic / already-shipped / preserved
issues carry their terminal verdict now.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2070 | Mission B — CommitTargetKind type eradication + richer-API adoption (the driver) | fixed | FR-001..FR-007 (type eradication + FLATTENED delete + topology=None absorption + C1/C2/C6 dedup). 18 WPs merged; pre-merge squad confirmed zero `CommitTargetKind` in src/, AST guard green. (FR-006 C2 inline-read sweep partial — ~62 reads remain; burn-down filed.) |
| #2086 | MissionTopology SSOT seam (merged predecessor PR) | verified-already-fixed | Merged 2026-06-22 (seam mission `single-planning-surface-authority-01KVPR00`); this mission is its C-007 cleanup carve-out and consumes the SSOT it landed (C-009) |
| #2062 | Un-backfilled flattened mission leaks the stale coord husk on the read path | fixed | FR-004 read-path `topology=None` absorption; RED-first proven (T002, drained WP06); squad-confirmed live (un-backfilled flattened → SINGLE_BRANCH/primary, C-001/C-004/C-005 KEEPs intact). |
| #1718 | Create-window transient (coord branch exists, husk not yet materialized) | verified-already-fixed | Preserved as C-005 KEEP — the create-window `probe_coord_state` EMPTY/DELETED transient probe is orthogonal to shape and stays intact; this mission must NOT flatten it (reverting the fix) |
| #1848 | Coord-deleted transient (coord worktree removed mid-mission) | verified-already-fixed | Preserved as C-005 KEEP — the coord-deleted transient probe stays intact; the `topology is None` arm collapsed by FR-004 was a shape stand-in, not this transient one |
| #2084 | `accept` blocks on spec-kitty's own bookkeeping files (topology-blind dirty gate) | fixed | FR-008 topology-aware residue allowance. NOTE: the pre-merge squad caught the gate calling `routes_through_coordination(CommitTarget)` (always-False → inert); fixed to `routes_through_coordination(resolve_topology(...))` so the gate genuinely filters coord residue (mission's own RED test now green). |
| #2085 | An orchestrated mission can't pass `spec-kitty accept` | fixed | FR-009 unchecked-tasks gate (derives from WP terminal status) — the in-scope half. Acceptance-matrix `overall_verdict` gate is the intentional C-010 human-review step (out of scope), tracked separately. |
| #1887 | Squash-merges leak coord-worktree paths into the target branch index | fixed | FR-012 single residue authority: all 4 `advance_branch_ref`/auto-rebase/post-merge-invariant sites delegate to `is_coordination_artifact_residue_path` (no per-site literal); WP13 13-cell gate test green; squad-confirmed. |
| #1891 | `agent … --json` broken: `CommitResult is not JSON serializable` | fixed | FR-013 `map-requirements --json` half: `CommitResult.to_dict()` renders `worktree_root: Path` as a string. NOTE: the regression test was DOA (stale `CommitTargetKind` import + a fake-signature drift) — caught by the squad, repaired, non-vacuous serialization proof confirmed. `agent action implement --json` half deferred (out of scope). |
| #2069 | MissionTopology SSOT seam (design predecessor) | verified-already-fixed | Fixed by PR #2086 (seam mission); this mission consumes the SSOT it landed (C-009) |
| #1868 | Canonical seams — authority in name only | deferred-with-followup | This mission binds the eradication to a CI AST guard (FR-011); Follow-up: the broader canonical-seams epic #1868 carries forward |
| #1716 | Single surface authority (epic facet) | deferred-with-followup | Follow-up: epic #1716 carries the remaining write-side cluster; this mission closes the type/dedup facet |
| #2007 | Execution-context coherence (parent epic) | deferred-with-followup | Follow-up: parent epic #2007 (this mission is one increment under it) |
| #1619 | Runtime/state overhaul (parent epic) | deferred-with-followup | Follow-up: parent epic #1619 (carries forward) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a WP in this mission; must reach a terminal verdict before mission `done`).

## Out-of-scope notes (do NOT fold)
- #2085 **acceptance-matrix** gate — genuine verification evidence, not redundant bookkeeping; not auto-satisfiable (C-010). The unchecked-checkbox half (#2085a) IS in scope via FR-009.
- The ~14 external richer-API callers from the original #2070 carve are **already SSOT-fed** (alphonso+randy correction); the only adoption site is the `resolve_action_context` WP-bearing branch (`resolution.py:1164-1194`) — a single NEEDS-CARE site, not a sweep.
- **Write-side death-spiral twin CARVED to #1716 (C-012)**: `coordination/transaction.py:200/230` (`_is_legacy_mission`) + `lanes/worktree_allocator.py:159` re-infer mission shape from `coordination_branch` absence — the write-path mirror of FR-004's read-side absorption. Folding write-path correctness into this behavior-neutral mission would break neutrality; recorded as considered-and-carved (squad-flagged, paula), NOT missed.

## Post-spec consistency squad (priti + paula + alphonso, 2026-06-22)
- **alphonso**: spec CONSISTENT-AND-GROUNDED — anchors real on `main`, hard arithmetic exact (CommitTargetKind 45/139, zero FLATTENED reads, zero `ensure_topology` callers, 481 LOC); FR↔KEEP boundaries crisp. No blockers. One SHOULD-FIX (load_meta count ~3× undersized) → folded into FR-006/NFR-004 re-baseline.
- **paula + priti convergence**: #2084 fold was undersized — the merge `advance_branch_ref` gates + post-merge invariant are #2084 siblings, and #1887 is their tracker ticket → folded as FR-012. #1891 rides FR-001 → FR-013 (conditional). Write-side twin → carve to #1716.
- Adjacent-but-separate (NOT folded, per squad): #1834 (NI verification timing), #1914 (no-op-stable umbrella epic), #1149 (accept cascade UX), #2017 (investigation). Not-related: #1782, #1862, #1734.

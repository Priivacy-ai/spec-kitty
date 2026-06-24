# Research: Write-Surface Coherence

Phase 0 consolidation. Most of this was resolved by the post-spec adversarial
squad (alphonso / debbie / paula / priti, 2026-06-23), which live-traced the
actual seams. Findings are recorded as Decision / Rationale / Alternatives.

## D-1 — The seam is a single shared placement authority, not N resolvers

- **Decision**: Treat the change as a **bifurcation of `resolve_placement_only`**
  (consumed via `commit_for_mission`) by artifact class, made in the `use_coord`
  arm at `commit_router.py:124`.
- **Rationale**: Live trace (debbie): `spec-commit → commit_for_mission →
  resolve_placement_only` returns `CommitTarget(ref=coordination_branch)` for a
  coord mission, for **both** planning and status commits. There is already one
  entry point and one authority — the split is that it doesn't distinguish
  artifact class. Fixing the one router arm closes all ≥7 callers.
- **Alternatives rejected**: "Converge 6 commands onto one resolver" (the original
  spec framing) — wrong: they already delegate to one authority; a per-command
  patch would leave analyze/tasks/accept routing planning to coord (the "fixed 3
  of N" trap).

## D-2 — Bifurcate by explicit artifact class, not by inference

- **Decision**: The artifact class (planning vs status/bookkeeping) is an
  **explicit input** to the placement authority, threaded from the caller.
- **Rationale**: `resolve_placement_only` is shared by planning (`commit_router`)
  and status (`status_transition.py:332`) callers; inferring class from paths is
  fragile. Status routing must remain unchanged (C-001).
- **Alternatives rejected**: Inferring class from filename patterns (brittle);
  a second parallel resolver (violates C-006 "no parallel read resolver" — and the
  bifurcation is a destination split, not a new resolver).

## D-3 — Protected-primary: require a feature branch (no coord transit)

- **Decision**: Planning commits require a **non-protected feature `target_branch`**;
  a coord-topology mission on a protected `target_branch` is refused with guidance
  to start a feature branch (operator decision 2026-06-23).
- **Rationale**: debbie corrected the spec's causal framing — coord routing is
  **topology-driven**, not protection-driven; the deadlock guard is `safe_commit`
  step 6 (`ProtectedBranchRefused`/`GuardCapability`). Requiring a feature branch
  removes the deadlock by invariant, with no coord-transit special case (cleaner
  than transiting coord for the commit landing).
- **Alternatives rejected**: Transit the coord-worktree materialization for the
  commit landing only (more plumbing, keeps a coord special case).

## D-4 — Shared coord-worktree helpers are entangled; govern them explicitly

- **Decision**: Add explicit handling (FR-005/IC-03) for `_planning_commit_worktree`,
  `_materialise_coord_worktree` staging, `_try_advance_ref` (#1878), and the
  `is_coordination_artifact_residue_path` dirty-filter once planning no longer
  transits coord.
- **Rationale**: alphonso — planning and status currently share the coord worktree,
  staging copy, and ff-advance; removing planning-on-coord changes their meaning.
  The ff-advance fast-forwarded primary to a coord HEAD mixing planning+status.
- **Alternatives rejected**: Leaving the helpers untouched (would leave dead
  ff-advance on the planning path + an orphaned `target_branch` param).

## D-5 — Read path must stop consulting the coord husk for planning artifacts

- **Decision**: After writes are primary-always, the planning **read** path must
  not fall back to the coord husk for planning artifacts (FR-006/IC-04).
- **Rationale**: paula — a stale pre-mission coord copy could shadow primary truth
  (the #2062 stale-coord class). The read side converged in 01KVRJ6P but still has
  `consults_coord_husk` arms (`_read_path_resolver.py`, `_coord_mid8`).
- **Alternatives rejected**: Assuming the read side is fully done (it is for status
  transients #1718/#1848 — KEEP those — but not for planning-artifact husk reads).

## D-6 — #2100 fold sized to in-mission sites; name the duplicate `load_meta`

- **Decision**: Route only the ~3 inline meta reads in the touched modules
  (`agent/mission.py`) through canonical `load_meta`; name/reconcile the duplicate
  `load_meta` at `task_utils/support.py:363`. Defer the remaining ~53-site backlog.
- **Rationale**: All four reviewers — "~62" is a repo-wide #2100 figure (real count
  56); the in-mission subset is ~3. Folding the whole backlog would balloon the
  diff with unrelated modules.
- **Alternatives rejected**: Folding the full #2100 backlog here (scope creep, no
  relationship to write-surface coherence).

## D-7 — Verification is behavioral, not structural

- **Decision**: NFR-002 guard asserts **two refs** from a coord-topology fixture
  (planning→primary `target_branch`, status→coordination), plus red-first repro of
  the split and a flattened-regression proof.
- **Rationale**: paula/DIRECTIVE_041 — a "resolved in exactly one function" count
  passes vacuously today (one authority already exists) and proves nothing.
- **Alternatives rejected**: Structural single-locus count (tautological).

## Anchors verified (alphonso)

All named anchors exist and are correctly characterized:
`primary_feature_dir_for_mission` / `resolve_handle_to_read_path` /
`candidate_feature_dir_for_mission` (`_read_path_resolver.py`); `setup_plan` /
`check_prerequisites` (`_primary_anchored_feature_dir`, PR #2089) / `finalize_tasks`
(`agent/mission.py`); `spec-commit` + `map-requirements`; `resolve_placement_only` /
`resolve_topology` / `routes_through_coordination` / `CommitTarget` (`mission_runtime`);
`load_meta` family (`mission_metadata.py`).

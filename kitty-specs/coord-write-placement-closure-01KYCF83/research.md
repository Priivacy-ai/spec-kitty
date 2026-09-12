# Phase 0 Research — Coord Write-Placement Closure & Birth-Cutover

Consolidated from the pre-spec grounding (a 4-lens #2917 squad + a 2-lens #2841-residual squad) and the spec-validation squad. Full narratives: `docs/plans/engineering-notes/2841-residual-2917-mission-scope.md`, `docs/plans/engineering-notes/2917-runtime-state-birth-cutover-research.md`. All anchors fact-checked ACCURATE against `feat/coord-write-placement-closure`.

## D-01 — Enforcement: whole-tree AST gate, not an allowlist

- **Decision**: replace `_CHECKOUT_GRAMMAR_MODULES` (17 modules) in `test_no_write_side_rederivation.py` with a whole-tree `src/` AST scan; extend `test_safe_commit_import_boundary.py` to assert `target=CommitTarget(...)` is seam-derived. A small, individually-justified sanctioned-primitive exclusion list replaces the module allowlist.
- **Rationale**: #2874's ratchet is allowlist-scoped, so a new writer in any unlisted module silently recreates the split-brain — the inverse of "unrepresentable."
- **Alternatives**: keep the allowlist (rejected — the residual itself); a runtime guard (rejected — arch gate is cheaper and pre-merge).

## D-02 — Birth seam at merge, reusing `cutover_mission`

- **Decision**: stamp the cutover at the merge bake stage, reusing `cutover_mission` (the sole `status_phase` writer). The `_bake_mission_number` hook (`merge/ordering.py`, from `_phase_bake_and_pre_target_done`) is a proven structural twin. **Timing is pre-target** (`executor.py:1319` precedes `_phase_mission_to_target`), so the PRIMARY meta flip **rides the mission→target merge atomically** — abort ⇒ never reaches target ⇒ consistent. (An earlier draft mis-stated "after target durable"; corrected.)
- **Rationale**: a bare create/finalize stamp is *provably wrong* — while `implement` still dual-writes runtime, verify reds the moment work accrues (the 12 prove it). Merge is the one moment runtime is complete + stable.
- **OPEN for IC-08** (surfaced by the post-plan squad): `cutover_mission(feature_dir)` is single-`feature_dir`; the meta→PRIMARY / seed-events→COORD split needs either a two-target spine form or delegation to the coord projection, with a transactional/resume-heal envelope so a crash between the two writes cannot half-birth a mission. Decide relocate-vs-ride-merge for the PRIMARY leg in tasks.
- **Alternatives**: create-time stamp (rejected — vacuous verify then re-drift); a new flip-only writer (rejected — forks the sole-writer invariant, C-004).

## D-03 — Event-source exactly two authoring paths (not broad retirement)

- **Decision**: event-source only the claim fields (`shell_pid`/`agent`) and subtask-completion (`tasks.md` checkboxes), per #2684, so nothing un-seeded accrues; then a birth-stamp is valid.
- **Rationale**: these two are the only authoring paths that make `read_legacy_runtime().has_evictable_state()` true post-cutover; retiring them closes the drift source without the broad #1619 program.
- **Alternatives**: retire all dual-writes (rejected — #1619 scope, C-002); leave authoring and rely on the merge seam only (rejected — merge-only re-migrates every wave; paula's whack-a-field).

## D-04 — `agent mission repair` is a new command, not `doctor --fix` growth

- **Decision**: add a dedicated `agent mission repair` for pre-existing content split-brain — forward-only under strict-ancestor + clean worktree, fail-loud with a diff otherwise. Keep `doctor coordination --fix` minimized (Gap-1, FF-only).
- **Rationale**: prevention (#2874) cannot cure an already-diverged corpus; #2874's C-003 explicitly walls off growing `--fix` into arbitrary-drift repair.
- **Alternatives**: grow `doctor coordination --fix` (rejected — C-003); manual git surgery (rejected — not reproducible/safe).

## D-05 — meta.json routing extends the port, not a re-architecture

- **Decision**: give `PRIMARY_METADATA` (today `commit_target=None`) a partition-aware write target by extending the existing port kind-mapping; route `write_meta`/`_flip_phase`/`_bake_mission_number` accordingly.
- **Rationale**: enables the coord/primary two-partition birth-write (meta→PRIMARY, seed events→COORD) that a single-`feature_dir` cutover cannot express.
- **Alternatives**: re-architect `MissionArtifactHome`/topology (rejected — C-002, out of scope → #1619).

## D-06 — Read-side enforcement mirrors write routing, reconciled with #2906

- **Decision**: route every mission-artifact read through `artifact_home_for(kind).read_surface`, fail-loud on partition mismatch; add a read-side arch gate symmetric to the write gate. Reconcile with #2906's existing read-gate guards (they refuse a substituted surface at accept-time) — the new authority generalizes, it does not double-guard.
- **Rationale**: #2874 closed writes; reads are still fixed one-at-a-time (whack-a-read). Symmetric completion closes the loop.
- **Alternatives**: keep advisory reads (rejected — the residual); block only accept-time reads (rejected — leaves other read sites ambient).

## D-07 — Front-load to unblock; migration retained for backward flow

- **Decision**: IC-01 runs `migrate backfill-runtime-state` over the 12 drifted missions and commits (idempotent, deterministic seeds). The one-time migration is retained for legacy corpora + consumer-upgrade backward flow; the birth seam owns forward flow.
- **Rationale**: clears the 3.2.6 CI red immediately, independent of the structural work; the two coexist on the same `cutover_mission` spine.
- **Open item resolved**: cold-upgrade strip-ordering (pre-3.0→3.2.6) is a pre-existing, orthogonal caveat — noted, not owned here.

## Resolved / no open NEEDS-CLARIFICATION

All design unknowns were resolved by the two grounding squads + fact-check. No `[NEEDS CLARIFICATION]` markers carried into `plan.md`.

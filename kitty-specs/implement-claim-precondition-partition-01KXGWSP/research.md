# Phase 0 Research — Partition-Aware Implement-Claim Precondition

All open questions were resolved by the pre-spec research squad
(debugger-debbie · researcher-robbie · paula-patterns) and the pre-planning
squad (planner-priti · paula-patterns). No `NEEDS CLARIFICATION` remains.

## Decision 1 — Locus of the fix: the consumer, not the placement mint

- **Decision**: Fix the implement-claim precondition consumer
  (`resolve_planning_artifact_staging` and its helper trio); do **not** touch the
  single-ref placement mint (`_assemble_artifact_placement_fragment` /
  `ArtifactPlacementFragment` in `mission_runtime/*`).
- **Rationale**: The single-ref fragment is *correct* for status events (which do
  route to the coordination branch). The bug is consumers treating PRIMARY planning
  artifacts as if they shared that ref. The write path (`commit_router`) and read
  resolver (`surface_resolver`, WP08) already honor the per-kind partition; the
  claim precondition is the lone straggler. `mission_runtime/*` is also HOT with the
  placement-seam SSOT / #2173 work — editing it would collide.
- **Alternatives rejected**: (a) Widen `_exclude_coord_owned`'s name-set — perpetuates
  ad-hoc name matching alongside the real per-kind authority. (b) Route implement-claim
  through `commit_router.commit_for_mission` — the right *eventual* shape, but a large
  blast radius owned by the #2160 cluster; deferred, not this fix.

## Decision 2 — One pure ref resolver as the seam

- **Decision**: Introduce `resolve_precondition_ref(coord_branch_for_filter: str | None) -> str | None`
  in `implement_cores.py`, the single owner of "which git ref does the working-tree
  precondition compare against." PRIMARY planning artifacts resolve to the
  primary/target ref (HEAD on a flat/primary checkout); COORD-owned files resolve to
  the coordination ref. All three helpers consume the resolver.
- **Rationale**: Today `_files_changed_vs_ref:417` short-circuits on `None`
  (`if not ref: return files`) while `_committed_meta_mapping:249` and
  `_drop_runtime_frontmatter_only_wp:387` fall back to `ref or "HEAD"`. That
  inconsistency *is* the defect. Centralizing it (a) removes the asymmetry, (b) folds
  the duplicated `ref or "HEAD"` idiom (SAFE campsite), and (c) exposes a pure
  `(str|None) -> str|None` function with exhaustive, subprocess-free unit coverage.
- **Alternatives rejected**: Per-helper inline conditionals — reintroduces the
  scattered legacy-resolver pattern the charter forbids ("no legacy resolver paths").

## Decision 3 — Reuse the per-kind partition authority

- **Decision**: Classify artifacts via `mission_runtime/artifacts.py`
  (`kind_for_mission_file` / `is_primary_artifact_kind` / `_PRIMARY_ARTIFACT_KINDS`),
  mirroring `commit_router._group_files_by_partition`.
- **Rationale**: Single canonical authority (NFR-004). #2549's 2026-07-11 correction
  confirms this module is the *designed* router. No parallel kind mapping.
- **Alternatives rejected**: A local allow/deny list in `implement_cores.py` — a
  second source of truth that will drift.

## Decision 4 — Red-first through the pre-existing gate

- **Decision**: Reproduce via `_ensure_planning_artifacts_committed_git:494` reached
  through `spec-kitty agent action implement`; harness template
  `test_implement.py::test_committing_content_already_on_coord_is_noop`. RED =
  non-empty staging for feature-branch-committed artifacts; GREEN = empty, claim
  proceeds, topology unchanged.
- **Rationale**: DIRECTIVE_041 / bugfix red-first — drive the real entry point, not a
  hand-rolled helper, so the test proves the user-visible behavior.
- **Alternatives rejected**: Asserting only on the pure resolver — necessary but not
  sufficient; it wouldn't prove the end-to-end claim no longer aborts.

## Decision 5 — Work-package shape and sequencing

- **Decision**: 2 dependency-sequenced WPs under LANES topology (WP01 seam+consumers+
  unit tests+re-pin; WP02 red-first integration + move-task regression + docs). Not 3
  parallel lanes.
- **Rationale**: `resolve_planning_artifact_staging` has two call sites
  (`implement.py:542`, `tasks_move_task.py:1400`); the shared signature must land in
  one lockstep WP (linearize shared surfaces). WP02's assertions depend on WP01's fix.
- **Sequencing gate**: #2570 WP01 (`e7cab2693`) already in base (implement_cores.py
  churn absorbed). Open PR #2639 line-shifts `tasks_move_task.py:1364` → rebase the
  move-task-touching WP onto `upstream/main` after #2639 merges (line reconciliation
  only).

## Confirmed prerequisites

- WP08 read-side fix (`52211737b`) is on the base branch.
- Per-kind partition authority (`mission_runtime/artifacts.py`) is stable and
  landed; write-side already consumes `placement_ref`; move-task already reuses the
  staging core. The asymmetry the spec targets is real and isolated to the read/compare side.

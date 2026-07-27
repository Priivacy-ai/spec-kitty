# Research: Trusted mission-artifact commit path

Consolidated re-grounding decisions from the pre-plan squad (paula-patterns root-cause, architect-alphonso
coord-commit seam, python-pedro #2861/e2e), verified against current `upstream/main` (the pre-spec notes
were on the stale branch `doctrine/drg-completeness-2843`). No open NEEDS CLARIFICATION.

## Decision A — the modern coord-commit path is already correct; fix the misroute, not "both paths"

- **Decision**: Do NOT change `_commit_via_coordination_transaction` (the modern path); it already resolves
  the coord sub-worktree root via `CoordinationWorkspace.resolve` and threads it into `safe_commit`. The
  real residual is (a) a fail-loud guard so a coord-routed topology can never reach
  `_commit_via_legacy_safe_commit` from `repo_root` when the identity triple is incomplete
  (`_load_coord_branch_meta`, `workflow_executor.py:~217`), and (b) fix the legacy leaf's porcelain
  pre-check (`workflow.py:~599`) to run against the resolved worktree root.
- **Rationale**: alphonso verified the only `git status --porcelain` in the whole commit chain is the
  legacy-leaf pre-check; the modern path has none and writes in-worktree. The phantom short-circuit is a
  **#2684** guard, not #2868 (#2868/#2612 are closed-unmerged).
- **Alternatives**: "route everything to the modern path" (rejected — could regress legitimately-legacy
  callers; a guard + leaf-fix is narrower and defect-class-closing).

## Decision B — the live #2861 repro decides causation before the actor work

- **Decision**: Run the NFR-002 live red-first repro (`agent action review --agent tool:model:profile:role`,
  no `--invocation-id`) FIRST. The squad's convergent hypothesis (alphonso + pedro): the blocking
  "commit refused" is the FR-002 misroute (`SafeCommitHeadMismatch`), NOT the actor-shape bug.
- **Rationale**: the dict-actor validator is the SaaS-fanout path — it warns-and-skips, never raises; the
  local JSONL append is dict-safe. So FR-005/006 cannot by themselves cause (or fix) the commit refusal.
- **Consequence**: FR-002 unblocks manual review (US2 AC-3); FR-005/006 is actor correctness + fanout
  fidelity. IC-01 (FR-002) sequences first; IC-04 (actor) does not claim AC-3 unless the repro says so.

## Decision C — re-home ANALYSIS_REPORT COORD→PRIMARY (operator-signed-off)

- **Decision**: Move `ANALYSIS_REPORT` from `_PLACEMENT_ARTIFACT_KINDS` to `_PRIMARY_ARTIFACT_KINDS`
  (`mission_runtime/artifacts.py`) — **the ONE frozenset membership move ONLY**; drop its best-effort coord
  copy (`mission_record_analysis.py`); keep `assert_partition_invariant` green.
- **⚠ Precision (post-plan squad)**: do NOT delete `analysis-report.md` from `_COORD_RESIDUE_FILENAMES`
  (that map is the general file→kind classifier consumed by `kind_for_mission_file`, NOT a residue-only
  list — deleting the entry makes `kind_for_mission_file("analysis-report.md") → None` and mis-routes it
  via the unrecognized-path fallback). The residue predicates + `is_primary_artifact_kind` all derive from
  the frozensets, so the ONE membership move flips ~9 delegators atomically — keep the classifier entry.
  Also rewrite the now-false comment at `mission_record_analysis.py:~336-340` (it asserts the opposite),
  and INVERT — not run-to-green — the ~8 tests that pin analysis-report as COORD (esp.
  `tests/coordination/test_commit_router.py:502`, a #2463 flip-test landmine), and update the arch-gate
  `tests/architectural/test_write_surface_placement_guard.py` `PARTITION_RATIONALE[ANALYSIS_REPORT]`
  (partition + rationale text + anti-mutant expected ref, from #2198).
- **Rationale**: paula found `write_analysis_report` requires spec/plan/tasks as *siblings* (freshness
  hash), which are PRIMARY-only — the coord worktree lacks them, so "write-in-home" on COORD is
  structurally impossible. The writer + freshness gate already resolve PRIMARY; only the SSOT said COORD.
  Re-homing makes writer+gate+SSOT agree — a mis-classification correction, not a contract redesign.
- **Alternatives**: (a) decouple `write_analysis_report` from sibling files by passing hash inputs as data
  (rejected by operator — larger change; the kind genuinely belongs on PRIMARY). Keep C-001's structure
  intact; move ONE kind only.

## Decision D — FR-001 is the disk-write step, independent of FR-002

- **Decision**: FR-001's target is write-in-home at the authorship sites (`review/cycle.py:~272` review-
  cycle → PRIMARY home), NOT the commit routing (already unified via `commit_for_mission →
  resolve_placement_only`). FR-001 (ref/dir projection) and FR-002 (worktree-root projection) are
  independent — co-land, don't block.
- **Rationale**: alphonso — `CommitTarget` is ref-only (C-007); the coord worktree root comes from
  `CoordinationWorkspace.resolve`, a separate projection the placement port does not supply.

## Decision E — FR-004 is topology-conditional, not a delete

- **Decision**: For coord topology, materialize/target the coord worktree at `status_transition.py:~924`;
  PRESERVE the primary-uncommitted fallback for coord-less topologies (`SINGLE_BRANCH`/`LANES`/flat).
- **Rationale**: paula — `_transaction_topology_available` already returns True for healthy coord missions
  (coordination_branch in meta.json); the False arm is the coord-worktree-missing edge + coord-less
  topologies where the primary write is correct. A blanket delete regresses flat missions.

## Decision F — parse --agent at the boundary WITHOUT synthetic defaults

- **Decision**: No boundary parse happens on the live claim path today (the `wp_metadata` parser is only
  reached from persisted frontmatter). Parse `--agent` at the CLI boundary → bare `tool` + widen
  `build_resolved_actor` with self-asserted `profile`/`model` kwargs. Do NOT reuse the parser's synthetic
  defaults (`unknown-model`, `{tool}-default`) for the actor — absent segments stay absent. Do NOT
  synthesize a `ResolvedBinding` (C-002/C-007). FR-006 widens `WPStatusChanged`/`WPCreated` validators;
  `WPAssigned` has no actor field (out of scope).
- **Rationale**: pedro — reusing the frontmatter parser verbatim would fabricate synthetic identity on the
  actor for partial `--agent` strings, which is wrong for a self-asserted actor.

## Decision G — real-repo e2e via existing un-stubbed harnesses

- **Decision**: Build NFR-001 on `tests/regression/test_issue_2508.py` + `tests/integration/coord_topology_fixture.py`
  (real `git init` + real `git worktree add` via production `CoordinationWorkspace.resolve`, `CliRunner` on
  `agent action`). Assert placement via `git show <ref>:<path>`, not filesystem state. Negative case: call
  `safe_commit` with a swapped `worktree_root`/`destination_ref` → `SafeCommitHeadMismatch`.
- **Rationale**: these harnesses are self-proven un-stubbed (`TestNoResolverPatchedInFixture`); NFR-001
  forbids a stubbed `safe_commit`.

## Re-grounding corrections to the stale notes (recorded for the campsite step)

- The residue factory is LIVE at `coordination/commit_router.py:703` (an earlier wrong-path grep said
  "gone" — corrected).
- The write-side partition guard `PrimaryKindReachedCoordStagingError` (the #2834-class fix) already
  landed; FR-001 builds on it.
- `review_artifact_consistency` moved into `merge/` — re-verify the review-cycle read partition before
  touching it.
- Line numbers throughout are current-main approximations — re-confirm at the campsite (C-006).

# Data Model: Trusted mission-artifact commit path

## Artifact-kind partition (after the ANALYSIS_REPORT re-home)

The partition is disjoint-and-total (`assert_partition_invariant`). Read surface == write surface per
kind. The ONE change this mission makes is moving `ANALYSIS_REPORT` COORD→PRIMARY.

| Kind | Partition (after) | Home dir | Authored/Derived | Notes |
|------|-------------------|----------|------------------|-------|
| `SPEC` / `PLAN` / `WORK_PACKAGE_TASK` / `PRIMARY_METADATA` | PRIMARY | target-branch `kitty-specs/<mission>/` | authored | reviewable planning surface |
| **`ANALYSIS_REPORT`** | **PRIMARY (changed from COORD)** | target-branch `kitty-specs/<mission>/analysis-report.md` | authored | writer + freshness gate + siblings already PRIMARY; SSOT corrected to match. **Change = the ONE `_PLACEMENT→_PRIMARY` frozenset move ONLY.** KEEP `_COORD_RESIDUE_FILENAMES["analysis-report.md"]` (it is the file→kind classifier, not a residue-only entry — deleting it mis-routes via the unrecognized-path fallback). ~9 residue delegators + `is_primary_artifact_kind` flip atomically from the frozenset. Also touch: the `PARTITION_RATIONALE[ANALYSIS_REPORT]` arch-gate (#2198), the stale `mission_record_analysis.py:~336` comment, and INVERT (not run-to-green) ~8 coord-pinning tests |
| `STATUS_STATE` (`status.events.jsonl`, `status.json`, notes) | COORD | coord-branch `kitty-specs/<mission>/` | log authored / snapshot+notes derived | single write-authority; commit to coord worktree |
| `ISSUE_MATRIX` | COORD | coord | authored verdicts | write-in-coord-home (verify no sibling coupling) |
| `ACCEPTANCE_MATRIX` | COORD | coord | authored evidence | write-in-coord-home (verify no sibling coupling) |
| review-cycle-N.md | PRIMARY (`WORK_PACKAGE_TASK` under `tasks/`) | target-branch `tasks/<wp>/` | authored prose + event-sourced verdict | FR-001 write-in-home (retire kind-blind resolver) |

**Invariant preserved**: after the move, `_PRIMARY_ARTIFACT_KINDS ∪ _PLACEMENT_ARTIFACT_KINDS` = all kinds,
disjoint; `assert_partition_invariant` stays green; no kind's read surface diverges from its write surface.

## Entity: the placement port (existing, reused)

- `kind_for_mission_file(path) -> MissionArtifactKind` (`artifacts.py:307`) — file → kind.
- `resolve_placement_only(kind) -> Placement` (`resolution.py:1219`) — kind → **ref** (branch). Ref-only
  (C-007) — does NOT supply a worktree root.
- `CoordinationWorkspace.resolve(repo_root, slug, mid8) -> worktree_root` — the SEPARATE projection that
  supplies the coord sub-worktree path (used by FR-002/FR-004, not FR-001).

## Entity: the commit-path routing (existing)

```
_commit_workflow_change (workflow_executor.py:189)
  └─ _load_coord_branch_meta(primary_meta) -> (coordination_branch, mission_id, mid8)?
       ├─ triple complete  -> _commit_via_coordination_transaction  (MODERN: threads coord worktree root — correct)
       └─ triple incomplete -> _commit_via_legacy_safe_commit         (LEGACY: repo_root — MISROUTE HAZARD, FR-002)
```

- FR-002 (a): the incomplete-triple → legacy arm is the misroute — for a coord-routed topology it must fail
  loud (or resolve the coord worktree), never commit coord paths from `repo_root`.
- FR-002 (b): the legacy leaf's `git status --porcelain` pre-check (`workflow.py:~599`, #2684) must run
  against the resolved worktree root, not `repo_root` (else it returns empty over gitignored `.worktrees/`
  files → phantom "already committed").

## Entity: actor payload (FR-005/006)

```python
# build_resolved_actor (status/emit.py:1077) — widened:
#   (*, role, tool: str|None, binding: ResolvedBinding|None,
#       self_profile: str|None = None, self_model: str|None = None)
actor = {
  "role":    role,
  "tool":    <bare tool token>,          # parsed from --agent, NOT the whole compact string
  "profile": binding.agent_profile or self_profile,   # self-asserted only if no dispatch binding
  "model":   binding.model or self_model,             # absent stays None — NO synthetic "unknown-model"
}
```

- The compact `--agent tool:model:profile:role` is parsed at the CLI boundary into these fields; absent
  segments stay `None` (self-asserted, not fabricated).
- A `ResolvedBinding` is NEVER synthesized from `--agent` (C-002/C-007) — self-asserted identity lives on
  the actor, not the binding.
- Emitter validators (`sync/emitter.py:434` WPStatusChanged, `:452` WPCreated) accept `Union[str, Dict]`
  (SaaS-fanout fidelity; the local JSONL append is already dict-safe).

## Entity: runtime-state allowlist (FR-007)

- A NAMED set of the mission's own bookkeeping basenames — `status.events.jsonl`, `status.json`,
  `review-cycle-N.md` (glob), issue-matrix, acceptance-matrix, notes — anchored to the RUNNING mission's
  OWN `feature_dir`. A path is exempt iff `(under this mission's feature_dir) AND (basename ∈ allowlist)`.
  `spec.md`/`plan.md`/`tasks.md` are NOT in the allowlist (reviewable). Another mission's runtime files are
  NOT exempt (feature_dir mismatch).

## Entity: coord staleness (FR-008/009)

- `coord_tip` vs `target_branch`: strict-ancestor → stale-fast-forwardable; not-ancestor → diverged (warn,
  fail-loud). `--fix` fast-forwards ONLY when strict-ancestor AND the coord worktree is clean; else fails
  loud with a unified diff, mutating nothing.

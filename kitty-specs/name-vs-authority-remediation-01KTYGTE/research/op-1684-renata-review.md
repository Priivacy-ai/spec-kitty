# Op #1684 — reviewer-renata stage-4 review record

**Issue:** #1684 — Lane worktree base ignores WP-level dependencies; sibling-lane work not propagated to dependent lanes
**Op invocation id:** `01KTYYFC60ZGDEAE4VWWP96YV5` (profile `reviewer-renata`)
**Tree:** `feat/name-vs-authority-remediation-01KTYGTE`
**Pipeline reviewed (combined diff):**
- stage 2 — python-pedro fix `aa44d76f5` "fix(#1684): lane worktree base honors depends_on_lanes (fresh + reuse paths, ATDD)"
- stage 3 — randy-reducer reduction `32b7698f2` "refactor(#1684): reduce worktree allocator post-fix (behavior-preserving)"

## VERDICT: PASS

The fix faithfully implements debby's prescription, the reduction is behavior-preserving,
seam discipline is honored, and all gates are green with zero new mypy errors. One missing
regression test (4a, the `--base` + dependency-merge composition) was identified and written
in this review; it is included in the review commit.

## Per-checklist findings

### 1. Fix correctness vs debby's prescription — PASS
- **Fresh path (coord + legacy) merges approved dep tips:** Both topology branches
  (`coordination_branch is not None` and the legacy `mission_branch` else-branch) fall through
  to a single shared `_merge_dependency_lane_tips(...)` call before `return`
  (`worktree_allocator.py:172-177`). Both paths covered.
- **Reuse path merges dep tips:** `worktree_allocator.py:135-137` — the reuse branch validates
  clean, then runs the same catch-up merge before returning. Covers the WP05/WP09 "dep approved
  after lane creation" double-hit (test `test_reuse_path_catches_up_dependency_approved_after_creation`).
- **`(parallel_group, lane_id)` ordering:** `_ordered_dependency_lanes` sorts resolved dep lanes
  by `key=lambda dep: (dep.parallel_group, dep.lane_id)` (`worktree_allocator.py:198`) — the same
  topological order `compute_lanes` emits and `merge` consumes. Multi-dep ordering covered by
  `test_two_dependencies_merged_in_order`.
- **Ancestor-check idempotency:** `git merge-base --is-ancestor dep_branch HEAD` short-circuits
  already-merged tips (no redundant merge commit) — idempotent on the reuse path.
- **Missing-branch → warn+skip — adjudicated ACCEPTABLE (faithful, not a deviation).**
  Debby's prescription #5: "fall back to the current target-branch tip ... skip the missing dep
  silently with a warning." Pedro skips the unresolvable dep with a (louder, non-silent) WARNING
  and continues. Because the lane is already rooted at coord/mission base (a descendant of
  `target_branch`), omitting the dep tip IS the target-tip fallback — no active re-rooting is
  needed. Pedro's warning is more informative than debby's "silently" (an improvement). Faithful.
- **Conflict → fail closed:** on non-zero merge rc, `git merge --abort` runs first, THEN
  `DependencyLaneMergeConflictError` is raised (`worktree_allocator.py:325-339`). The error
  extends `StructuredError`, carries `error_code="DEPENDENCY_LANE_MERGE_CONFLICT"` + structured
  `next_step`, and extends `to_dict()`. Worktree-left-clean verified by
  `test_conflicting_dependency_merge_fails_closed` (asserts `git status --porcelain` empty).

### 2. Seam discipline — PASS
- Dep-lane branch resolution goes through the canonical grammar
  `lane_branch_name(mission_slug, dep_lane.lane_id)` (`worktree_allocator.py:284`) — no
  name-derived f-strings. Consistent with the lane's own branch resolution at line 125.
- Topology ratchet `tests/architectural/test_topology_resolution_boundary.py` — **3 passed** (run by reviewer).

### 3. Randy's reduction safety (adversarial trace) — PASS
- **Coord early-return → if/else restructure:** Traced both branches. Pedro's version had the
  coord path end with `_merge_dependency_lane_tips(...) + return`, and the legacy path as a
  fallthrough with its own duplicate merge call. Randy folded both into `if/else`, then a single
  shared merge + single `return`. Coord branch still runs `_create_lane_worktree` +
  `register_lane_sparse_checkout`; legacy branch still runs `_ensure_mission_branch` +
  `_create_lane_worktree`. The merge step and return execute identically in both paths.
  **Semantics preserved.**
- **`_create_branch_from` extraction — error messages byte-identical:** `label="mission branch"`
  → `"Failed to create mission branch {branch} from {parent}: ..."` (matches pre-extraction
  `_ensure_mission_branch`); default `label="branch"` → `"Failed to create branch {branch} from
  {parent}: ..."` (matches pre-extraction `_ensure_branch_exists`). Byte-identical.
- **Test-fixture factories:** The reduction touched only production code; no test assertions were
  weakened. Existing `tests/lanes/` suite (incl. `test_worktree_allocator.py`) — **237 passed,
  1 skipped.**

### 4. Randy's two flagged items — adjudicated
- **4a. `--base` + dep-merge interplay had no dedicated regression test — RESOLVED in this review.**
  Decision: the composition is a documented contract (`implement.py:1106-1108`) and was genuinely
  unpinned. I wrote `test_explicit_base_composes_with_dependency_merge` (real git fixture, mirrors
  `implement.py`'s `_dc_replace(mission_branch=base)` legacy-path patch) asserting BOTH the chosen
  base's content and the approved dep tip land on the dependent lane. Included in the review commit.
  Note (non-blocking): `--base` patches `mission_branch`, which only the legacy (no-coordination)
  path reads; for new-topology missions `--base` is a pre-existing no-op (lane roots on
  `coordination_branch`). The doc comment's "regardless of the chosen root" is accurate for the
  legacy path the flag actually affects; the dep-merge composition itself is correct on both paths.
- **4b. Cross-module `_branch_exists` triplication — confirmed NON-BLOCKING follow-up.**
  Randy correctly consolidated the idiom intra-module (3 sites → 1 `_branch_exists`). The same
  `git rev-parse --verify refs/heads/...` idiom is duplicated across ~10 other modules
  (`coordination/policy.py`, `merge.py`, `mission_type.py`, `orchestrator_api/commands.py`,
  `git/commit_helpers.py`, `missions/_create.py`, ...). A shared `git` helper is a sensible
  follow-up but out of scope for this fix.

### 5. Gates (run by reviewer) — ALL GREEN
- `tests/regression/test_issue_1684_cross_lane_base.py` — **6 passed** (5 original + the new 4a test).
- `tests/lanes/` — **237 passed, 1 skipped.**
- `tests/architectural/` (full) — **353 passed** (warnings pre-existing).
- `ruff check` (touched files) — **All checks passed.**
- `mypy` — **zero NEW errors.** Single-file `mypy worktree_allocator.py` reports 2 errors
  (`Class cannot subclass StructuredError (has type Any)` + `Returning Any`), but the
  pre-existing sibling subclass `branch_naming.py` reports the *identical* 2 errors in isolation;
  whole-package `mypy --strict src/specify_cli/lanes/ src/specify_cli/core/errors.py` (the CI
  invocation shape) reports **"Success: no issues found in 14 source files."** The single-file
  errors are a module-resolution artifact, not new defects.

### 6. Dead code / NFR-001 — PASS
- All four new helpers have live call sites: `_ordered_dependency_lanes`,
  `_merge_dependency_lane_tips`, `_create_branch_from` (3 callers), `_branch_exists` (3 callers).
- No existing test logic altered; the only existing-code change is the `_branch_exists` /
  `_create_branch_from` consolidation, verified semantically identical above.

## Op close
`spec-kitty profile-invocation complete --invocation-id 01KTYYFC60ZGDEAE4VWWP96YV5 --outcome done`
(see terminal — closed with one-line verdict).

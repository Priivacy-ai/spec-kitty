# Op #1684 — debugger-debbie stage-1 investigation

**Issue:** #1684 — Lane base ignores WP-level dependencies; sibling-lane work not propagated to dependent lanes
**Op invocation id:** `01KTYXF27M5X8AG57BBN1QDJZ5` (profile `debugger-debbie`; note: requested `debugger-debby` does not exist — canonical id is `debugger-debbie`)
**Tree:** `feat/name-vs-authority-remediation-01KTYGTE`
**Date:** 2026-06-12

## VERDICT: CONFIRMED (cross-lane base bug). Reporter's *root-cause attribution is partly wrong on this tree.*

The core symptom is real and reproduced. But the reporter pinned it on
`finalize-tasks` failing to translate WP deps into `depends_on_lanes`.
On THIS tree `compute_lanes` **does** compute `depends_on_lanes` correctly
(see below). The defect is downstream: the worktree base-selection path
ignores `depends_on_lanes` entirely. So even with a correct manifest, the
dependent lane is rooted at the bare mission branch.

## Root cause (file:line)

**`src/specify_cli/lanes/worktree_allocator.py` → `allocate_lane_worktree()`, lines 82–115.**

The base ref for a *fresh* lane worktree is chosen unconditionally as:
- `coordination_branch` (new-topology missions) — lines 91–108, or
- `lanes_manifest.mission_branch` (legacy) — lines 110–113.

`lane.depends_on_lanes` is **never read** in this function (or anywhere in
the module — grep confirms `depends_on_lanes` appears only in
`lanes/models.py` and `lanes/compute.py`, never in `worktree_allocator.py`,
`implement_support.py`, or `cli/commands/implement.py`). The lane object is
fetched via `lanes_manifest.lane_for_wp(wp_id)` (line 68) purely to derive
the branch name + worktree path; its dependency edges are discarded.

**Classification: never-implemented (cross-lane).** Same-lane sequential
WPs work because they *reuse the one worktree* (lines 77–80 `worktree_path.exists()`
→ reuse) — the second WP inherits the first WP's commits on the shared lane
branch. The bug is specifically CROSS-lane: a dependent WP in a *different*
lane gets a brand-new worktree branched from mission/coord branch with no
edge to the dependency lane's tip.

### Why deps are consulted but don't help

`cli/commands/implement.py:982` calls `dependency_readiness_for_wp(...)` —
this gates the *claim* (deps must be `approved`/`done`) but does nothing to
the base ref. `declared_deps` is threaded into
`implement_support.create_lane_workspace(..., declared_deps, ...)` and only
written into WorkspaceContext metadata / WP frontmatter
(`implement_support.py:125,157`), never used to pick a base.

The only existing escape hatch is the manual `--base` flag
(`implement.py:851–1114`): it patches `lanes_manifest.mission_branch` via
`_dc_replace` so the allocator branches from the operator-supplied ref. This
is exactly the documented workaround surface — it confirms the base is a
single mission-branch knob with no per-lane dependency awareness.

## `compute_lanes` DOES populate `depends_on_lanes` (reporter's claim #1 nuance)

`src/specify_cli/lanes/compute.py:466–537`: lane edges are built from the
WP `dependency_graph` (`lane_deps[my_lane].add(dep_lane)` at line 501) and
written into each lane's `depends_on_lanes` (line 534), with
`parallel_group` = lane depth from the dependency DAG (line 535). Lanes are
sorted by `(parallel_group, lane_id)` (line 552). The reporter's observed
empty `depends_on_lanes` / `parallel_group: 0` was on 3.1.x and/or because
their WP-frontmatter deps weren't reaching `dependency_graph` — NOT the
current state of this branch. Stage 2 should treat the manifest as
trustworthy and fix the *consumer*.

## Merge layer proves the data is trustworthy

`cli/commands/merge.py:1983` builds `all_wp_ids` by iterating
`lanes_manifest.lanes` in their stored order, which `compute.py:552` already
sorted by `(parallel_group, lane_id)` — i.e. dependency-topological lane
order derived from `depends_on_lanes`. So `merge` consumes the lane-dependency
ordering and works; only the *worktree allocator* ignores it. The data is
reliable; the bug is purely in base-selection.

## Repro test

**Path:** `tests/regression/test_issue_1684_cross_lane_base.py`
(NOT committed; left in working tree for stage 2).

Real git fixture, two lanes (lane-a=WP01, lane-b=WP02 with
`depends_on_lanes=("lane-a",)`). Implements + commits WP01 on lane-a, then
claims WP02 and asserts (a) WP01's module file is visible on lane-b and
(b) lane-a's branch tip is an ancestor of lane-b HEAD.

**Failure output (current tree, correct reason):**
```
tests/regression/test_issue_1684_cross_lane_base.py:102: in test_...
    assert (wt_b / "wp01_module.py").exists(), (
E   AssertionError: WP01's module is not present on lane-b — the dependent lane
    was created from the bare mission branch and cannot import the approved
    sibling-lane dependency (issue #1684).
E   assert False
E    +  where False = exists()
```
Lane-b worktree exists but is rooted at the mission branch; WP01's commit
(only on lane-a) is absent → exactly the reported symptom.

## Recommended FIX SURFACE for stage 2

**Primary:** `src/specify_cli/lanes/worktree_allocator.py::allocate_lane_worktree`
(fresh-creation branch, lines 82–115) and the reuse branch (lines 77–80).

**Fix shape — "merge-on-claim of approved dependency lane tips":**
1. After resolving `lane = lanes_manifest.lane_for_wp(wp_id)`, read
   `lane.depends_on_lanes`. For each dep lane id, resolve its branch via
   `lane_branch_name(mission_slug, dep_lane_id)` (authority disposes — do
   NOT derive lanes by name guessing; the manifest is the authority and the
   #132 branch-identity/topology seams must mint/resolve the ref).
2. **Fresh worktree:** branch from the mission/coord base as today, then
   `git merge` each approved dependency lane tip (ordered by the dep lanes'
   `parallel_group`) — OR, equivalently, base the new lane on the highest
   approved dependency tip. Decide base-at-creation vs merge-after-create;
   merge-after-create composes cleanly when there are multiple deps.
3. **Existing/reuse worktree** (lines 77–80): a dep lane may have been
   approved *after* this lane's worktree was created. The reuse path must
   also fast-forward/merge newly-approved dep tips in (this is the WP05/WP09
   case hit twice on 01KTYGTE — lane already existed, dep approved later).
4. **Multiple deps:** merge in `parallel_group` order; surface conflicts as
   a structured error rather than leaving a half-merged worktree.
5. **Dep lane deleted post-merge:** if a dep lane branch no longer resolves
   (merged-and-deleted), fall back to the current target-branch tip — this is
   exactly what `--base main` does today; reuse `_validate_base_ref` and skip
   the missing dep silently with a warning (don't crash).

**Constraint (mission #132):** name proposes, authority disposes — resolve
dependency lane branches through the canonical branch-identity / topology
seams, never via name-derived lane lookups. Gate the new merge step behind
"dependency lane status == approved/done" (reuse `dependency_readiness_for_wp`
logic) so an in-flight dep lane is never merged.

**Secondary (verify, likely fine):** `cli/commands/implement.py` already
gates the claim on dep readiness (line 982) and threads `declared_deps`;
stage 2 may want to pass `lanes_manifest` deeper so the allocator can resolve
status, but the manifest already carries `depends_on_lanes`.

## Upstream duplicate check

`gh search issues` over "lane base dependency", "sibling lane propagated",
"worktree base mission branch dependency" returns only **#1684 itself**.
No duplicate. Adjacent (from the ticket, all open/architectural, none fix
the base-selection): #1619 epic (stale execution context), #1666 (state
domain redesign), #1672 (CWD parity ratchet), #1236 (closed — opposite
over-collapse bug). None enumerate the lane-base-from-dependency case.

## Op close

`spec-kitty profile-invocation complete --invocation-id 01KTYXF27M5X8AG57BBN1QDJZ5 --outcome done`
(see terminal — closed with one-line evidence).

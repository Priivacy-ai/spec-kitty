---
work_package_id: WP07
title: Two-stage merge + finalize-tasks canonical-target fix
dependencies:
- WP06
requirement_refs:
- FR-008
- FR-012
- FR-016
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
agent: claude
history:
- at: '2026-05-28T08:55:00+00:00'
  actor: claude
  event: wp_created
  notes: Generated via /spec-kitty.tasks from plan.md PR 2 design
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/merge.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/cli/commands/agent/mission_finalize_tasks.py
- src/specify_cli/missions/_resolve_planning_branch.py
- src/specify_cli/merge/**
- tests/specify_cli/cli/commands/test_merge.py
- tests/specify_cli/cli/commands/agent/test_mission_finalize_tasks.py
- tests/integration/test_mission_close.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, invoke `/ad-hoc-profile-load` with the profile listed in this WP's frontmatter (`agent_profile`). This loads the implementer identity, governance scope, and boundaries you must operate under for this WP.

Then return here and proceed.

---

## Objective

Two related fixes:
1. **`_resolve_planning_branch()` returns the canonical merge target** (from `meta.json`), not the current checkout branch. This closes the "prep-branch leak" symptom from issue #1348.
2. **Two-stage merge**: `spec-kitty merge` merges each lane → coordination (Stage 1), then coordination → target (Stage 2). Lane code reaches the target only via the coordination branch. Mission close tears down the coordination worktree, coordination branch, and lane branches.

## Context

**Spec source**: FR-008, FR-012, FR-016, SC-04, SC-10.
**Predecessor WPs**: WP06 (BookkeepingTransaction in workflow paths).
**Note about owned_files overlap**: this WP's `mission_finalize_tasks.py` and WP03's `mission_create.py` are both subcommand handlers of `agent mission`. If those live in a single monolithic `mission.py` file in the current codebase, you'll need to either (a) split that file as part of WP03 (preferred) or (b) carefully coordinate edits between WP03 and WP07 to avoid conflicts. **Verify the file layout first.**

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- Lane C; sequential after WP06.

---

## Subtask T031: Fix `_resolve_planning_branch()` to return canonical target

**Purpose**: Today `_resolve_planning_branch()` returns the current checkout branch. When an operator runs `finalize-tasks` from a `prep/` branch (which they did because the old guard pushed them off main), the prep branch name gets baked into WP frontmatter as `merge_target_branch`. When the prep branch is later deleted, lane allocation crashes.

**Steps**:
1. Locate `_resolve_planning_branch()` in `src/specify_cli/cli/commands/agent/mission.py` (around line 321).
2. Replace the implementation:
   ```python
   def _resolve_planning_branch(repo_root: Path, mission_meta: dict) -> str:
       """Return the canonical merge target branch from meta.json.

       This is the value persisted by `mission create` (it captured branch context
       at mission start, when the operator was definitively on the right base).
       """
       target = mission_meta.get("target_branch") or mission_meta.get("merge_target_branch")
       if not target:
           raise PlanningBranchResolutionFailed(
               "meta.json missing target_branch / merge_target_branch; "
               "this mission was created before branch context was persisted. "
               "Manually pass --target-branch to override.",
           )
       return target
   ```
3. Update all callers to use this resolver instead of calling `git branch --show-current` directly.
4. Add a CLI flag `--target-branch <ref>` for explicit override in legacy missions or edge cases.

**Files**:
- `src/specify_cli/cli/commands/agent/mission.py` (or `mission_finalize_tasks.py` if split)
- `src/specify_cli/missions/_resolve_planning_branch.py` (new helper module if extracted)

**Validation**:
- [ ] Running `finalize-tasks` from a `prep/` branch records `merge_target_branch: main` (not `prep/...`) in WP frontmatter.
- [ ] Running `finalize-tasks` from `main` records the same value.
- [ ] Legacy missions without `target_branch` in `meta.json` surface a clear error with the `--target-branch` escape hatch.

## Subtask T032: Two-stage merge — lane → coordination → target

**Purpose**: `spec-kitty merge` runs two stages. Stage 1 integrates each lane's code into the coordination branch (per WP, on done). Stage 2 merges coordination → target.

**Steps**:
1. Locate `spec-kitty merge` (likely `src/specify_cli/cli/commands/merge.py`).
2. Determine the topology of the mission (new coord-branch vs legacy). New topology: do the two-stage merge. Legacy: do the existing single-stage merge.
3. Stage 1 — Lane integration:
   ```python
   for wp_id in topologically_sorted_done_wps:
       lane_branch = wp_to_lane_branch(wp_id)
       # check out coordination worktree
       coord_path = CoordinationWorkspace.resolve(repo_root, slug, mid8)
       # merge lane into coordination
       result = subprocess.run(
           ["git", "-C", str(coord_path), "merge", "--no-ff",
            lane_branch, "-m", f"merge {lane_branch} into coordination"],
           capture_output=True,
       )
       if result.returncode != 0:
           # surface conflict via existing interactive merge UX
           raise LaneIntegrationConflict(wp_id, lane_branch, result.stderr)
       # emit lane_integrated event via BookkeepingTransaction
       with BookkeepingTransaction.acquire(...) as txn:
           txn.append_event(build_status_event(wp_id=wp_id, event_type="lane_integrated"))
   ```
4. Stage 2 — Coordination → target:
   ```python
   subprocess.run(
       ["git", "-C", str(repo_root), "checkout", target_branch],
       check=True,
   )
   subprocess.run(
       ["git", "-C", str(repo_root), "merge", "--no-ff",
        coord_branch, "-m", f"merge mission {slug} into {target_branch}"],
       check=True,
   )
   ```
5. The order matters: complete Stage 1 for ALL lanes before Stage 2 begins.

**Files**:
- `src/specify_cli/cli/commands/merge.py`
- `src/specify_cli/merge/executor.py` (the existing executor module from CLAUDE.md)

**Validation**:
- [ ] After merge, target branch contains every lane's code.
- [ ] After merge, coord branch is an ancestor of target.
- [ ] `lane_integrated` events are present in `status.events.jsonl` for each WP.
- [ ] Lane conflicts surface via the existing interactive merge UX.

## Subtask T033: Mission close teardown

**Purpose**: After successful merge OR `--discard`, remove the coordination worktree, coordination branch, and all lane branches. Idempotent.

**Steps**:
1. After Stage 2 of T032 succeeds, run teardown:
   ```python
   # delete lane branches
   for lane_branch in mission_lane_branches:
       subprocess.run(["git", "-C", str(repo_root), "branch", "-D", lane_branch], check=False)
       subprocess.run(["git", "-C", str(repo_root), "worktree", "remove",
                       lane_worktree_path, "--force"], check=False)
   # remove coord worktree
   CoordinationWorkspace.teardown(repo_root, mission_slug, mid8)
   # delete coord branch
   subprocess.run(["git", "-C", str(repo_root), "branch", "-D", coord_branch], check=False)
   ```
2. For `spec-kitty mission close --discard`: skip the merge stages and go straight to teardown. The coordination branch and lane branches are deleted; `main` is untouched.
3. Teardown is idempotent: if a worktree or branch is already gone, treat as success and log info.

**Files**:
- `src/specify_cli/cli/commands/merge.py`
- `src/specify_cli/cli/commands/mission_close.py` (or wherever `mission close --discard` lives)

**Validation**:
- [ ] After successful merge, `git branch --list 'kitty/mission-*'` returns nothing.
- [ ] After `--discard`, same thing; `main` untouched.
- [ ] Teardown is idempotent.

## Subtask T034: Integration tests — finalize-tasks from prep + full multi-lane merge

**Purpose**: End-to-end verification.

**Steps**:
1. In `tests/specify_cli/cli/commands/agent/test_mission_finalize_tasks.py`:
   - `test_finalize_tasks_from_prep_branch_records_canonical_target()` — create mission on `main`, manually check out a `prep/foo` branch, run `finalize-tasks`, assert WP frontmatter records `merge_target_branch: main` (not `prep/foo`). Direct verification of SC-04.
2. In `tests/integration/test_mission_close.py` (new):
   - `test_two_lane_mission_merges_via_coordination()` — full end-to-end: create mission, finalize-tasks, implement WP01 (lane A) and WP02 (lane B), mark both done, run `spec-kitty merge`. Assert: `main` has both lane code, coordination branch is gone, lane branches are gone, all worktrees removed. Verifies SC-10.
   - `test_mission_close_discard_teardown()` — create mission, discard, assert all branches/worktrees gone, `main` untouched.
   - `test_lane_conflict_surfaces_interactive()` — two lanes touch the same file; merge surfaces a conflict via the existing UX.
3. Tests run in real tmp git repos via subprocess; expect them to be slow.

**Files**:
- `tests/specify_cli/cli/commands/agent/test_mission_finalize_tasks.py`
- `tests/integration/test_mission_close.py`

**Validation**:
- [ ] All tests pass.
- [ ] SC-04 and SC-10 are explicitly verified.

---

## Definition of Done

- [ ] All 4 subtasks complete (T031..T034).
- [ ] `pytest tests/specify_cli/cli/commands/agent/test_mission_finalize_tasks.py` passes.
- [ ] `pytest tests/integration/test_mission_close.py` passes.
- [ ] A real 2-lane mission can be created, implemented, and merged end-to-end without manual intervention.
- [ ] `_resolve_planning_branch()` never returns the current checkout branch as the canonical target.

## Risks

- **Owned-file conflict with WP03**: if `mission.py` is monolithic, WP03 and WP07 fight for ownership. Coordinate; the cleanest answer is splitting `mission.py` into per-subcommand modules as part of WP03's owned scope, then WP07 owns only `mission_finalize_tasks.py`.
- **Lane integration conflicts**: real code conflicts surface here. Use the existing interactive UX (`spec-kitty merge --interactive`); don't try to auto-resolve.
- **Topological sort of WPs for Stage 1**: respect dependency order. The `lanes.json` file should encode the right order.
- **Status events for lane_integrated**: this is a new event type. Coordinate with the status reducer (if it has a strict allowed-event-types list) to add it.

## Reviewer guidance

1. **`_resolve_planning_branch()` reads meta.json, not git**: confirm no `git rev-parse` or `git branch --show-current` calls remain in this code path.
2. **Two-stage merge invariant**: Stage 1 completes for ALL lanes before Stage 2 starts. No interleaving.
3. **Teardown idempotency**: re-running teardown after success is a no-op, not an error.
4. **Discard path**: confirm `main` is byte-identical pre/post discard.
5. **Conflict UX**: confirm lane conflicts use the existing interactive merge handler.

## References

- Spec: FR-008, FR-012, FR-016, SC-04, SC-10
- Plan: PR 2 steps 8–9
- Identity model: ADR `2026-04-09-1-mission-identity-uses-ulid-not-sequential-prefix.md`
- Cross-review evidence: `mission.py:321` (see `spec.md` § References)

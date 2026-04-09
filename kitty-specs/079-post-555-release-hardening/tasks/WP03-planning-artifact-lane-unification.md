---
work_package_id: WP03
title: Track 2 — Planning Artifact Lane Unification
dependencies:
- WP02
requirement_refs:
- FR-101
- FR-102
- FR-103
- FR-104
- FR-105
- FR-106
- FR-503
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
agent: claude:opus:reviewer:reviewer
shell_pid: '98348'
history:
- at: '2026-04-09T07:30:50Z'
  event: created
authoritative_surface: src/specify_cli/lanes/compute.py
execution_mode: code_change
mission_slug: 079-post-555-release-hardening
owned_files:
- src/specify_cli/lanes/compute.py
- src/specify_cli/lanes/branch_naming.py
- src/specify_cli/lanes/models.py
- src/specify_cli/core/worktree.py
- src/specify_cli/workspace_context.py
- src/specify_cli/context/resolver.py
- src/specify_cli/cli/commands/implement.py
- tests/lanes/**
- tests/context/**
- tests/agent/cli/commands/test_implement_planning_artifact.py
- tests/agent/cli/commands/test_implement_help.py
tags: []
---

# WP03 — Track 2: Planning Artifact Lane Unification

**Spec FRs**: FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-503
**Priority**: P1 — closes a fundamental lane-contract hole; also handles the `implement.py` docstring (FR-503).
**Estimated size**: ~430 lines

## Objective

Make planning-artifact WPs first-class lane-owned entities. Currently `compute.py` filters them out of lane assignment; `resolver.py` has a special-case branch that returns `None` for their authoritative ref. This WP:
1. Assigns planning-artifact WPs to a canonical `lane-planning` lane.
2. Makes `lane-planning` resolve to the main repo checkout, not a `.worktrees/` directory.
3. Collapses the `execution_mode == "planning_artifact"` special-case branches at every consumer.
4. Updates `implement.py` to use uniform lane lookup AND rewrites its `--help` docstring to mark it as internal infrastructure (FR-503).

## Context

**Key data model** (from Phase 0 research):
- `ExecutionLane` (frozen dataclass): `lane_id`, `wp_ids`, `write_scope`, `predicted_surfaces`, `depends_on_lanes`, `parallel_group` — at `src/specify_cli/lanes/models.py:72-89`.
- `LanesManifest`: has `lanes: list[ExecutionLane]` and `planning_artifact_wps: list[str]`. Keep `planning_artifact_wps` as a **derived view** (backward-compat with historical manifests).
- `get_main_repo_root()` at `src/specify_cli/core/paths.py:200` — use this to resolve the planning lane workspace.
- `resolver.py:174-182` current code:
  ```python
  if execution_mode == "planning_artifact":
      authoritative_ref = None
  else:
      lane = require_lanes_json(feature_dir).lane_for_wp(wp_code)
      authoritative_ref = lane_branch_name(mission_slug, lane.lane_id)
  ```
  Target: remove the `if` branch; all lookups go through `lane_for_wp()`.

**agent/mission.py producer** already passes `mission_id=meta.get("mission_id")` to `compute_lanes()`. No producer-side change needed there beyond the filter removal.

## Branch Strategy

Plan in `main`, implement in the lane worktree allocated by `finalize-tasks`. Merge back to `main` on completion.

## Subtask Guidance

### T010 — Stop filtering `PLANNING_ARTIFACT`; assign to `lane-planning`

**File**: `src/specify_cli/lanes/compute.py`

**Current code** (lines 254-276):
```python
code_wp_ids: list[str] = []
planning_artifact_wps: list[str] = []
for wp_id in all_wp_ids:
    manifest = ownership_manifests.get(wp_id)
    if manifest and manifest.execution_mode == ExecutionMode.PLANNING_ARTIFACT:
        planning_artifact_wps.append(wp_id)
        continue  # ← this is the filter we're removing
    ...
    code_wp_ids.append(wp_id)
```

**Steps**:

1. Remove the `if manifest.execution_mode == ExecutionMode.PLANNING_ARTIFACT: ... continue` branch. All WPs flow into `code_wp_ids` (rename to `wp_ids` or leave as is — no semantic difference now).

2. After the lane assignment algorithm runs for code WPs, collect all WP IDs whose `execution_mode == PLANNING_ARTIFACT` from the ownership manifests and assign them all to a single `ExecutionLane` with:
   - `lane_id = "lane-planning"` (canonical, stable string constant; consider defining it as `PLANNING_LANE_ID = "lane-planning"` at module level)
   - `wp_ids = tuple(sorted(planning_artifact_wp_ids))` — all planning-artifact WPs in this mission
   - `write_scope = tuple(union of owned_files globs for all planning-artifact WPs)`
   - `predicted_surfaces = ("planning",)` (or empty tuple if no surface taxonomy applies)
   - `depends_on_lanes = ()` — planning artifacts are independent
   - `parallel_group = 0` (or any value that doesn't conflict with code lane groups; planning happens in its own workspace, parallel to code lanes)

3. Add the `lane-planning` ExecutionLane to `lanes_manifest.lanes` if any planning-artifact WPs exist.

4. Keep `planning_artifact_wps` in `LanesManifest` as a **derived view**: after assigning, populate `planning_artifact_wps` from the lane-planning lane's `wp_ids`. Do NOT remove this field (backward compat).

5. Handle the edge case: if there are no planning-artifact WPs, do NOT add a `lane-planning` lane. The lane only exists when there are planning-artifact WPs.

**Validation**:
- Call `compute_lanes()` with a dependency graph containing one planning-artifact WP and one code WP. Assert: result `lanes` list includes exactly one lane with `lane_id == "lane-planning"` containing the planning-artifact WP. Assert: the code WP is in a different lane. Assert: `planning_artifact_wps` is a list containing the planning-artifact WP id.

---

### T011 — Update `branch_naming.py` for `lane-planning`

**File**: `src/specify_cli/lanes/branch_naming.py`

**Current behavior**: `lane_branch_name(mission_slug, lane_id)` → `f"kitty/mission-{mission_slug}-{lane_id}"`.

**Required behavior**: For `lane_id == "lane-planning"`, return the mission's planning branch (the `target_branch` field from `meta.json`), NOT `"kitty/mission-<slug>-lane-planning"`.

**Steps**:

1. Identify the signature of `lane_branch_name()`. It currently takes `mission_slug` and `lane_id`. To know the planning branch, it also needs the `target_branch`. Either:
   - Add `target_branch: str` as a parameter with a default of `"main"`, OR
   - Accept a `meta_json_path: Path` parameter and read `target_branch` from it inside the function, OR
   - Add `planning_base_branch: str | None = None` parameter — if provided, use it for `lane-planning`.

2. Recommended approach: Add `planning_base_branch: str | None = None` as an optional parameter. When `lane_id == "lane-planning"` and `planning_base_branch` is provided, return it. When `lane_id == "lane-planning"` and `planning_base_branch` is None, return `"main"` (safe default).

3. Update all call sites of `lane_branch_name()` to pass `planning_base_branch` when available (primarily in `resolver.py` and `workspace_context.py`).

4. The key invariant: `lane_branch_name(slug, "lane-planning", planning_base_branch="main") == "main"`.

**Validation**:
- `lane_branch_name("079-post-555-release-hardening", "lane-planning")` → `"main"` (using default).
- `lane_branch_name("079-post-555-release-hardening", "lane-a")` → `"kitty/mission-079-post-555-release-hardening-lane-a"` (existing behavior preserved).

---

### T012 — `worktree.py` + `workspace_context.py` route `lane-planning` to main checkout

**Files**: `src/specify_cli/core/worktree.py`, `src/specify_cli/workspace_context.py`

**Steps**:

1. In `worktree.py`, find the `create_wp_workspace()` function (or `allocate_lane_worktree()` in `lanes/worktree_allocator.py` if that's where allocation happens). Add a check: if `lane_id == "lane-planning"`, return `get_main_repo_root(current_path)` directly — do NOT call `git worktree add`.

2. The existing `create_planning_workspace()` helper at `worktree.py:135` already returns `repo_root` for `PLANNING_ARTIFACT` execution mode. After T010 and T013, all routing to this function should now go through the lane lookup, not the WP-type check. Verify the routing is now: lane lookup → `lane_id == "lane-planning"` → `get_main_repo_root()`. Remove the `if execution_mode == PLANNING_ARTIFACT` type-branch from the allocation path (that branch is replaced by the `lane_id == "lane-planning"` lane-branch).

3. In `workspace_context.py`, `resolve_workspace_for_wp()` or similar function: after the lane lookup, if `lane_id == "lane-planning"`, set `worktree_path = get_main_repo_root(current_path)` instead of computing a `.worktrees/` path.

4. **Add the `get_next_feature_number()` docstring note** (from plan §6 Track 3, R-X.1 note): In `worktree.py`, find `get_next_feature_number()` (lines 163-207). Add a docstring note:
   > **Display-only**: This function computes a human-friendly sequential display number for a mission. It MUST NOT be used as the canonical machine-facing identity. The canonical identity is the `mission_id` (ULID) in `meta.json`. See FR-204.

**Validation**:
- For a planning-artifact WP in a test fixture, call the workspace resolver. Assert the returned `worktree_path` is the main repo root, NOT a `.worktrees/...` directory. Assert no `.worktrees/...` directory was created.

---

### T013 — Collapse `resolver.py:174-182` special-case

**File**: `src/specify_cli/context/resolver.py`

**Current code** (lines 174-182):
```python
if execution_mode == "planning_artifact":
    authoritative_ref = None
else:
    lane = require_lanes_json(feature_dir).lane_for_wp(wp_code)
    if lane is None:
        raise MissingIdentityError(...)
    authoritative_ref = lane_branch_name(mission_slug, lane.lane_id)
```

**Target code**:
```python
lane = require_lanes_json(feature_dir).lane_for_wp(wp_code)
if lane is None:
    raise MissingIdentityError(
        f"WP {wp_code!r} has no lane assignment in {feature_dir}/lanes.json. "
        f"Run 'spec-kitty agent mission finalize-tasks --mission {mission_slug}' to compute lanes."
    )
authoritative_ref = lane_branch_name(
    mission_slug,
    lane.lane_id,
    planning_base_branch=target_branch,  # pass through so lane-planning resolves correctly
)
```

**Steps**:

1. Verify `resolver.py` has access to `target_branch` (it likely reads from `meta.json` or is passed as a parameter). If not, thread it through from the call site.
2. Remove the `if execution_mode == "planning_artifact"` branch.
3. Pass `planning_base_branch` to `lane_branch_name()` so `lane-planning` resolves to the actual planning branch (not just `"main"` hardcoded).

**Validation**:
- For a planning-artifact WP with `lane_id == "lane-planning"` in lanes.json, call the resolver. Assert `authoritative_ref == target_branch` (e.g., `"main"`), not `None`, not `MissingIdentityError`.

---

### T014 — `implement.py`: uniform lane lookup + internal-infrastructure docstring

**File**: `src/specify_cli/cli/commands/implement.py`

**Steps — part A (uniform lane lookup)**:

1. Find the implement dispatch logic. Confirm it calls the workspace resolver (which was fixed in T012). If there are remaining `if execution_mode == "planning_artifact"` branches in implement.py itself, remove them. All routing should now go through the lane lookup.

2. The `_ensure_planning_artifacts_committed_git()` helper (lines 179-200) handles planning-artifact-specific git commit semantics (committing planning artifacts to the planning branch in the main checkout). Keep this function and its behavior — it is still the correct action for planning-artifact WPs. The change is only that the ROUTING to this function now comes from the lane lookup (lane_id == "lane-planning") rather than a WP-type check. If the current code checks `execution_mode == PLANNING_ARTIFACT` to decide whether to call `_ensure_planning_artifacts_committed_git()`, change that check to `lane_id == "lane-planning"`.

**Steps — part B (docstring, FR-503)**:

3. Find the docstring for the `implement()` function at `implement.py:389`:
   - Current: `"""Allocate or reuse the lane worktree for a work package."""`
   - New:
     ```
     Internal — allocate or reuse the lane worktree for a work package.

     This command is internal infrastructure, used by `spec-kitty agent action implement`
     for workspace creation. It is not the canonical user-facing implementation path for
     spec-kitty 3.1.1.

     Canonical user workflow:
       spec-kitty next --agent <name> --mission <slug>   (loop entry)
       spec-kitty agent action implement <WP> --agent <name>  (per-WP verb)

     This command remains available as a compatibility surface for direct callers.
     See FR-503 and D-4 in the 3.1.1 spec.
     """
     ```

**Validation**:
- `spec-kitty implement --help` output contains "internal infrastructure" (or "internal") and contains "spec-kitty next" and "spec-kitty agent action implement".
- `spec-kitty implement WP01 --mission <slug>` still runs without error for a code WP.
- `spec-kitty implement <planning-wP> --mission <slug>` resolves to main repo checkout for a planning-artifact WP.

---

### T015 — Regression tests for Track 2

**Files**: New test files in `tests/lanes/`, `tests/context/`, `tests/agent/cli/commands/`

**Test T2.1 — `compute_lanes` includes planning-artifact WPs**:
```python
# tests/lanes/test_compute_planning_artifact.py
def test_planning_artifact_wps_are_included_in_lanes():
    # Build fixture: one code WP, one planning-artifact WP
    # Call compute_lanes()
    # Assert: result.lanes contains a lane with lane_id == "lane-planning"
    # Assert: that lane's wp_ids includes the planning-artifact WP
    # Assert: the code WP is in a different lane
```

**Test T2.2 — Canonical `lane_id` is `"lane-planning"`**:
```python
def test_planning_lane_has_canonical_id():
    # Same fixture
    # Assert: the planning-artifact lane's lane_id == "lane-planning"  (exact string)
```

**Test T2.3 — `lane_branch_name` for `lane-planning` returns planning branch**:
```python
# tests/lanes/test_branch_naming_planning.py
def test_lane_branch_name_planning_returns_planning_branch():
    result = lane_branch_name("079-test", "lane-planning", planning_base_branch="main")
    assert result == "main"
    # NOT "kitty/mission-079-test-lane-planning"

def test_lane_branch_name_normal_lane_unchanged():
    result = lane_branch_name("079-test", "lane-a")
    assert result == "kitty/mission-079-test-lane-a"
```

**Test T2.4 — Resolver returns coherent ref for planning-artifact WP**:
```python
# tests/context/test_resolver_planning_artifact.py
def test_resolver_returns_planning_branch_for_planning_artifact_wp():
    # Set up: mission with planning-artifact WP, lanes.json has lane-planning
    # Call resolver
    # Assert: authoritative_ref == "main" (the planning branch)
    # Assert: no MissingIdentityError raised
    # Assert: no "planning_artifact" type-check at the call site
```

**Test T2.5 — `implement` dispatch for planning-artifact WP lands in main checkout**:
```python
# tests/agent/cli/commands/test_implement_planning_artifact.py
def test_implement_planning_artifact_resolves_to_main_checkout():
    # Set up: mission with planning-artifact WP, lanes computed
    # Invoke implement command for planning-artifact WP
    # Assert: resolved workspace == main repo root
    # Assert: no .worktrees/ directory created for lane-planning
```

**Test T2.6 — Code WPs still get normal lane assignments**:
```python
# In test_compute_planning_artifact.py
def test_code_wps_still_get_normal_lanes():
    # Same fixture as T2.1
    # Assert: code WP is in a lane-a/lane-b style lane
    # Assert: code WP's lane has a non-empty write_scope
```

**Test T6.1 (FR-503 via T014) — `implement --help` marks command as internal**:
```python
# tests/agent/cli/commands/test_implement_help.py
def test_implement_help_marks_command_as_internal(runner):
    result = runner.invoke(app, ["implement", "--help"])
    assert result.exit_code == 0
    assert "internal" in result.output.lower()
    assert "spec-kitty next" in result.output
    assert "spec-kitty agent action implement" in result.output
```

## Definition of Done

- [ ] `compute_lanes()` with planning-artifact WPs produces a `lane-planning` lane (T2.1, T2.2).
- [ ] `lane_branch_name(..., "lane-planning")` returns the planning branch, not a kitty-namespace branch (T2.3).
- [ ] Resolver returns coherent `authoritative_ref` for planning-artifact WPs (T2.4).
- [ ] `implement` dispatch for planning-artifact WPs lands in main checkout, no `.worktrees/` created (T2.5).
- [ ] Code WPs still get normal lane assignments (T2.6).
- [ ] `implement --help` contains "internal" and names `spec-kitty next` (T6.1).
- [ ] `spec-kitty implement WP01` still runs for code WPs (compatibility).
- [ ] `LanesManifest.planning_artifact_wps` remains as a derived view (not removed).
- [ ] `mypy --strict` clean on all modified files.

## Risks

| Risk | Mitigation |
|------|-----------|
| `worktree_allocator.py` triggers worktree create for `lane-planning` | Grep for `worktree_allocator.py` callers; add `if lane_id == "lane-planning": return repo_root` guard early. |
| Historical `lanes.json` missing `lane-planning` | Old manifests have `planning_artifact_wps` list; readers should still work because the lane-planning lane is new and only present in newly computed manifests. |
| `lane_branch_name` signature change breaks callers | Make `planning_base_branch` optional with default `"main"`. Existing callers are unaffected. |

## Reviewer Guidance

1. Confirm: no `if execution_mode == "planning_artifact"` branches remain in `resolver.py`.
2. Confirm: `lane-planning` lane is added to `lanes` list, not to a separate field.
3. Confirm: `LanesManifest.planning_artifact_wps` is preserved (backward compat) but is a derived view.
4. Run the 6 new tests + `mypy --strict` on all 7 modified files.
5. Do a manual `spec-kitty implement` test against a planning-artifact WP in a test mission — confirm workspace is main repo, no `.worktrees/` created.

## Activity Log

- 2026-04-09T08:14:14Z – unknown – shell_pid=65349 – Dispatching implementation
- 2026-04-09T08:23:01Z – unknown – shell_pid=65349 – Lane-planning canonical model implemented, all consumers use uniform lane lookup, implement.py docstring updated
- 2026-04-09T08:23:45Z – claude:opus:reviewer:reviewer – shell_pid=67506 – Started review via action command
- 2026-04-09T08:34:49Z – claude:opus:reviewer:reviewer – shell_pid=67506 – Moved to planned
- 2026-04-09T08:35:23Z – claude:opus:reviewer:reviewer – shell_pid=85994 – Fixing 9 stale tests (cycle 2)
- 2026-04-09T08:42:47Z – claude:opus:reviewer:reviewer – shell_pid=85994 – Cycle 2: Fixed 9 stale test assertions, all tests pass (552 passed in full suite)
- 2026-04-09T08:43:24Z – claude:opus:reviewer:reviewer – shell_pid=87673 – Started review via action command
- 2026-04-09T08:53:16Z – claude:opus:reviewer:reviewer – shell_pid=87673 – Moved to planned
- 2026-04-09T08:53:56Z – claude:opus:reviewer:reviewer – shell_pid=98348 – Fixing final stale test (cycle 3)

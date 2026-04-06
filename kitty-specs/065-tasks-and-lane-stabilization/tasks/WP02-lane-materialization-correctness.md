---
work_package_id: WP02
title: Lane Materialization Correctness
dependencies: []
requirement_refs:
- FR-006
- FR-007
- FR-014
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T010, T011, T012, T013, T014, T015]
agent: "claude:opus:reviewer:reviewer"
shell_pid: "12577"
history:
- at: '2026-04-06T13:45:48+00:00'
  actor: claude
  action: Created WP02 prompt during /spec-kitty.tasks
authoritative_surface: src/specify_cli/ownership/
execution_mode: code_change
owned_files:
- src/specify_cli/ownership/inference.py
- src/specify_cli/ownership/validation.py
- tests/ownership/test_inference.py
- tests/ownership/test_validation.py
- tests/ownership/test_inference.py
- tests/ownership/test_validation.py
---

# WP02 — Lane Materialization Correctness

## Objective

Ensure lane computation produces a lane assignment for every executable (non-planning-artifact) WP, fails diagnostically when assignment is impossible, surfaces planning-artifact exclusions, and warns on ownership problems (zero-match globs, broad fallbacks).

This WP addresses issue #422 (the structural gap half — lane completeness and ownership validation).

## Context

### Current State

`compute_lanes()` at `src/specify_cli/lanes/compute.py:140-308` processes only WPs present in `dependency_graph.keys()`. WPs missing from the graph are silently dropped. WPs without ownership manifests are included in `code_wp_ids` but excluded from overlap checking (lines 196-199), creating invisible gaps.

`infer_owned_files()` at `src/specify_cli/ownership/inference.py:135-136` falls back to `["src/**"]` without warning when no paths are extracted from WP body text.

No validation checks that extracted glob patterns match real files.

### Target State

- Post-computation assertion: every executable WP in the task set appears in exactly one lane
- Fail with diagnostic error when an executable WP has no ownership manifest
- Surface planning-artifact exclusions in output
- Warn (not fail) when owned_files globs match zero files
- Warn (not fail) when the `src/**` fallback is applied

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`
- To start implementation: `spec-kitty implement WP02`

**Ownership note**: WP02 owns `ownership/inference.py` and `ownership/validation.py`. T010 and T011 also modify `lanes/compute.py`, but that file is owned by WP03 (which depends on WP02, so they share a lane). WP02's compute.py changes (assertions, error paths in lines 170-220) will be committed first; WP03 then modifies the union rules and output (lines 186-308).

---

## Subtask T010: Assert All Executable WPs Appear in Lane Assignment

**Purpose**: Guarantee that no executable WP is silently omitted from `lanes.json` (FR-006).

**Steps**:

1. In `compute.py`, after `raw_groups = uf.groups()` (line 219), add a completeness check:
   ```python
   assigned_wps: set[str] = set()
   for group_members in raw_groups.values():
       assigned_wps.update(group_members)

   missing_wps = set(code_wp_ids) - assigned_wps
   if missing_wps:
       raise LaneComputationError(
           f"Executable WPs not assigned to any lane: {sorted(missing_wps)}. "
           f"Verify that these WPs appear in the dependency_graph and have "
           f"ownership manifests in frontmatter."
       )
   ```

2. Define `LaneComputationError` as a new exception class in `compute.py` or `lanes/__init__.py`.

3. Ensure the `_UnionFind` constructor at line 57 initializes all `code_wp_ids`, so every WP has at least its own singleton group. This should already be the case — verify.

**Files**: `src/specify_cli/lanes/compute.py`

**Validation**: Test with a WP present in `code_wp_ids` but somehow missing from groups → error raised.

---

## Subtask T011: Fail Diagnostically on Missing Ownership Manifests

**Purpose**: When an executable WP has no ownership manifest at all, lane computation should fail with a clear error rather than silently including it without overlap checking (FR-007).

**Steps**:

1. In `compute.py` lines 177-181, change the WP filtering loop:
   ```python
   code_wp_ids: list[str] = []
   for wp_id in all_wp_ids:
       manifest = ownership_manifests.get(wp_id)
       if manifest and manifest.execution_mode == ExecutionMode.PLANNING_ARTIFACT:
           continue
       if not manifest:
           raise LaneComputationError(
               f"Executable WP '{wp_id}' has no ownership manifest. "
               f"Ensure owned_files and execution_mode are set in WP frontmatter, "
               f"or run finalize-tasks to infer them."
           )
       code_wp_ids.append(wp_id)
   ```

2. This is a behavioral change from the current silent-pass behavior. Verify that `finalize-tasks` always populates ownership manifests BEFORE calling `compute_lanes`. Check `mission.py` around line 1440 where `infer_ownership()` fills missing fields.

**Files**: `src/specify_cli/lanes/compute.py`

**Validation**: Test with a WP that has no manifest → error raised naming the WP.

---

## Subtask T012: Add Planning-Artifact Exclusion Diagnostic

**Purpose**: Make planning-artifact exclusions visible so operators can verify they're correct (FR-006).

**Steps**:

1. Collect planning-artifact WP IDs during the filtering loop:
   ```python
   planning_wps: list[str] = []
   for wp_id in all_wp_ids:
       manifest = ownership_manifests.get(wp_id)
       if manifest and manifest.execution_mode == ExecutionMode.PLANNING_ARTIFACT:
           planning_wps.append(wp_id)
           continue
       ...
   ```

2. Include `planning_wps` in the return value. Options:
   - Add a `planning_artifact_wps: list[str]` field to `LanesManifest` in `models.py`
   - Or return a separate diagnostic dict alongside the manifest

   Prefer adding to `LanesManifest` since it already has lane-related metadata.

3. Surface in JSON output from `finalize-tasks`:
   ```json
   "lanes": {
     "computed": true,
     "count": 3,
     "planning_artifact_wps": ["WP09"]
   }
   ```

**Files**: `src/specify_cli/lanes/compute.py`, `src/specify_cli/lanes/models.py`

**Validation**: Test with a planning-artifact WP → excluded from lanes but listed in diagnostic.

---

## Subtask T013: Add Glob-Match Validation Warning

**Purpose**: Warn when a WP's `owned_files` globs match zero actual files (FR-014).

**Steps**:

1. Add a new function to `src/specify_cli/ownership/validation.py`:
   ```python
   def validate_glob_matches(
       manifests: dict[str, OwnershipManifest],
       repo_root: Path,
   ) -> list[str]:
       """Warn when owned_files globs match zero files in the repo."""
       warnings: list[str] = []
       for wp_id, manifest in sorted(manifests.items()):
           for pattern in manifest.owned_files:
               if not any(repo_root.glob(pattern)):
                   warnings.append(
                       f"{wp_id}: owned_files glob '{pattern}' matches "
                       f"zero files in the repository"
                   )
       return warnings
   ```

2. Call from `finalize-tasks` (in `mission.py`) after building ownership manifests, include warnings in JSON output.

3. Warnings do not cause failure — they are informational.

**Files**: `src/specify_cli/ownership/validation.py`, `src/specify_cli/cli/commands/agent/mission.py`

**Validation**: Test with a glob pointing to a nonexistent directory → warning emitted.

---

## Subtask T014: Add Warning for src/** Fallback

**Purpose**: Make the broad `src/**` fallback visible so operators know a WP's scope is synthetic (FR-015).

**Steps**:

1. In `src/specify_cli/ownership/inference.py`, modify the fallback at line 135-136:
   ```python
   if not globs:
       globs = ["src/**"]
       warnings.append(
           f"No file paths found in WP body text; using broad fallback 'src/**'. "
           f"Consider adding explicit owned_files to WP frontmatter."
       )
   ```

2. Change `infer_owned_files` return type to include warnings. Two approaches:
   - Return `tuple[list[str], list[str]]` (globs, warnings)
   - Add warnings to a module-level list (not recommended — thread-unsafe)
   - Use the first approach

3. Update all callers of `infer_owned_files` to handle the new return type. Key caller: `infer_ownership()` at inference.py:183-205.

4. Propagate warnings through to `finalize-tasks` JSON output.

**Files**: `src/specify_cli/ownership/inference.py`

**Validation**: Test with a WP body that mentions no file paths → warning about src/** fallback.

---

## Subtask T015: Write Regression Tests

**Purpose**: Cover all WP02 changes with targeted tests.

**Tests to add/modify**:

1. **`tests/lanes/test_compute.py`** (modify):
   - `test_all_executable_wps_in_lanes`: 5 WPs → all 5 appear in lanes
   - `test_missing_manifest_raises_error`: WP without manifest → `LaneComputationError`
   - `test_planning_artifact_excluded_with_diagnostic`: planning WP excluded, listed in `planning_artifact_wps`
   - `test_completeness_check_catches_orphan_wp`: WP in code_wp_ids but not in groups → error

2. **`tests/ownership/test_validation.py`** (new or modify):
   - `test_glob_matches_zero_files_warning`: nonexistent glob → warning
   - `test_glob_matches_existing_files_no_warning`: valid glob → no warning

3. **`tests/ownership/test_inference.py`** (new or modify):
   - `test_src_fallback_emits_warning`: WP with no paths → warning message
   - `test_explicit_paths_no_fallback_warning`: WP with paths → no warning

**Files**: `tests/lanes/test_compute.py`, `tests/ownership/test_validation.py`, `tests/ownership/test_inference.py`

---

## Definition of Done

- [ ] Every executable WP appears in exactly one lane in `lanes.json`
- [ ] Missing ownership manifest → `LaneComputationError` naming the WP
- [ ] Planning-artifact WPs listed in diagnostic summary
- [ ] Zero-match glob → warning in JSON output
- [ ] `src/**` fallback → warning in JSON output
- [ ] All tests pass, mypy --strict clean on changed files
- [ ] Existing features with valid lanes.json still compute identically (regression check)

## Reviewer Guidance

- Check that `LaneComputationError` is raised BEFORE any lanes are written (fail-fast)
- Verify `infer_owned_files` API change is reflected in all callers (search for `infer_owned_files(` across codebase)
- Verify `planning_artifact_wps` appears in the LanesManifest serialization

## Activity Log

- 2026-04-06T14:11:15Z – claude:sonnet:implementer:implementer – shell_pid=10098 – Started implementation via action command
- 2026-04-06T14:17:59Z – claude:sonnet:implementer:implementer – shell_pid=10098 – Ready for review: T010-T015 all implemented and tested. LaneComputationError raised on missing manifests and completeness gaps, planning_artifact_wps field added to LanesManifest, validate_glob_matches warns on zero-match globs, infer_owned_files returns (globs, warnings) with src/** fallback warning. 1890 tests pass.
- 2026-04-06T14:18:20Z – claude:opus:reviewer:reviewer – shell_pid=11591 – Started review via action command
- 2026-04-06T14:21:52Z – claude:opus:reviewer:reviewer – shell_pid=11591 – Moved to planned
- 2026-04-06T14:22:07Z – claude:sonnet:implementer:implementer – shell_pid=12061 – Started implementation via action command
- 2026-04-06T14:24:37Z – claude:sonnet:implementer:implementer – shell_pid=12061 – Fixed: wired validate_glob_matches, ownership warnings, and planning_artifact_wps into JSON output
- 2026-04-06T14:25:02Z – claude:opus:reviewer:reviewer – shell_pid=12577 – Started review via action command

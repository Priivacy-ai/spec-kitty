---
work_package_id: WP02
title: Active-Mission Fallback Removal
lane: "approved"
dependencies: []
base_branch: 2.x
base_commit: ac3b601e46b48f9f9c2db1a96bc9caa9ca1a4f31
created_at: '2026-03-20T13:51:56.768729+00:00'
subtasks:
- T004
- T005
- T006
- T007
- T008
phase: Phase 1 - Core Cleanup
assignee: ''
agent: codex
shell_pid: '83615'
review_status: "approved"
reviewed_by: "Robert Douglass"
review_feedback: feedback://054-state-architecture-cleanup-phase-2/WP02/20260320T142248Z-b7877022.md
history:
- timestamp: '2026-03-20T13:39:48Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
---

# Work Package Prompt: WP02 – Active-Mission Fallback Removal

## Objectives & Success Criteria

- Remove project-level `.kittify/active-mission` fallback from manifest, verify, and diagnostics.
- All mission-sensitive operations resolve mission from feature-level `meta.json` or require explicit feature context.
- A project with a research-mission feature and no `.kittify/active-mission` verifies correctly as `research`.
- No behavior regression for existing workflows that already pass feature context.

## Context & Constraints

- **Evidence**: The Obsidian vault audit confirmed that `FileManifest.active_mission` returns `software-dev` when no `.kittify/active-mission` exists, even when the feature's `meta.json` says `research`. This is the highest-impact correctness bug.
- **Plan reference**: Design decision D2 in plan.md — hard removal, no deprecation period.
- **Key function**: `get_mission_for_feature(feature_dir, project_root)` already exists and reads from `meta.json`. Use this instead of the project-level fallback.
- **Constraint C-002**: Preserve working behavior for callers that already pass feature context.

## Implementation Command

```bash
spec-kitty implement WP02
```

## Subtasks & Detailed Guidance

### Subtask T004 – Remove `_detect_active_mission()` from manifest.py

**Purpose**: Eliminate the project-level mission fallback from the manifest module.

**Steps**:

1. In `src/specify_cli/manifest.py`:
   - Delete the `_detect_active_mission()` method (lines 20-33).
   - Remove `self.active_mission = self._detect_active_mission()` from `__init__()` (line 17).
   - Remove `self.mission_dir = kittify_dir / "missions" / self.active_mission` from `__init__()`.
   - Remove any property or attribute that exposes `active_mission`.

2. **Find all callers of `manifest.active_mission` and `manifest.mission_dir`**:
   ```bash
   grep -r "manifest\.active_mission\|manifest\.mission_dir\|\.active_mission\b" src/specify_cli/ --include="*.py"
   ```
   Each caller must be updated to either:
   - Accept a `feature_dir` parameter and resolve mission from `meta.json`, OR
   - Stop using mission context if it's not needed for that operation.

3. If `FileManifest` still needs a `mission_dir` for non-mission-sensitive operations (like listing available templates), make it accept an explicit `mission_key: str` parameter instead of auto-detecting.

**Files**:
- `src/specify_cli/manifest.py` (MODIFY)

**Edge Cases**:
- If `FileManifest` is used in contexts where no feature exists (e.g., `spec-kitty init`), those callers should pass an explicit mission key or use the default `software-dev`.

### Subtask T005 – Update verify_enhanced.py for feature-level mission

**Purpose**: Make verification resolve mission from feature `meta.json` instead of project-level fallback.

**Steps**:

1. In `src/specify_cli/verify_enhanced.py`:
   - Add `feature_dir: Path | None = None` parameter to `run_enhanced_verify()`.
   - When `feature_dir` is provided, resolve mission: `from specify_cli.feature_metadata import load_meta; meta = load_meta(feature_dir); mission = meta.get("mission", "software-dev")`.
   - When `feature_dir` is None, skip mission-sensitive file checks or use a default mission with a warning.
   - Replace `manifest.active_mission` references with the resolved mission.

2. Update callers of `run_enhanced_verify()` to pass `feature_dir` when available.

**Files**:
- `src/specify_cli/verify_enhanced.py` (MODIFY)
- Any CLI commands that call `run_enhanced_verify()` (MODIFY to pass feature_dir)

### Subtask T006 – Update diagnostics.py for feature-level mission

**Purpose**: Make dashboard diagnostics resolve mission per-feature.

**Steps**:

1. In `src/specify_cli/dashboard/diagnostics.py`:
   - Add `feature_dir: Path | None = None` parameter to `run_diagnostics()`.
   - When provided, resolve mission from `meta.json` (same pattern as T005).
   - Replace `manifest.active_mission` usage with the resolved mission.
   - Update `diagnostics['active_mission']` to show the feature-level mission (or "no feature context").

2. Update callers to pass `feature_dir`.

**Files**:
- `src/specify_cli/dashboard/diagnostics.py` (MODIFY)

### Subtask T007 – Update mission CLI for no-feature-context

**Purpose**: The `spec-kitty mission current` command should show a clear message instead of a silent project-level fallback.

**Steps**:

1. In `src/specify_cli/cli/commands/mission.py`:
   - Find `current_cmd()` (lines 186-231).
   - The `else` branch (no feature detected, lines ~220-231) currently calls `get_active_mission()` which reads `.kittify/active-mission`.
   - Replace with: display "No active feature detected. Use `--feature <slug>` to specify one, or run from within a feature worktree." and optionally list available features.

**Files**:
- `src/specify_cli/cli/commands/mission.py` (MODIFY)

### Subtask T008 – Tests for mission resolution changes

**Purpose**: Verify the new feature-level mission resolution works correctly.

**Steps**:

1. Add/update tests:
   - **test_verify_with_research_feature**: Create a project with a research-mission feature, no `.kittify/active-mission`. Run verify with `feature_dir`. Assert mission resolves to `research`.
   - **test_verify_without_feature_dir**: Run verify without `feature_dir`. Assert mission-sensitive checks are skipped or use default gracefully.
   - **test_diagnostics_with_feature_dir**: Same pattern as verify test for diagnostics.
   - **test_manifest_no_active_mission_property**: Instantiate `FileManifest`. Assert it has no `active_mission` attribute.
   - **test_mission_current_no_feature**: Mock no feature detection. Assert the CLI shows "No active feature detected" message.

2. Update any existing tests that relied on `manifest.active_mission`.

**Files**:
- `tests/cross_cutting/packaging/test_manifest_cli_filtering.py` (MODIFY)
- `tests/test_dashboard/test_diagnostics.py` (MODIFY)
- `tests/specify_cli/` (NEW or MODIFY tests)

**Validation**:
- `pytest tests/cross_cutting/packaging/test_manifest_cli_filtering.py tests/test_dashboard/test_diagnostics.py -v`

## Risks & Mitigations

- **Unknown callers of `manifest.active_mission`**: Grep thoroughly before removing. If a caller is missed, it will raise `AttributeError` at runtime — fail fast, but still a regression.
- **CLI command changes**: The `mission current` command behavior changes for the no-feature case. This is intentional per the spec.

## Review Guidance

- Verify ALL usages of `manifest.active_mission` and `manifest.mission_dir` are addressed.
- Verify the research-mission test actually creates a `meta.json` with `"mission": "research"`.
- Verify no silent fallback to `software-dev` remains in any code path.

## Activity Log

- 2026-03-20T13:39:48Z – system – lane=planned – Prompt created.
- 2026-03-20T13:51:57Z – coordinator – shell_pid=73479 – lane=doing – Assigned agent via workflow command
- 2026-03-20T14:00:50Z – coordinator – shell_pid=73479 – lane=for_review – Ready for review: removed active-mission fallback from FileManifest, verify_enhanced, diagnostics, and mission CLI. All 14 tests passing.
- 2026-03-20T14:01:32Z – codex – shell_pid=96119 – lane=doing – Started review via workflow command
- 2026-03-20T14:09:11Z – codex – shell_pid=96119 – lane=planned – Moved to planned
- 2026-03-20T14:09:21Z – coordinator – shell_pid=12831 – lane=doing – Started implementation via workflow command
- 2026-03-20T14:15:58Z – coordinator – shell_pid=12831 – lane=for_review – Fixed: production callers now pass feature_dir via _resolve_feature_dir helper and scan_all_features/resolve_active_feature (cycle 2/3)
- 2026-03-20T14:16:22Z – codex – shell_pid=24137 – lane=doing – Started review via workflow command
- 2026-03-20T14:22:48Z – codex – shell_pid=24137 – lane=planned – Moved to planned
- 2026-03-20T14:22:55Z – coordinator – shell_pid=45261 – lane=doing – Started implementation via workflow command
- 2026-03-20T14:37:53Z – coordinator – shell_pid=45261 – lane=for_review – Fixed: worktree detection uses main repo root for feature detection - locate_project_root() in diagnostics mode + _get_main_repo_root() in FeatureContext construction. Added realistic worktree test without detect_feature mock. (cycle 3/3 FINAL)
- 2026-03-20T14:38:20Z – codex – shell_pid=83615 – lane=doing – Started review via workflow command
- 2026-03-20T14:42:14Z – codex – shell_pid=83615 – lane=approved – Review passed: removed manifest active-mission fallback and verified feature-level mission resolution in verify, diagnostics, and mission current

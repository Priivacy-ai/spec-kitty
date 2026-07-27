**Review cycle 1 — WP03: Planning Artifact Lane Unification**

## Result: Changes requested

The core lane-planning model is correctly implemented (FR-101..FR-106, FR-503 pass in the new tests), but 9 pre-existing tests that encoded the OLD behavior were not updated to reflect the new contract. These tests now fail and must be fixed before the WP can be approved.

---

## Issue 1: Stale test assertions — `authoritative_ref is None` still expected

**Failing tests:**
- `tests/specify_cli/context/test_resolver.py::TestResolveContext::test_authoritative_ref_none_for_planning_artifact`
- `tests/specify_cli/integration/test_context_lifecycle.py::TestContextFieldCorrectness::test_authoritative_ref_none_for_planning_artifact`

**Assertion that breaks:** `assert ctx.authoritative_ref is None`

**Actual behavior after WP03:** `authoritative_ref` is now `"main"` (or the target branch), not `None`. This is the correct new behavior — FR-105 explicitly requires uniform lane lookup. The tests must be updated to assert the new contract: `assert ctx.authoritative_ref == "main"` (or whatever the target_branch is in the fixture).

---

## Issue 2: Stale test assertion — `resolved.lane_id is None` expected

**Failing test:**
- `tests/runtime/test_workspace_context_unit.py::TestContextIndexAndResolution::test_resolve_workspace_for_wp_returns_repo_root_for_inferred_planning_artifact`

**Assertion that breaks:** `assert resolved.lane_id is None`

**Actual behavior after WP03:** `lane_id` is now `"lane-planning"`, not `None`. FR-102 requires the canonical lane_id to be `"lane-planning"`. Update the assertion to `assert resolved.lane_id == "lane-planning"`.

---

## Issue 3: Stale topology test assertions — `lane_id is None` expected

**Failing tests:**
- `tests/specify_cli/core/test_worktree_topology.py::test_mixed_mission_topology_includes_repo_root_planning_entry`
- `tests/specify_cli/core/test_worktree_topology.py::test_render_topology_json_marks_repo_root_planning_workspace`
- `tests/specify_cli/core/test_worktree_topology.py::test_planning_only_mission_without_lanes_json_still_materializes_topology`

**Assertions that break:** `assert planning_entry.lane_id is None` and `assert planning_entry["lane_id"] is None`

**Fix:** Update these assertions to `assert planning_entry.lane_id == "lane-planning"` (and the JSON equivalent).

---

## Issue 4: Stale prompt builder test — wrong workspace label expected

**Failing tests:**
- `tests/next/test_prompt_builder_unit.py::TestBuildPromptWPPlanningArtifact::test_implement_prompt_for_planning_artifact_uses_repo_root_workspace_label`
- `tests/next/test_prompt_builder_unit.py::TestBuildPromptWPPlanningArtifact::test_review_prompt_for_planning_artifact_without_claim_commit_says_unavailable`
- `tests/next/test_prompt_builder_unit.py::TestBuildPromptWPPlanningArtifact::test_review_prompt_with_claim_commit_emits_pathspec_review_commands`

**Assertion that breaks:** `assert "Workspace contract: repository root planning workspace" in text`

**Actual output after WP03:** `"Workspace contract: lane lane-planning shared by WP02"`

**Fix:** Update the expected string to `"Workspace contract: lane lane-planning"` (or the full new format). The workspace_name field now uses `f"{mission_slug}-{PLANNING_LANE_ID}"` instead of `f"{mission_slug}-repo-root"`, which changes the prompt builder output. Investigate what downstream prompt-rendering logic depends on `workspace_name` and update the assertion to match the new canonical label.

---

## Issue 5: Stale workflow canonical cleanup test — wrong workspace label expected

**Failing test:**
- `tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py::TestPlanningArtifactWorkflowPrompt::test_implement_prompt_uses_repo_root_for_planning_artifact`

Same root cause as Issue 4 — workspace label changed from `"repository root planning workspace"` to `"lane lane-planning"`. Update the assertion.

---

## What is correct and should NOT be changed

- FR-101..FR-106 are correctly implemented: `compute.py`, `branch_naming.py`, `resolver.py`, `workspace_context.py`, `implement.py` all correctly implement the new contract.
- FR-503 is correctly implemented: `implement --help` contains "internal", "spec-kitty next", and "spec-kitty agent action implement".
- All 74 new tests in `tests/lanes/` and `tests/agent/cli/commands/test_implement_help.py` pass.
- The `planning_artifact_wps` derived view is preserved for backward compat.
- No `execution_mode == "planning_artifact"` branches remain in `resolver.py`.
- The pre-existing test failures for `test_adversarial` and `test_research_workflow_integration` (both fail with `--no-git` option error) are NOT introduced by WP03 and are pre-existing — do NOT fix those in this WP.

## Fix summary

Update the 9 stale tests (Issues 1–5) to assert the new contract. The changes are purely mechanical: replace `is None` with `== "lane-planning"` for `lane_id`, replace `is None` with `== target_branch` for `authoritative_ref`, and replace `"repository root planning workspace"` with the new `"lane lane-planning"` label in prompt assertions.

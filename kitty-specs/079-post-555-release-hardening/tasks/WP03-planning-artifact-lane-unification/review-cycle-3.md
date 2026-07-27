## Cycle 3 Review Feedback

### Summary

Cycle 2 fixed the 9 stale tests that caused Cycle 1 rejection. The core implementation (FR-101..FR-106, FR-503) is correct and 9,716 tests pass. However, **one additional stale test was introduced by WP03's main implementation commit**, which must be fixed before approval.

---

### Issue 1 — Stale test in `test_workflow_canonical_cleanup.py` (blocking)

**File**: `tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py`
**Test**: `TestPlanningArtifactWorkflowPrompt::test_implement_prompt_uses_repo_root_for_planning_artifact`

**Status before WP03 main commit**: PASSING
**Status after WP03 main commit**: FAILING

**Root cause**: WP03's implementation commit (`760d0a22`) changed the prompt template wording for planning-artifact WPs. The test was not updated to reflect the new contract text.

**Assertions that now fail**:
1. `assert "Workspace contract: repository root planning workspace" in prompt`
   - Actual output: `"Workspace contract: lane lane-planning shared by WP02"`
2. `assert "This WP runs in the repository root" in prompt`
   - This line may also be absent from the updated prompt output

**How to fix**: Update the test assertions to match the new wording produced by WP03. The correct approach is either:
- Update the assertion to check for `"lane lane-planning"` (the new canonical contract text), OR
- Update the prompt template to preserve `"repository root planning workspace"` text for planning-artifact WPs (if that wording was intentional), and update the test accordingly.

The workspace itself **is** correctly routing to the repo root (the `Workspace:` line shows the correct path), so the functional behavior is correct. Only the contract description text and any "repository root" messaging changed.

**Verification command**:
```bash
poetry run pytest tests/specify_cli/cli/commands/agent/test_workflow_canonical_cleanup.py::TestPlanningArtifactWorkflowPrompt::test_implement_prompt_uses_repo_root_for_planning_artifact -v
```
Must pass before approval.

---

### Pre-existing failures (non-blocking, do not fix)

The following failures were pre-existing before WP03 and are NOT introduced by WP03. Do not attempt to fix them:
- `tests/adversarial/test_distribution.py::TestInitWithoutTemplateRoot::test_init_creates_project_structure` (from WP01, already approved)
- `tests/agent/test_init_command.py` (5 errors, from WP01, already approved)
- `tests/research/test_research_workflow_integration.py::test_full_research_workflow_via_cli` (pre-existed on main before all WP03 changes)

---

### All other checks pass

- The 9 Cycle 1 stale tests: all pass (97/97 in targeted run)
- `resolver.py`: no `execution_mode == "planning_artifact"` branches remain
- `compute.py`: planning-artifact WPs assigned to `lane-planning` lane
- `branch_naming.py`: `lane_branch_name(..., "lane-planning")` returns `"main"` (or planning base branch)
- `implement.py`: docstring updated with "internal infrastructure", "spec-kitty next", "spec-kitty agent action implement" (FR-503)
- `LanesManifest.planning_artifact_wps`: preserved as derived view
- `workspace_context.py` + `worktree.py`: lane-planning routes to main repo root
- Full owned-file suite (tests/lanes/ + tests/agent/cli/commands/test_implement_help.py): 173/173 pass

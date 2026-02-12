---
work_package_id: WP09
title: End-to-end CLI smoke test
lane: planned
dependencies:
- WP01
subtasks:
- T040
- T041
- T042
- T043
- T044
phase: Wave 3 - Integration
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-12T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 – End-to-end CLI smoke test

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP09 --base WP01
```

Depends on WP01 (setup-plan must work). Use WP01 as base since it fixes the planning workflow that this test exercises.

---

## Objectives & Success Criteria

- Full `create-feature → setup-plan → finalize-tasks → implement → move-task` sequence completes without errors
- All intermediate artifacts verified (spec.md, plan.md, tasks/, worktree)
- Test is self-contained (creates and cleans up its own temp repo)
- Test passes locally on the 2.x branch
- Marked with `pytest.mark.e2e` for optional CI separation

## Context & Constraints

- **Delivery branch**: 2.x
- **Dependency on WP01**: The `setup-plan` command must work (NameError fixed)
- **Test isolation**: Must create a fresh git repo, not modify the spec-kitty source repo
- **CLI invocation**: Use `typer.testing.CliRunner` for in-process testing, or `subprocess.run` for true E2E
- **Reference**: `spec.md` (FR-016), `plan.md` (WP09)

## Subtasks & Detailed Guidance

### Subtask T040 – Create tests/e2e/ directory structure

- **Purpose**: Set up the E2E test directory with proper Python package structure.
- **Steps**:
  1. Create the directory structure:
     ```
     tests/e2e/
     ├── __init__.py
     └── conftest.py
     ```
  2. In `conftest.py`, add shared fixtures:
     ```python
     import pytest
     import subprocess
     from pathlib import Path
     import tempfile
     import shutil

     @pytest.fixture
     def temp_repo(tmp_path):
         """Create a temporary git repository with spec-kitty initialized."""
         repo_dir = tmp_path / "test-project"
         repo_dir.mkdir()

         # Initialize git
         subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
         subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True, capture_output=True)
         subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, check=True, capture_output=True)

         # Create initial commit
         (repo_dir / "README.md").write_text("# Test Project\n")
         subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
         subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)

         # Initialize spec-kitty
         subprocess.run(["spec-kitty", "init"], cwd=repo_dir, check=True, capture_output=True)
         subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
         subprocess.run(["git", "commit", "-m", "Add spec-kitty"], cwd=repo_dir, check=True, capture_output=True)

         yield repo_dir

         # Cleanup is handled by tmp_path
     ```
  3. Make the fixture robust: handle cases where spec-kitty is not on PATH
- **Files**: `tests/e2e/__init__.py` (new), `tests/e2e/conftest.py` (new)
- **Parallel?**: No — foundation for T041/T042

### Subtask T041 – Write temp repo fixture with full .kittify setup

- **Purpose**: The fixture from T040 provides basic git + spec-kitty. This subtask ensures the repo has enough structure for the full workflow.
- **Steps**:
  1. Extend the `temp_repo` fixture or create a more specific one:
     ```python
     @pytest.fixture
     def smoke_test_repo(temp_repo):
         """Temp repo with .kittify properly configured for full workflow."""
         repo_dir = temp_repo

         # Ensure .kittify has necessary config
         kittify_dir = repo_dir / ".kittify"
         assert kittify_dir.exists(), "spec-kitty init should create .kittify/"

         # Create a minimal source directory
         src_dir = repo_dir / "src"
         src_dir.mkdir()
         (src_dir / "__init__.py").write_text("")

         # Commit the source directory
         subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
         subprocess.run(["git", "commit", "-m", "Add source"], cwd=repo_dir, check=True, capture_output=True)

         return repo_dir
     ```
  2. Verify the fixture creates a valid project state
- **Files**: `tests/e2e/conftest.py` (extend)
- **Parallel?**: No — depends on T040

### Subtask T042 – Implement full E2E test sequence

- **Purpose**: Exercise the complete CLI workflow end-to-end.
- **Steps**:
  1. Create `tests/e2e/test_cli_smoke.py`:
     ```python
     import pytest
     import subprocess
     import json
     from pathlib import Path

     @pytest.mark.e2e
     def test_full_cli_workflow(smoke_test_repo):
         """Full create-feature → setup-plan → implement → review workflow."""
         repo = smoke_test_repo

         # Step 1: Create feature
         result = subprocess.run(
             ["spec-kitty", "agent", "feature", "create-feature", "smoke-test", "--json"],
             cwd=repo, capture_output=True, text=True, check=True
         )
         output = json.loads(result.stdout)
         assert output["result"] == "success"
         feature_slug = output["feature"]
         feature_dir = Path(output["feature_dir"])

         # Step 2: Write a minimal spec.md
         spec_content = "# Spec: Smoke Test\n\n## Requirements\n- FR-001: Hello world\n"
         (feature_dir / "spec.md").write_text(spec_content)
         subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
         subprocess.run(["git", "commit", "-m", "Add spec"], cwd=repo, check=True, capture_output=True)

         # Step 3: Setup plan
         result = subprocess.run(
             ["spec-kitty", "agent", "feature", "setup-plan", "--feature", feature_slug, "--json"],
             cwd=repo, capture_output=True, text=True, check=True
         )
         output = json.loads(result.stdout)
         assert output["result"] == "success"
         assert (feature_dir / "plan.md").exists()

         # Step 4: Write minimal tasks.md and WP prompt
         tasks_dir = feature_dir / "tasks"
         tasks_dir.mkdir(exist_ok=True)

         tasks_md = "# Work Packages\n## WP01: Hello World\n### Included Subtasks\n- [ ] T001 Create hello.py\n"
         (feature_dir / "tasks.md").write_text(tasks_md)

         wp_content = '---\nwork_package_id: "WP01"\ntitle: "Hello World"\nlane: "planned"\ndependencies: []\nsubtasks: ["T001"]\nhistory:\n  - timestamp: "2026-02-12T00:00:00Z"\n    lane: "planned"\n    agent: "system"\n    shell_pid: ""\n    action: "Created"\n---\n\n# WP01 – Hello World\n\nCreate hello.py\n'
         (tasks_dir / "WP01-hello-world.md").write_text(wp_content)

         subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
         subprocess.run(["git", "commit", "-m", "Add tasks"], cwd=repo, check=True, capture_output=True)

         # Step 5: Implement WP01 (create workspace)
         result = subprocess.run(
             ["spec-kitty", "implement", "WP01"],
             cwd=repo, capture_output=True, text=True
         )
         # Check workspace was created
         worktree_dir = repo / ".worktrees" / f"{feature_slug}-WP01"
         assert worktree_dir.exists() or result.returncode == 0

         # Step 6: Make a change in workspace and commit
         if worktree_dir.exists():
             (worktree_dir / "src" / "hello.py").write_text("print('hello')\n")
             subprocess.run(["git", "add", "."], cwd=worktree_dir, check=True, capture_output=True)
             subprocess.run(["git", "commit", "-m", "feat(WP01): hello world"], cwd=worktree_dir, check=True, capture_output=True)

         # Step 7: Move to for_review
         result = subprocess.run(
             ["spec-kitty", "agent", "tasks", "move-task", "WP01",
              "--to", "for_review", "--feature", feature_slug, "--json"],
             cwd=repo, capture_output=True, text=True
         )

         # Verify final state
         assert (feature_dir / "spec.md").exists()
         assert (feature_dir / "plan.md").exists()
         assert (feature_dir / "tasks.md").exists()
         assert (feature_dir / "tasks" / "WP01-hello-world.md").exists()
     ```
  2. Handle edge cases:
     - If `spec-kitty` is not on PATH, skip the test with `pytest.mark.skipif`
     - If workspace creation fails (may need specific git version), log details
  3. Ensure cleanup is thorough (worktrees, branches)
- **Files**: `tests/e2e/test_cli_smoke.py` (new)
- **Parallel?**: No — sequential test steps
- **Notes**: The test exercises the critical path. It doesn't test sync (no server). It's a "does the workflow hold together" test.

### Subtask T043 – Add pytest.mark.e2e marker to pyproject.toml

- **Purpose**: Allow CI to selectively run or skip E2E tests.
- **Steps**:
  1. Read `pyproject.toml` to find the `[tool.pytest.ini_options]` section
  2. Add the `e2e` marker:
     ```toml
     [tool.pytest.ini_options]
     markers = [
         "e2e: End-to-end tests that exercise the full CLI workflow (may be slow)",
     ]
     ```
  3. If markers already exist, append to the list
  4. This enables: `python -m pytest tests/ -m "not e2e"` to skip E2E in fast test runs
- **Files**: `pyproject.toml` (edit)
- **Parallel?**: Yes — independent file edit

### Subtask T044 – Verify test passes locally

- **Purpose**: Confirm the E2E test works on the 2.x branch before marking as complete.
- **Steps**:
  1. Run the E2E test:
     ```bash
     python -m pytest tests/e2e/test_cli_smoke.py -v -s
     ```
  2. If it fails:
     - Check the failure output carefully
     - Common issues: spec-kitty not on PATH, git version incompatibility, missing worktree support
     - Fix the test or add appropriate `pytest.mark.skipif` conditions
  3. Run the full test suite (excluding E2E) to verify no regressions:
     ```bash
     python -m pytest tests/ -m "not e2e" -x -q
     ```
  4. Document any CI-specific considerations (environment variables, git config, PATH requirements)
- **Files**: No changes expected (verification only)
- **Parallel?**: No — depends on T040-T043

## Test Strategy

- **New tests**: 1 comprehensive E2E test + fixtures
- **Run command**: `python -m pytest tests/e2e/ -v -s`
- **Skip in fast CI**: `python -m pytest tests/ -m "not e2e" -x -q`
- **Prerequisites**: `spec-kitty` on PATH, git available, temp directory writable

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| E2E test is flaky (timing, filesystem) | Generous timeouts; cleanup in fixture teardown; isolated tmp_path |
| spec-kitty not on PATH in CI | Use `pytest.mark.skipif(not shutil.which("spec-kitty"))` |
| Worktree creation needs specific git version | Check git version in fixture; skip if too old |
| Test modifies spec-kitty source repo | Use isolated tmp_path; never operate on CWD |

## Review Guidance

- Verify test creates a FRESH repo (not modifying source)
- Verify all 7 steps of the workflow are exercised and assertions check intermediate state
- Verify cleanup is thorough (no leftover worktrees, branches, or temp files)
- Run `python -m pytest tests/e2e/test_cli_smoke.py -v -s` — passes
- Verify `pytest.mark.e2e` marker is registered in pyproject.toml

## Activity Log

- 2026-02-12T12:00:00Z – system – lane=planned – Prompt created.

---
work_package_id: WP02
title: e2e Parity Ratchet — CWD-Invariance Gate
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: claude
history:
- date: '2026-06-03'
  event: created
  author: spec-kitty
agent_profile: python-pedro
authoritative_surface: tests/architectural/
execution_mode: code_change
owned_files:
- tests/architectural/test_execution_context_parity.py
- .github/workflows/*.yml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load` and specify profile `python-pedro` before reading further. This profile configures your role as a Python test implementer.

---

## Objective

Build the e2e CWD-parity ratchet: a test that proves the `next → implement → move-task → review → status` command sequence produces identical results when invoked from the **main-checkout CWD** and from the **lane-worktree CWD**. This test is Strangler step 1 and **gates all subsequent steps** (WP03, WP04, WP06).

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: assigned from `lanes.json`; do not guess worktree path
- **Prerequisite**: WP01 (ADRs) must be merged to `main` before starting
- Start with: `spec-kitty agent action implement WP02 --agent claude`

## Context

The root failure class in #1619 is command surfaces that re-derive execution context independently, so the same command invoked from different CWDs produces different results. The ratchet is the only automated proof that a surface has been *unified* rather than *re-masked with a different bug*.

**Existing test pattern to follow**: `tests/architectural/test_shared_package_boundary.py` — look at its fixture setup, `tmp_path` usage, and how it uses subprocess invocations.

**Existing integration test infrastructure**: `tests/integration/conftest.py` — check for shared fixtures for creating tmp repos.

**Test placement**: `tests/architectural/test_execution_context_parity.py` — architectural tests, not integration tests, because CWD-invariance is an architectural invariant.

---

## Subtask T006 — Create Ratchet Test Fixture

**Purpose**: Set up a temporary git repo with an initialized `.kittify/`, a mission, and two work packages. This fixture is reused by T007 and T008.

**Steps**:
1. Study `tests/integration/conftest.py` for existing repo/mission setup helpers
2. Study `tests/architectural/conftest.py` for shared architectural fixtures
3. Create a `pytest` fixture (scope=`function` or `module`) in `test_execution_context_parity.py` that:
   - Creates a `tmp_path` git repo
   - Runs `spec-kitty` initialization (or uses test helpers) to set up `.kittify/`
   - Creates a mission with slug `test-parity-mission`
   - Creates two work packages: WP01 and WP02 (WP02 depends on WP01)
   - Runs `spec-kitty agent mission finalize-tasks` to compute lanes
   - Returns `(repo_root, worktree_path)` where `worktree_path` is the lane worktree for WP01

**Key implementation detail**: Use `subprocess` calls with `cwd=repo_root` (not `os.chdir`) to avoid global process state mutation. Example:
```python
def run_cmd(args, cwd):
    result = subprocess.run(
        ["spec-kitty"] + args, cwd=cwd, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return result.stdout
```

**Validation**: Fixture produces a valid repo with `lanes.json` and at least one worktree path.

---

## Subtask T007 — Main-CWD Command Sequence

**Purpose**: Run the full `next → implement → move-task → review → status` sequence from the main checkout CWD and capture the output.

**Steps**:
1. Using the fixture from T006, with `cwd=repo_root`:
   ```python
   # Step 1: next (resolves WP to implement)
   next_out = run_cmd(["next", "--agent", "claude", "--mission", mission_slug, "--json"], cwd=repo_root)
   wp_id = json.loads(next_out)["wp_id"]  # should be "WP01"

   # Step 2: implement (creates worktree, claims WP)
   run_cmd(["agent", "action", "implement", wp_id, "--agent", "claude", "--mission", mission_slug], cwd=repo_root)

   # Step 3: move-task to in_progress
   run_cmd(["move-task", wp_id, "in_progress", "--mission", mission_slug], cwd=repo_root)

   # Step 4: review
   run_cmd(["move-task", wp_id, "for_review", "--mission", mission_slug], cwd=repo_root)

   # Step 5: status
   status_out = run_cmd(["agent", "tasks", "status", "--mission", mission_slug, "--json"], cwd=repo_root)
   ```
2. Store `main_cwd_result = {"wp_id": wp_id, "status": json.loads(status_out)}`

**Note**: The exact command arguments may differ — check `spec-kitty --help` for the actual subcommand structure. Adjust to match.

---

## Subtask T008 — Lane-CWD Command Sequence

**Purpose**: Run the same status-relevant portion of the sequence from the lane-worktree CWD and capture the output.

**Steps**:
1. Using the worktree path from T006 (the lane worktree created by `implement`):
   ```python
   # From lane worktree CWD, run move-task and status
   run_cmd(["move-task", wp_id, "in_progress", "--mission", mission_slug], cwd=worktree_path)
   run_cmd(["move-task", wp_id, "for_review", "--mission", mission_slug], cwd=worktree_path)
   status_out = run_cmd(["agent", "tasks", "status", "--mission", mission_slug, "--json"], cwd=worktree_path)
   ```
   
   **Important**: Reset lane state between T007 and T008 so both start from the same state. Either run T008 on a fresh fixture instance, or reset the WP lane back to `planned` before T008.

2. Store `lane_cwd_result = {"status": json.loads(status_out)}`

---

## Subtask T009 — Parity Assertions

**Purpose**: Assert that the resolved WP identity, lane state, and status output are identical between both CWD invocations.

**Steps**:
1. Write assertion comparing `main_cwd_result` and `lane_cwd_result`:
   ```python
   def test_cwd_parity(repo_fixture):
       repo_root, worktree_path, mission_slug = repo_fixture

       # Run from main CWD
       main_status = get_status_json(cwd=repo_root, mission=mission_slug)

       # Run from lane CWD
       lane_status = get_status_json(cwd=worktree_path, mission=mission_slug)

       # Assert parity: same WP lanes
       assert main_status["wps"]["WP01"]["lane"] == lane_status["wps"]["WP01"]["lane"]
       # Assert full JSON equality (field-by-field, not string match — timestamps may differ)
       for wp_id in main_status["wps"]:
           assert main_status["wps"][wp_id]["lane"] == lane_status["wps"][wp_id]["lane"]
   ```

2. **Also test that the ratchet catches a violation**: Add a test that mocks or temporarily breaks CWD-awareness in a known way and verifies the test fails:
   ```python
   def test_ratchet_catches_divergence(repo_fixture, monkeypatch):
       # Simulate divergence by pointing one read path to a stale dir
       # Assert that the status outputs differ (prove the test is not vacuously passing)
       ...
   ```
   This "injection proof" ensures the ratchet catches real regressions, not just structural presence.

**Validation**: Both `test_cwd_parity` and `test_ratchet_catches_divergence` pass.

---

## Subtask T010 — Register in CI Path Filter

**Purpose**: Ensure the ratchet runs in CI for every PR touching execution-context code paths.

**Steps**:
1. Open `.github/workflows/ci*.yml` (whichever file contains path-triggered test runs)
2. Find the `paths` filter for the test job (or create one)
3. Add these paths to trigger the test:
   ```yaml
   paths:
     - "src/specify_cli/core/execution_context.py"
     - "src/specify_cli/status/**"
     - "src/runtime/next/**"
     - "src/specify_cli/cli/commands/agent/**"
     - "tests/architectural/test_execution_context_parity.py"
   ```
4. Verify the test runs in the CI job that covers `tests/architectural/`

**Validation**: CI configuration updated. Confirm by checking that `pytest tests/architectural/test_execution_context_parity.py` is invoked in the CI job.

---

## Definition of Done

- [ ] `tests/architectural/test_execution_context_parity.py` exists
- [ ] `test_cwd_parity` passes locally
- [ ] `test_ratchet_catches_divergence` proves the test is not vacuously passing
- [ ] Test registered in CI path filter
- [ ] All existing tests still pass (`pytest tests/architectural/ -x`)
- [ ] e2e ratchet is green in CI

## Risks

- Command surface API may have changed — verify subcommand names against `spec-kitty --help` before coding
- `finalize-tasks` may not be callable from test fixtures without a full repo setup — investigate existing integration test helpers first
- CWD simulation via subprocess `cwd=` is correct; do NOT use `os.chdir()` (global process mutation)

## Reviewer Guidance

Verify that:
1. The test uses subprocess `cwd=` for CWD simulation, not `os.chdir()`
2. `test_ratchet_catches_divergence` actually fails when CWD-parity is broken (not vacuously passing)
3. The CI path filter covers all execution-context-adjacent files

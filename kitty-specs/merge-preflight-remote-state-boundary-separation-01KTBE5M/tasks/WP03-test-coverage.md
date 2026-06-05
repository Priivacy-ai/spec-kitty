---
work_package_id: WP03
title: Test Coverage
dependencies:
- WP02
requirement_refs:
- FR-009
- FR-010
- NFR-003
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-merge-preflight-remote-state-boundary-separation-01KTBE5M
base_commit: ce677cf2e887888e458500426561d69ea2a2c6a0
created_at: '2026-06-05T10:33:16.540891+00:00'
subtasks:
- T009
- T010
- T011
agent: "claude:sonnet:implementer-ivan:implementer"
shell_pid: "58728"
history:
- date: '2026-06-05'
  author: spec-kitty.tasks
  note: Initial WP generation
agent_profile: implementer-ivan
authoritative_surface: tests/merge/
execution_mode: code_change
owned_files:
- tests/merge/test_target_branch_preflight.py
- tests/merge/test_push_preflight.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Update the existing merge preflight test suite and add new tests that verify: (1) "ahead" state no longer blocks merge, (2) the push=True/False × origin-state matrix is correct, and (3) the exact #1706 scenario completes without error.

---

## Context

**WP02 must be merged before this WP starts.**

**Key file**: `tests/merge/test_target_branch_preflight.py`

Read this file completely before making any changes. Understand what each test currently does and what fixture/mock it uses. The main changes are:

1. `test_merge_preflight_blocks_unsafe_target_with_non_destructive_guidance` — currently uses `"ahead"` as the blocked-state fixture. After WP02, `"ahead"` no longer blocks. This test must be updated to use `"diverged"` as the blocked state.

2. Some tests may import `TargetBranchSyncStatus` from `specify_cli.merge.preflight` — update these imports to `specify_cli.merge.push_preflight`.

3. New tests are needed for the push-guarded path and the #1706 regression scenario.

---

## Subtask T009 — Invert Blocked-Ahead Test Assertions

**Purpose**: The test that asserted `"ahead"` blocks merge must be corrected to assert it does NOT block.

**File**: `tests/merge/test_target_branch_preflight.py`

**Steps**:

1. Find the test(s) that use `"ahead"` as the unsafe state. The known test is `test_merge_preflight_blocks_unsafe_target_with_non_destructive_guidance`.

2. For each such test, do ONE of the following (choose the approach that best fits the existing test structure):

   **Option A — Change the fixture state to `"diverged"`**:
   ```python
   # Before: fixture used "ahead" to test blocking
   # After: use "diverged" which IS a push-blocking state
   mock_sync_status = MagicMock()
   mock_sync_status.state = "diverged"
   mock_sync_status.is_safe_to_push = False
   ```

   **Option B — Add a separate "ahead is not blocked" assertion**:
   Keep the existing test for `"diverged"` blocking. Add a new test that verifies `"ahead"` with `push=False` does NOT block:
   ```python
   def test_merge_does_not_block_when_ahead_and_no_push():
       # ...set up ahead state...
       # assert merge completes without Exit(1)
   ```

3. Update any imports of `TargetBranchSyncStatus`, `TargetBranchRefreshStatus` to come from `specify_cli.merge.push_preflight` (not `specify_cli.merge.preflight`).

**Validation**: `pytest tests/merge/test_target_branch_preflight.py -v -k "ahead"` passes.

---

## Subtask T010 — Add Push-Path Safety Tests

**Purpose**: Cover the full origin-state × push/no-push matrix to prevent future regressions.

**File**: `tests/merge/test_push_preflight.py` (new file, or add to existing file — choose the more natural location)

**Test matrix to cover**:

| Origin state | push=False | push=True |
|---|---|---|
| `in_sync` | ✅ proceeds | ✅ proceeds |
| `ahead` | ✅ proceeds (was blocked — key regression) | ✅ proceeds |
| `behind` | ✅ proceeds | ⚠️ proceeds (git handles rejection) |
| `diverged` | ✅ proceeds | ❌ blocked |
| `no_tracking_branch` | ✅ proceeds | ✅ proceeds |

**For `push=False` tests** (testing the call-site gate):
```python
@pytest.mark.parametrize("state", ["in_sync", "ahead", "behind", "diverged", "no_tracking_branch"])
def test_merge_no_push_never_calls_push_preflight(state, mocker):
    """When push=False, push_preflight.check_push_safety must never be called."""
    mock_check = mocker.patch("specify_cli.merge.push_preflight.check_push_safety")
    # Invoke the merge command (or the relevant function) with push=False
    # ...
    mock_check.assert_not_called()
```

**For `push=True` tests** (testing push-safety decisions):
```python
@pytest.mark.parametrize("state,expected_blocked", [
    ("in_sync", False),
    ("ahead", False),
    ("behind", False),
    ("diverged", True),
    ("no_tracking_branch", False),
])
def test_push_safety_decision(state, expected_blocked, mocker):
    """check_push_safety returns is_safe_to_push=True for all non-diverged states."""
    # Mock git fetch to succeed
    # Mock rev-list to return appropriate ahead/behind counts for 'state'
    result = check_push_safety(repo_root=Path("/fake"), target_branch="main")
    assert result.is_safe_to_push == (not expected_blocked)
```

Focus on unit tests for `check_push_safety` directly, mocking the `subprocess` calls. For the call-site gate (push=False never calls check), use a mock at the module boundary.

**Validation**: `pytest tests/merge/test_push_preflight.py -v` exits 0. Coverage for `push_preflight.py` ≥90% when running `pytest tests/merge/ --cov=specify_cli.merge.push_preflight`.

---

## Subtask T011 — Add #1706 Regression Test

**Purpose**: Prevent reintroduction of the exact bug reported in issue #1706: a user with local main ahead AND behind origin cannot run `spec-kitty merge` without `--push`.

**File**: `tests/merge/test_target_branch_preflight.py` (or new file — place where it reads most naturally)

**Test scenario**:
- Local `main` is 10 commits ahead of `origin/main`
- Local `main` is 5 commits behind `origin/main`
- `spec-kitty merge` is invoked without `--push`
- Expected: merge proceeds to local lane integration (no `typer.Exit(1)` from the preflight)

```python
def test_issue_1706_ahead_and_behind_does_not_block_no_push_merge():
    """Regression: local main ahead+behind of origin must not block local-only merge.

    Issue: https://github.com/Priivacy-ai/spec-kitty/issues/1706
    """
    # Set up a mock sync status that returns "diverged" (10 ahead, 5 behind)
    # representing the #1706 scenario
    mock_status = TargetBranchSyncStatus(
        target_branch="main",
        tracking_branch="origin/main",
        ahead_count=10,
        behind_count=5,
        state="diverged",
    )
    # When push=False, the preflight should NOT be called
    # Verify that calling the merge command (or its internal function)
    # with push=False and a diverged state does NOT raise typer.Exit(1)
    # This can be tested by:
    # Option A: Mock check_push_safety and assert it's never called
    # Option B: Call _enforce_target_branch_sync_preflight directly with push=False
    #           and verify it's a no-op
```

Add a `# Regression: https://github.com/Priivacy-ai/spec-kitty/issues/1706` comment so the test is traceable.

**Validation**: `pytest -v -k "1706"` exits 0. The test description clearly states the scenario and expected outcome.

---

## Branch Strategy

**Planning base branch**: `main`
**Merge target**: `main`

To start: `spec-kitty agent action implement WP03 --agent claude`

---

## Definition of Done

- [ ] Existing tests that asserted `"ahead"` blocks merge are updated — they now use `"diverged"` or are inverted
- [ ] No test imports `TargetBranchSyncStatus` from `specify_cli.merge.preflight` (import must come from `push_preflight`)
- [ ] New tests cover all five origin states for `push=False` (none blocked)
- [ ] New tests cover `push=True` × `diverged` (blocked) and `push=True` × `ahead`/`in_sync` (not blocked)
- [ ] `test_issue_1706_ahead_and_behind_does_not_block_no_push_merge` exists and passes
- [ ] `pytest tests/merge/ -v` exits 0
- [ ] Coverage for `push_preflight.py` ≥90%

## Risks

- **Fixture complexity**: The #1706 test may need a realistic git fixture (not just a mock). If the existing test infrastructure does not support creating a real git repo with the required ahead/behind state, use mocks at the `subprocess` boundary instead.
- **Import path changes**: Tests that did `from specify_cli.merge.preflight import TargetBranchSyncStatus` will break after WP01/WP02. Fix these imports before adding new tests.
- **Mock boundary choice**: Tests can mock at `subprocess.run` level or at `check_push_safety` level. Prefer mocking at the module function boundary (e.g., `mocker.patch("specify_cli.merge.push_preflight.check_push_safety")`) for the call-site gate tests, and at `subprocess.run` for unit tests of `check_push_safety` itself.

## Activity Log

- 2026-06-05T10:33:18Z – claude:sonnet:implementer-ivan:implementer – shell_pid=58728 – Assigned agent via action command

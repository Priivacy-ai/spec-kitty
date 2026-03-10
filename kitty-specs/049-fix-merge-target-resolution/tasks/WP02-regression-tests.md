---
work_package_id: WP02
title: Regression Tests & Verification
lane: "done"
dependencies: [WP01]
base_branch: 049-fix-merge-target-resolution-WP01
base_commit: 05d85579ce21ededad3645e673c8cf1da30b4f3e
created_at: '2026-03-10T11:55:39.145856+00:00'
subtasks:
- T004
- T005
phase: Phase 2 - Verification
assignee: ''
agent: claude-opus
shell_pid: '2513'
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-03-10T11:44:58Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
---

# Work Package Prompt: WP02 – Regression Tests & Verification

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

Depends on WP01 — branches from WP01's branch.

---

## Objectives & Success Criteria

Create a regression test suite that proves the merge target resolution fix works correctly across all acceptance scenarios. After this WP:

1. All 7 test cases pass (NFR-002: 4+ test cases required, we deliver 7)
2. SC-001 verified: `--dry-run` returns correct `target_branch` from `meta.json`
3. SC-002 verified: No regression in no-feature path
4. SC-003 verified: Template consistency (checked by reading merge.md)
5. SC-004 verified: All scenarios covered (2.x, main, missing meta, override, nonexistent, no-feature, malformed)

## Context & Constraints

- **Spec**: `kitty-specs/049-fix-merge-target-resolution/spec.md`
- **Plan**: `kitty-specs/049-fix-merge-target-resolution/plan.md`
- **WP01 delivers**: Fixed `merge.py` with target resolution from `meta.json` + branch validation + aligned `merge.md` template
- **Test strategy**: Unit tests with `tmp_path` fixtures and mocked git commands
- **Test location**: `tests/specify_cli/cli/commands/test_merge_target_resolution.py`

### Reference: The fixed resolution logic (from WP01)

After WP01, `merge.py` lines 721-724 will look like:

```python
if target_branch is None:
    if feature:
        from specify_cli.core.feature_detection import get_feature_target_branch
        target_branch = get_feature_target_branch(repo_root, feature)
    else:
        from specify_cli.core.git_ops import resolve_primary_branch
        target_branch = resolve_primary_branch(repo_root)
```

### Reference: `get_feature_target_branch()` behavior

- Reads `kitty-specs/<slug>/meta.json`
- Returns `meta["target_branch"]` if present
- Falls back to `resolve_primary_branch()` on missing/malformed meta.json
- Located in `src/specify_cli/core/feature_detection.py` lines 645-696

### Reference: Existing test patterns in the codebase

Before writing tests, check these files for patterns used in the project:
- `tests/specify_cli/cli/commands/` — existing command tests
- Look for how other tests mock `subprocess.run`, `run_command`, or `resolve_primary_branch`
- Check if there's a test helper for creating mock `kitty-specs/` structures

---

## Subtasks & Detailed Guidance

### Subtask T004 – Create regression test file with 7 test cases

**Purpose**: Prove all acceptance scenarios from the spec pass. Each test exercises one specific code path in the target resolution logic.

**Steps**:

1. Create `tests/specify_cli/cli/commands/test_merge_target_resolution.py`

2. Set up common fixtures:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def feature_dir(tmp_path):
    """Create a minimal kitty-specs feature directory."""
    feature_slug = "049-fix-merge-target-resolution"
    spec_dir = tmp_path / "kitty-specs" / feature_slug
    spec_dir.mkdir(parents=True)
    return spec_dir, feature_slug


def write_meta_json(feature_dir: Path, target_branch: str):
    """Write a meta.json with the given target_branch."""
    meta = {
        "feature_number": "049",
        "slug": "049-fix-merge-target-resolution",
        "target_branch": target_branch,
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
```

3. Implement each test case:

**Test 1: Feature targets 2.x** (Acceptance Scenario 1.1)
```python
def test_feature_targeting_2x_resolves_to_2x(feature_dir):
    """When meta.json says target_branch: '2.x', merge resolves to '2.x'."""
    spec_dir, slug = feature_dir
    write_meta_json(spec_dir, "2.x")
    # Mock repo_root to point to tmp_path
    # Call the resolution logic
    # Assert target_branch == "2.x"
```

- Setup: meta.json with `target_branch: "2.x"`, feature slug provided
- Mock: `_get_main_repo_root` to return `tmp_path`, `resolve_primary_branch` to return `"main"`
- Assert: resolved target is `"2.x"`, NOT `"main"`

**Test 2: Feature targets main** (Acceptance Scenario 1.2)
- Setup: meta.json with `target_branch: "main"`, feature slug provided
- Assert: resolved target is `"main"`

**Test 3: Missing meta.json** (Acceptance Scenario 1.4, edge case 1)
- Setup: No meta.json file created, feature slug provided
- Mock: `resolve_primary_branch` returns `"main"`
- Assert: resolved target is `"main"` (fallback)

**Test 4: Explicit --target overrides meta.json** (Acceptance Scenario 1.3)
- Setup: meta.json with `target_branch: "2.x"`, feature slug + explicit `target_branch="main"` provided
- Assert: resolved target is `"main"` (explicit wins)
- Note: This tests that the `if target_branch is None:` guard works — when `--target` is provided, the resolution block is skipped entirely

**Test 5: Nonexistent target branch** (Edge case 4, FR-006)
- Setup: meta.json with `target_branch: "nonexistent"`, feature slug provided
- Mock: `git rev-parse --verify refs/heads/nonexistent` returns non-zero, `refs/remotes/origin/nonexistent` returns non-zero
- Assert: Command exits with error, error message contains `"nonexistent"` and `"meta.json"`

**Test 6: No --feature flag** (User Story 3, FR-004)
- Setup: No feature slug provided
- Mock: `resolve_primary_branch` returns `"main"`
- Assert: resolved target is `"main"` from `resolve_primary_branch()`, NOT from any meta.json lookup

**Test 7: Malformed meta.json** (Edge case 2)
- Setup: Write invalid JSON to meta.json, feature slug provided
- Mock: `resolve_primary_branch` returns `"main"`
- Assert: resolved target is `"main"` (fallback), no crash

4. **Testing approach**: There are two valid strategies. Choose based on what works best with the existing test patterns:

   **Option A: Test the resolution logic directly** — extract or call `get_feature_target_branch()` and the merge resolution code path in isolation.

   **Option B: Test via CLI invocation** — use `typer.testing.CliRunner` to invoke the `merge` command with `--dry-run --json` and parse the JSON output. This is more of an integration test but catches more issues.

   Check existing tests in `tests/specify_cli/cli/commands/` to see which pattern is used. Match the existing style.

**Files**:
- `tests/specify_cli/cli/commands/test_merge_target_resolution.py` (new file)

**Validation**:
- [ ] All 7 tests pass with `python -m pytest tests/specify_cli/cli/commands/test_merge_target_resolution.py -v`
- [ ] Tests cover all 4 acceptance scenarios from User Story 1
- [ ] Tests cover the backward compatibility scenario (User Story 3)
- [ ] Tests cover all 4 edge cases from the spec
- [ ] No existing tests broken (run `python -m pytest tests/specify_cli/cli/commands/ -v --timeout=30`)

**Notes**:
- When mocking `get_feature_target_branch`, patch at the consuming module's namespace: `specify_cli.cli.commands.merge.get_feature_target_branch` (NOT `specify_cli.core.feature_detection.get_feature_target_branch`)
- For the import to exist in merge.py's namespace, the code uses a local import inside the `if` block. You may need to mock it differently — check how the import is structured in the fixed code.

---

### Subtask T005 – Run tests and verify success criteria

**Purpose**: Confirm all success criteria pass after WP01 fix + WP02 tests are in place.

**Steps**:

1. Run the new regression tests:
```bash
python -m pytest tests/specify_cli/cli/commands/test_merge_target_resolution.py -v
```

2. Run the broader command test suite to check for regressions:
```bash
python -m pytest tests/specify_cli/cli/commands/ -v --timeout=60
```

3. Verify SC-001: Check that `get_feature_target_branch()` is called when `--feature` is provided (confirmed by test cases 1, 2)

4. Verify SC-002: Check that `resolve_primary_branch()` is called when `--feature` is NOT provided (confirmed by test case 6)

5. Verify SC-003: Read the updated `merge.md` template:
```bash
grep -c "agent feature merge" src/specify_cli/missions/software-dev/command-templates/merge.md
```
Expected: 0 matches

6. Verify SC-004: All 7 test cases pass (confirmed by step 1)

**Files**:
- No new files — verification only

**Validation**:
- [ ] All 7 regression tests pass
- [ ] No regressions in existing command tests
- [ ] SC-001 through SC-004 all verified
- [ ] `merge.md` has zero occurrences of `agent feature merge`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Mocking complexity for local imports | Check how WP01 structured the imports; mock at consuming namespace |
| Test isolation issues (tmp_path cleanup) | Each test creates its own fixture; no shared state |
| Flaky subprocess mocks | Use deterministic return values; avoid real git operations |

## Review Guidance

Reviewers should verify:
1. **Coverage**: All 7 test cases match the spec's acceptance scenarios and edge cases
2. **Isolation**: Each test is independent (no shared state, no order dependency)
3. **Mocking correctness**: Mocks target the right namespace (consuming module, not source)
4. **No false positives**: Tests actually exercise the resolution logic, not just pass trivially
5. **Regressions**: Existing tests still pass after the changes

## Activity Log

- 2026-03-10T11:44:58Z – system – lane=planned – Prompt created.
- 2026-03-10T11:55:39Z – claude-opus – shell_pid=98349 – lane=doing – Assigned agent via workflow command
- 2026-03-10T11:59:10Z – claude-opus – shell_pid=98349 – lane=for_review – Ready for review: 8 regression tests (all pass). Covers FR-001 through FR-006, all acceptance scenarios, edge cases, and template consistency.
- 2026-03-10T12:03:06Z – claude-opus – shell_pid=2513 – lane=doing – Started review via workflow command
- 2026-03-10T12:04:48Z – claude-opus – shell_pid=2513 – lane=done – Review passed: All 8 regression tests pass, 190 broader command tests pass with no regressions. FR-001 through FR-006 covered. | Done override: Review approval - branch will be merged to 2.x via spec-kitty merge after all WPs are approved

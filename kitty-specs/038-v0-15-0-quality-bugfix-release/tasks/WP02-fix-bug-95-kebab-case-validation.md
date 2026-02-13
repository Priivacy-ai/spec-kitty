---
work_package_id: WP02
title: Fix Bug
lane: "done"
dependencies: []
base_branch: main
base_commit: 12d8126acbf7c4f1b5888b071a665c65dadc7e7f
created_at: '2026-02-11T15:22:39.642003+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Bug Fixes
assignee: ''
agent: "codex"
shell_pid: "6635"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-11T14:45:00Z'
  lane: planned
  agent: system
  action: Tasks generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Fix Bug #95 - Kebab-Case Validation

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Feature slug validation prevents invalid characters (spaces, underscores, uppercase)
- Clear error message shows valid examples when validation fails
- Regex pattern `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` enforced
- 8 tests written and passing (4 test cases, integration test)
- Fix committed atomically with all tests

**Implementation command**: `spec-kitty implement WP02`

## Context & Constraints

- **Spec**: User Story 1 (FR-001: Input Validation)
- **Plan**: Bug fix order #1 (foundation fix, prevents bad data)
- **GitHub Issue**: #95 reported by @MRiabov
- **Risk Level**: LOW
- **Repository**: spec-kitty main branch at `/Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty`
- **Files to Modify**:
  - `src/specify_cli/cli/commands/agent/feature.py` (lines 224-288)
  - `tests/specify_cli/cli/commands/test_feature_slug_validation.py` (new file)

---

## Test-First Discipline

**CRITICAL**: Write ALL tests FIRST (they must fail), then implement fix, then verify tests pass.

**Test cycle**:
1. Write test → Run → ❌ RED (proves bug exists)
2. Implement fix
3. Run test → ✅ GREEN (proves fix works)
4. Run full suite → ✅ ALL GREEN
5. Commit atomically

---

## Subtask Breakdown

### Subtask T005: Write Test for Invalid Slug with Spaces

**Purpose**: Prove that feature slugs with spaces are currently accepted (bug exists) and should be rejected after fix.

**Steps**:
1. Create test file: `tests/specify_cli/cli/commands/test_feature_slug_validation.py`

2. Write test:
   ```python
   import pytest
   from typer.testing import CliRunner
   from specify_cli.cli.main import app

   runner = CliRunner()

   def test_feature_slug_with_spaces_rejected():
       """Feature slugs with spaces should be rejected."""
       result = runner.invoke(
           app,
           ["agent", "feature", "create-feature", "Invalid Feature Name", "--json"]
       )

       # Should fail with validation error
       assert result.exit_code != 0, "Should reject slug with spaces"

       # Check error message contains helpful guidance
       output = result.stdout
       assert "kebab-case" in output.lower(), "Error should mention kebab-case requirement"
       assert "examples:" in output.lower() or "example" in output.lower(), "Should show examples"
   ```

3. Run test:
   ```bash
   pytest tests/specify_cli/cli/commands/test_feature_slug_validation.py::test_feature_slug_with_spaces_rejected -v
   ```

4. **Expected**: ❌ FAIL (bug exists - spaces are currently accepted)

**Validation**:
- [ ] Test file created
- [ ] Test runs and fails (proves bug exists)
- [ ] Failure message clear

**Time Estimate**: 15 minutes

---

### Subtask T006: Write Test for Invalid Slug with Underscores

**Purpose**: Verify underscores are rejected (kebab-case uses hyphens, not underscores).

**Steps**:
1. Add to test file from T005:
   ```python
   def test_feature_slug_with_underscores_rejected():
       """Feature slugs with underscores should be rejected."""
       result = runner.invoke(
           app,
           ["agent", "feature", "create-feature", "user_authentication", "--json"]
       )

       assert result.exit_code != 0, "Should reject slug with underscores"
       assert "kebab-case" in result.stdout.lower()
   ```

2. Run test: `pytest tests/specify_cli/cli/commands/test_feature_slug_validation.py::test_feature_slug_with_underscores_rejected -v`

3. **Expected**: ❌ FAIL

**Validation**:
- [ ] Test added
- [ ] Test fails (proves bug)

**Time Estimate**: 5 minutes

---

### Subtask T007: Write Test for Invalid Slug Starting with Number

**Purpose**: Verify slugs must start with letter (kebab-case convention).

**Steps**:
1. Add test:
   ```python
   def test_feature_slug_starting_with_number_rejected():
       """Feature slugs must start with a letter."""
       result = runner.invoke(
           app,
           ["agent", "feature", "create-feature", "123-test-feature", "--json"]
       )

       assert result.exit_code != 0, "Should reject slug starting with number"
       assert "kebab-case" in result.stdout.lower()
   ```

2. Run test, expect ❌ FAIL

**Validation**:
- [ ] Test added and failing

**Time Estimate**: 5 minutes

---

### Subtask T008: Write Test for Uppercase in Slug

**Purpose**: Verify uppercase letters are rejected (kebab-case is lowercase only).

**Steps**:
1. Add test:
   ```python
   def test_feature_slug_with_uppercase_rejected():
       """Feature slugs must be lowercase only."""
       result = runner.invoke(
           app,
           ["agent", "feature", "create-feature", "UserAuth", "--json"]
       )

       assert result.exit_code != 0, "Should reject slug with uppercase"
       assert "lowercase" in result.stdout.lower()
   ```

2. Also add test for valid slugs:
   ```python
   def test_valid_kebab_case_slugs_accepted():
       """Valid kebab-case slugs should be accepted."""
       valid_slugs = [
           "user-auth",
           "fix-bug-123",
           "new-dashboard",
           "a",
           "test-feature-2"
       ]

       for slug in valid_slugs:
           result = runner.invoke(
               app,
               ["agent", "feature", "create-feature", slug, "--json"]
           )
           # Note: Will actually create features - run in temp dir or clean up
           assert result.exit_code == 0, f"Valid slug '{slug}' should be accepted"
   ```

3. Run all tests, expect ❌ FAIL on invalid, mixed results on valid (bug exists)

**Validation**:
- [ ] All 4 test cases written
- [ ] Tests demonstrate bug (invalid slugs currently accepted)

**Time Estimate**: 10 minutes

---

### Subtask T009: Add Regex Validation to feature.py

**Purpose**: Implement kebab-case validation before directory creation.

**Steps**:
1. Open `src/specify_cli/cli/commands/agent/feature.py`

2. Find the `create_feature` function (around line 224-288)

3. Add validation immediately after feature_slug parameter capture (before line 257 where repo_root is determined):
   ```python
   import re  # Add to imports at top of file

   # ... in create_feature function ...

   # Validate kebab-case format (add after line 226)
   KEBAB_CASE_PATTERN = r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$'
   if not re.match(KEBAB_CASE_PATTERN, feature_slug):
       error_msg = (
           f"Invalid feature slug '{feature_slug}'. "
           "Must be kebab-case (lowercase letters, numbers, hyphens only). "
           "\n\nValid examples:"
           "\n  - user-auth"
           "\n  - fix-bug-123"
           "\n  - new-dashboard"
           "\n\nInvalid examples:"
           "\n  - User-Auth (uppercase)"
           "\n  - user_auth (underscores)"
           "\n  - 123-fix (starts with number)"
       )
       if json_output:
           console.print(json.dumps({"error": error_msg}))
       else:
           console.print(f"[red]Error:[/red] {error_msg}")
       raise typer.Exit(1)

   # Continue with existing logic...
   ```

4. Verify `re` module is imported (should already be, but check)

**Validation**:
- [ ] Validation added before directory creation
- [ ] Regex pattern matches spec: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`
- [ ] Error message is clear and actionable
- [ ] Error shows valid and invalid examples

**Files**:
- `src/specify_cli/cli/commands/agent/feature.py` (~15 lines added)

**Time Estimate**: 15 minutes

---

### Subtask T010: Add Error Message with Examples

**Purpose**: Ensure error message is helpful and actionable (already done in T009).

**Steps**:
1. Verify error message from T009 includes:
   - Clear statement of problem
   - Explanation of kebab-case requirement
   - Valid examples (3+)
   - Invalid examples with explanation (3+)

2. No additional work needed (covered in T009)

**Validation**:
- [ ] Error message is user-friendly
- [ ] Examples are clear and correct
- [ ] Works in both JSON and console output modes

**Time Estimate**: 5 minutes (verification only, implementation in T009)

---

### Subtask T011: Run Tests - Verify All Pass

**Purpose**: Confirm all 4 test cases now pass after fix implementation.

**Steps**:
1. Run all validation tests:
   ```bash
   pytest tests/specify_cli/cli/commands/test_feature_slug_validation.py -v
   ```

2. **Expected output**: All tests ✅ PASS
   - test_feature_slug_with_spaces_rejected: ✅ PASS
   - test_feature_slug_with_underscores_rejected: ✅ PASS
   - test_feature_slug_starting_with_number_rejected: ✅ PASS
   - test_feature_slug_with_uppercase_rejected: ✅ PASS
   - test_valid_kebab_case_slugs_accepted: ✅ PASS

3. Run full test suite to verify no regressions:
   ```bash
   pytest tests/ -v
   ```

4. **Expected**: All ~1733 existing tests + 5 new tests = 1738 total, all ✅ PASS

**Validation**:
- [ ] All new tests pass (green)
- [ ] No test failures introduced
- [ ] No linting errors: `ruff check src/specify_cli/cli/commands/agent/feature.py`

**Time Estimate**: 10 minutes (test execution + verification)

---

### Subtask T012: Commit Fix Atomically (Fix + Tests Together)

**Purpose**: Create single atomic commit containing both fix and all tests for surgical cherry-picking to 2.x.

**Steps**:
1. Stage both fix and test files:
   ```bash
   git add src/specify_cli/cli/commands/agent/feature.py
   git add tests/specify_cli/cli/commands/test_feature_slug_validation.py
   ```

2. Commit with standard format:
   ```bash
   git commit -m "fix: enforce kebab-case validation for feature slugs (fixes #95)

   Feature slugs must now be kebab-case (lowercase letters, numbers, hyphens only)
   before creating directories. Invalid slugs are rejected with clear error message
   showing valid and invalid examples.

   Previously, slugs with spaces, underscores, or uppercase were accepted, causing
   downstream failures in worktree creation and git branch naming.

   Validation pattern: ^[a-z][a-z0-9]*(-[a-z0-9]+)*$

   Tests added:
   - tests/specify_cli/cli/commands/test_feature_slug_validation.py (5 test cases)

   Fixes #95"
   ```

3. Verify commit contains both fix and tests:
   ```bash
   git show HEAD --stat
   ```

4. **Expected**:
   - 2 files changed
   - feature.py: +15 lines
   - test_feature_slug_validation.py: +60 lines (new file)

**Validation**:
- [ ] Atomic commit (fix + tests in one commit)
- [ ] Commit message follows format
- [ ] References #95 in commit message
- [ ] Both files included in commit

**Time Estimate**: 5 minutes

---

## Notes for Implementer

**This is the first bug fix** - sets the pattern for WP03-WP08.

**Test-first discipline is CRITICAL**:
- Tests must fail before fix (proves bug exists)
- Tests must pass after fix (proves fix works)
- Atomic commit enables clean cherry-pick to 2.x

**Common pitfalls**:
- Writing tests after fix (can't prove bug existed)
- Committing fix and tests separately (breaks atomic cherry-pick)
- Vague error messages (users won't understand what to fix)

**Edge cases to consider**:
- Empty slug: Should fail (add test if time permits)
- Very long slug (>100 chars): Should warn or fail
- Special characters (!@#$%): Should fail
- Just hyphens "---": Should fail (no letters/numbers)

## Activity Log

- 2026-02-11T14:31:29Z – claude – lane=for_review – Moved to for_review
- 2026-02-11T15:02:49Z – codex – shell_pid=93817 – lane=doing – Started review via workflow command
- 2026-02-11T15:20:41Z – codex – shell_pid=93817 – lane=planned – Moved to planned
- 2026-02-11T15:27:42Z – codex – shell_pid=1724 – lane=for_review – Ready for review: Kebab-case validation implemented with 5 passing tests. Invalid slugs (spaces, underscores, uppercase, leading numbers) are now rejected with helpful error messages.
- 2026-02-11T15:27:59Z – codex – shell_pid=6635 – lane=doing – Started review via workflow command
- 2026-02-11T15:30:37Z – codex – shell_pid=6635 – lane=done – Review passed: kebab-case validation regex enforced with helpful examples; new slug validation tests and create-feature integration checks passed.

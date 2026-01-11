# WP Prompt Analysis: Test Execution & Path Issues

**Analyzed**: 2026-01-08
**Issue**: Incorrect test execution paths and conceptual confusion about testing new behavior

---

## Critical Issues Found

### Issue 1: Incorrect Test Execution Paths (WP01, WP08)

**Location**: WP01 and WP08 prompts

**Problem**: Prompts instruct `cd /Users/robert/Code/spec-kitty` before running tests.

**Why this is wrong**:
1. Goes back to main repo (old code)
2. Tests would run against 0.10.12 code, not 0.11.0 code we're building
3. Tests are in the worktree where new code lives
4. Absolute paths are fragile (user-specific)

**Found in**:
- `WP01-dependency-graph-utilities-tdd-foundation.md:361`
- `WP08-integration-tests-full-workflow-validation.md:582`

**Should be**:
```bash
# Run from current worktree (no cd needed)
pytest tests/specify_cli/test_dependency_graph.py -v
pytest tests/specify_cli/test_dependency_graph.py --cov=src/specify_cli/core/dependency_graph.py
```

---

## Conceptual Issues

### Issue 2: Integration Tests Must Use tmp_path

**Analysis**: Integration tests (WP08) will test the NEW workspace-per-WP behavior (0.11.0) which doesn't exist yet in the running Spec Kitty installation (0.10.12).

**Solution Already Correct**: WP08 test examples DO use tmp_path fixture ✅
- Line 452-467: `init_test_repo(tmp_path)` - creates clean test environment
- Line 469-486: Uses tmp_path throughout
- No pollution of actual Spec Kitty repo

**Verification**: Checked WP08 T070-T077 test examples - all use tmp_path ✅

---

## Manual Testing Sections Analysis

### WP05: Manual Testing Commands (Lines 689-707)

**Status**: ✅ **GOOD** - Uses generic placeholder

```bash
cd /path/to/test-project  # ← Generic placeholder, not actual path
```

User will replace with their test project path. No hardcoded paths.

---

### WP09: Manual Testing Commands (Lines 510-528)

**Status**: ⚠️ **MINOR ISSUE** - References specific test feature names

```bash
cd .worktrees/011-test-WP01  # ← Specific feature "011-test", could be confusing
```

**Not critical** because:
- It's in manual testing section (user adapts)
- "011-test" is clearly a placeholder example
- No absolute paths

**Could improve**: Use generic `###-feature-WP01` placeholder instead of `011-test-WP01`

---

## Summary of Fixes

### HIGH Priority - ✅ APPLIED

**Fix 1: Removed incorrect cd commands from test execution sections**

Files updated:
1. ✅ `WP01-dependency-graph-utilities-tdd-foundation.md:361` - Fixed
2. ✅ `WP08-integration-tests-full-workflow-validation.md:582` - Fixed

Changed FROM:
```bash
cd /Users/robert/Code/spec-kitty
pytest tests/specify_cli/test_dependency_graph.py -v
```

Changed TO:
```bash
# Run from current worktree (where new code lives)
pytest tests/specify_cli/test_dependency_graph.py -v
```

Added notes explaining tests run in worktree, not main repo.

### LOW Priority (Optional Clarity Improvements)

**Fix 2: Genericize WP09 manual test example**

File: `WP09-review-feedback-warning-system.md:518`

Change FROM:
```bash
cd .worktrees/011-test-WP01
```

Change TO:
```bash
cd .worktrees/###-feature-WP01  # Replace ### with your feature number
```

---

## Validation: What We Got Right

✅ **WP08 integration tests use tmp_path** - Checked all test examples, all use tmp_path fixture
✅ **No hardcoded test project creation** - No one runs `spec-kitty init actual-project` in real repo
✅ **Unit tests isolated** - WP01-WP07 unit tests don't assume repo structure
✅ **Manual test sections use placeholders** - WP05 uses `/path/to/test-project` (generic)

---

## Root Cause Analysis

**Why this happened**: When writing prompts, I initially thought about running tests from the "standard" location (main repo root) without considering:
1. We're IN a worktree (feature 010)
2. New code lives HERE (in worktree), not in main
3. Tests need to run against code in THIS worktree

**The bootstrap paradox**: Building workspace-per-WP using legacy worktree model created mental confusion about where code lives and where tests run.

---

## Fixes Required

### WP01: Lines 359-365

**Current**:
```bash
**Test execution**:
```bash
cd /Users/robert/Code/spec-kitty
pytest tests/specify_cli/test_dependency_graph.py -v
pytest tests/specify_cli/test_dependency_graph.py --cov=src/specify_cli/core/dependency_graph.py
```

**Expected initial state**: All tests FAIL (module doesn't exist yet)
**After T006**: All tests PASS
```

**Fixed**:
```bash
**Test execution**:
```bash
# Run from current worktree (where new code lives)
pytest tests/specify_cli/test_dependency_graph.py -v
pytest tests/specify_cli/test_dependency_graph.py --cov=src/specify_cli/core/dependency_graph.py --cov-report=term-missing
```

**Expected initial state**: All tests FAIL (module doesn't exist yet)
**After T006**: All tests PASS

**Note**: Do NOT cd to main repo - tests must run against code in this worktree.
```

### WP08: Lines 580-584

**Current**:
```bash
**Execution**:
```bash
cd /Users/robert/Code/spec-kitty
pytest tests/specify_cli/test_integration/test_workspace_per_wp_workflow.py -v --tb=short
```
```

**Fixed**:
```bash
**Execution**:
```bash
# Run from current worktree (where new code lives)
pytest tests/specify_cli/test_integration/test_workspace_per_wp_workflow.py -v --tb=short
```

**Note**: Tests run in this worktree. Integration tests create isolated tmp_path environments to test new 0.11.0 behavior.
```

### WP09: Line 518 (Optional)

**Current**:
```bash
cd .worktrees/011-test-WP01 && echo "WP01" > file.txt && git add . && git commit -m "WP01"
```

**Fixed** (optional clarity):
```bash
cd .worktrees/###-test-feature-WP01 && echo "WP01" > file.txt && git add . && git commit -m "WP01"
# Replace ### with your actual feature number
```

---

## Testing Philosophy for This Feature

**Correct approach**:

1. **Unit Tests** (WP01, WP02, WP03, WP09):
   - Run from worktree: `pytest tests/specify_cli/test_dependency_graph.py`
   - Test new code in THIS worktree
   - No cd needed

2. **Integration Tests** (WP04:T030, WP08):
   - Run from worktree: `pytest tests/specify_cli/test_integration/...`
   - Create clean test environments: `init_test_repo(tmp_path)`
   - Test NEW 0.11.0 behavior in isolated tmp directories
   - Never pollute actual Spec Kitty repo

3. **Manual Validation** (WP05, WP06, WP09, WP10):
   - Create throwaway test project: `/tmp/test-workspace-per-wp/`
   - Test NEW commands in that project
   - Don't test on actual Spec Kitty development repo

**The Key Insight**: We're building 0.11.0 code in a 0.10.12 worktree. Tests must validate the NEW code (in worktree), not the OLD code (in main repo).

---

## Recommendation

**Apply High Priority Fixes**:
1. Update WP01 test execution section (remove cd command)
2. Update WP08 test execution section (remove cd command)

**Optional**:
3. Update WP09 manual test examples (use generic placeholders)

**All other prompts are correct** - no other path issues found.

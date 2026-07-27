# Corrections Applied Based on Reviews

**Date**: 2026-01-08
**Feature**: 010-workspace-per-work-package-for-parallel-development

---

## WP01 Review Corrections ✅

### Issue 1: FrontmatterManager Bypass (HIGH)

**Problem**: `parse_wp_dependencies()` bypassed the mandated FrontmatterManager and did custom YAML parsing.

**Impact**: Could parse differently than rest of CLI (BOM handling, closing --- detection, key ordering).

**Fix Applied**:
```python
# BEFORE (custom parsing)
yaml = YAML()
frontmatter = yaml.load(parts[1])

# AFTER (uses FrontmatterManager)
from specify_cli.frontmatter import read_frontmatter
frontmatter, _ = read_frontmatter(wp_file)
```

**Files Changed**:
- `src/specify_cli/core/dependency_graph.py:32-48` - Now uses read_frontmatter()

**Validation**: ✅ All 25 tests still PASS

---

### Issue 2: Filename vs Frontmatter Mismatch (MEDIUM)

**Problem**: `build_dependency_graph()` used filename to derive WP ID without verifying it matches frontmatter `work_package_id`.

**Impact**: Misnamed files or stale frontmatter could corrupt dependency graph silently.

**Fix Applied**:
```python
# BEFORE (trusts filename)
wp_id = extract_wp_id_from_filename(wp_file.name)
graph[wp_id] = dependencies

# AFTER (validates match)
filename_wp_id = extract_wp_id_from_filename(wp_file.name)
frontmatter, _ = read_frontmatter(wp_file)
frontmatter_wp_id = frontmatter.get("work_package_id")

# Verify match, use frontmatter as canonical
if frontmatter_wp_id != filename_wp_id:
    wp_id = frontmatter_wp_id  # Frontmatter is source of truth
```

**Files Changed**:
- `src/specify_cli/core/dependency_graph.py:76-101` - Now validates filename vs frontmatter

**Validation**: ✅ All 25 tests still PASS

---

## WP02 Review Corrections ✅

### Issue 1: Testing Non-Existent Agent Directories (HIGH)

**Problem**: Tests attempted to validate files in `.claude/commands/`, `.gemini/commands/`, etc. which are GITIGNORED and don't exist in repo.

**Impact**: Tests would FAIL immediately - can't test files that don't exist.

**Root Cause**: Misunderstood template architecture:
- ❌ Agent directories are generated at runtime (gitignored)
- ✅ Template sources are committed (`.kittify/missions/software-dev/command-templates/`)

**Fix Applied**:
- Rewrote WP02 to test **template sources** instead of agent directories
- Changed from 48 files (12 agents × 4 templates) to 4 files (template sources)

**Files Changed**:
- `tasks/WP02-migration-tests-tdd-agent-template-coverage.md` - Complete rewrite
- `tasks.md` - Updated WP02 description and subtask count

**Scope Impact**: WP02 subtasks reduced from 8 to 6 (removed T014, T059-T067)

---

### Issue 2: Hardcoded .md Extensions (HIGH)

**Problem**: Tests assumed all agents use `.md` extension, but AGENT_COMMAND_CONFIG shows:
- Gemini/Qwen use `.toml`
- Copilot uses `.prompt.md`
- Others use `.md`

**Impact**: Tests would fail even with correct paths due to wrong extensions.

**Fix Applied**: Testing template sources eliminates this issue (templates are all `.md`, generation handles extensions).

**Files Changed**: Same as Issue 1 (complete WP02 rewrite)

---

## WP07 Corrections ✅

### Issue 1: Scope Reduction (48 files → 4 files)

**Problem**: WP07 had T053-T067 (15 subtasks) updating individual agent directories.

**Fix Applied**:
- Reduced to T053-T056 (4 subtasks) updating template sources
- Template location: `.kittify/missions/software-dev/command-templates/`
- Agent files generated from templates (not directly updated)

**Files Changed**:
- `tasks/WP07-migration-implementation.md` - Complete rewrite (10 subtasks, not 21)
- `tasks.md` - Updated WP07 description

**Scope Impact**: WP07 subtasks reduced from 21 to 10

---

## Test Execution Path Corrections ✅

### Issue: Incorrect cd Commands

**Problem**: WP01 and WP08 prompts included `cd /Users/robert/Code/spec-kitty` before running tests.

**Impact**:
- Would test OLD code in main repo (0.10.12)
- Would NOT test NEW code in worktree (0.11.0)
- Absolute paths are user-specific and fragile

**Fix Applied**:
```bash
# BEFORE
cd /Users/robert/Code/spec-kitty
pytest tests/specify_cli/test_dependency_graph.py

# AFTER
# Run from current worktree (where new code lives)
pytest tests/specify_cli/test_dependency_graph.py
```

**Files Changed**:
- `tasks/WP01-dependency-graph-utilities-tdd-foundation.md:361` - Removed cd, added note
- `tasks/WP08-integration-tests-full-workflow-validation.md:582` - Removed cd, added note

**Rationale**: Tests must run against code in THIS worktree, not main repo

---

## Metrics: Scope Impact

### Original Scope
- **Total Subtasks**: 93
- **WP02**: 8 subtasks
- **WP07**: 21 subtasks (15 parallel agent updates!)
- **Files to Update**: 48 agent directory files

### Corrected Scope
- **Total Subtasks**: 80 (13 subtasks removed)
- **WP02**: 6 subtasks (removed T014, changed focus to template sources)
- **WP07**: 10 subtasks (removed T059-T069, update 4 template sources not 48 files)
- **Files to Update**: 4 template source files

**Scope Reduction**: 14% fewer subtasks, 92% fewer files to update!

---

## Why These Corrections Matter

### Testability

**Before**: Tests would fail on file existence (agent dirs don't exist in repo)
**After**: Tests validate committed template sources (exist in repo, testable in CI)

### Maintainability

**Before**: 48 files to keep in sync (nightmare for future changes)
**After**: 4 template sources (single source of truth, propagates to all agents)

### CI/CD

**Before**: Can't run migration tests in CI (agent dirs not in repo)
**After**: Migration tests run in CI (template sources are committed)

### User Experience

**Before**: Migration would update 48 files (slow, error-prone)
**After**: Migration updates 4 templates, users regenerate agent files (fast, reliable)

---

## Files Modified Summary

### Implementation Files
- ✅ `src/specify_cli/core/dependency_graph.py` - Uses FrontmatterManager, validates filename vs frontmatter

### Test Files
- ✅ `tests/specify_cli/test_dependency_graph.py` - Created (25 tests, all passing)

### WP Prompt Files
- ✅ `tasks/WP01-dependency-graph-utilities-tdd-foundation.md` - Fixed test execution path
- ✅ `tasks/WP02-migration-tests-tdd-agent-template-coverage.md` - Complete rewrite (template sources)
- ✅ `tasks/WP07-migration-implementation.md` - Complete rewrite (4 templates, not 48 files)
- ✅ `tasks/WP08-integration-tests-full-workflow-validation.md` - Fixed test execution path

### Planning Files
- ✅ `tasks.md` - Updated WP02, WP07 descriptions, subtask counts, scope corrections

### Analysis Files
- ✅ `PROMPT_ANALYSIS.md` - Created (documents test execution issues)
- ✅ `CORRECTIONS_APPLIED.md` - This file

---

## Lessons Learned

**L1: Always Verify File Existence**
- Check if files exist in repo before writing tests
- Check .gitignore to understand what's generated vs committed

**L2: Understand Template Architecture**
- Templates are source of truth (committed)
- Agent directories are generated (runtime)
- Update sources, not generated files

**L3: Test Execution Context**
- Tests run in worktree (where new code lives)
- Never cd back to main repo during tests
- Integration tests use tmp_path (isolated environments)

**L4: Single Source of Truth**
- 4 template sources better than 48 agent files
- Propagation via generation, not manual sync

---

## Next Steps

**WP01**: ✅ Complete, in for_review
**WP02**: ⚠️ In "doing" lane, needs implementation with corrected approach
**WP03**: In "doing" lane
**WP06**: In "doing" lane

**Recommendation**: Complete WP02 and WP03 (Wave 2) before proceeding to WP04-WP07 (depend on WP02/WP03).

---

## Validation Checklist

After all corrections:
- [ ] WP01 tests pass (25/25) ✅
- [ ] WP02 tests will validate 4 template sources (not 48 agent files)
- [ ] WP07 will update 4 template sources (not 48 agent files)
- [ ] No absolute paths in test commands
- [ ] No testing of gitignored files
- [ ] All tests run from worktree context

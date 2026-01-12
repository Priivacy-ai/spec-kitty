---
work_package_id: "WP03"
subtasks:
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "Mission Constitution Removal"
phase: "Feature - Track 1 Critical Safety"
lane: "done"
assignee: ""
agent: "claude-sonnet-4-5"
shell_pid: ""
review_status: "approved"
reviewed_by: "claude-sonnet-4-5"
history:
  - timestamp: "2026-01-12T11:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2026-01-12T20:15:00Z"
    lane: "done"
    agent: "claude-sonnet-4-5"
    shell_pid: ""
    action: "Code review approved - constitution_dir removed from mission.py, constitution scanning removed from manifest.py, no mission constitution directories remain. 5/5 tests passed."
---

# Work Package Prompt: WP03 – Mission Constitution Removal

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

**Goal**: Remove mission-specific constitution system entirely from codebase and template structure.

**Success Criteria**:
1. `src/specify_cli/mission.py` no longer has `constitution_dir` property (lines 247-249)
2. `src/specify_cli/manifest.py` no longer scans for constitution files (lines 70-74)
3. `src/specify_cli/missions/*/constitution/` directories deleted (in template sources after WP01 move)
4. All tests updated to remove mission constitution references
5. No code references to "mission.*constitution" remain in codebase
6. Documentation updated to reflect single project-level constitution model

**Acceptance Test**:
```bash
# Verify no constitution_dir references
grep -rn "constitution_dir" src/specify_cli/
# Expected: Empty output (exit code 1)

# Verify no mission constitution directories
find src/specify_cli/missions -type d -name "constitution"
# Expected: Empty output (exit code 1)

# Verify no manifest constitution scanning
grep -A5 -B5 "constitution" src/specify_cli/manifest.py
# Expected: No matches for constitution file scanning

# Run tests
pytest tests/ -k constitution
# Expected: All pass, no failures related to mission constitutions
```

---

## Context & Constraints

**Why This Matters**: Mission-specific constitutions caused confusion about which constitution applied to a project. Users didn't understand if they should use the project-level constitution (`.kittify/memory/constitution.md`) or mission-specific constitution (`.kittify/missions/*/constitution/principles.md`).

**Architectural Decision**: Spec-kitty now uses ONLY project-level constitutions. Each project has ONE constitution at `.kittify/memory/constitution.md`. Missions no longer have their own constitutions.

**Related Documents**:
- Spec: `kitty-specs/011-constitution-packaging-safety-and-redesign/spec.md` (User Story discussion)
- Plan: `kitty-specs/011-constitution-packaging-safety-and-redesign/plan.md` (Constitution System Changes)
- Research: `kitty-specs/011-constitution-packaging-safety-and-redesign/research.md` (Constitution command redesign)
- Data Model: `kitty-specs/011-constitution-packaging-safety-and-redesign/data-model.md` (Entity 3: Constitution Structure)

**Dependencies**:
- **WP01 must complete first**: Template files must be moved to `src/specify_cli/` before we can delete mission constitution directories
- WP02 adds migration to remove constitution directories from user projects (handles runtime cleanup)
- This WP handles code and template cleanup (handles source cleanup)

---

## Subtasks & Detailed Guidance

### Subtask T017 – Remove `constitution_dir` property from `mission.py`

**Purpose**: Remove code that provides access to mission-specific constitution directories.

**File**: `src/specify_cli/mission.py`

**Current Code** (lines 247-249):
```python
@property
def constitution_dir(self) -> Path:
    """Get the constitution directory for this mission."""
    return self.path / "constitution"
```

**Steps**:
1. Read `src/specify_cli/mission.py`
2. Locate the `constitution_dir` property (around line 247)
3. **Delete the entire property** (all 4 lines including decorator and docstring)
4. Search file for any internal usage of `self.constitution_dir`
5. If internal usage exists, remove those references too

**Verification**:
```bash
# After deletion, verify property gone
grep -n "constitution_dir" src/specify_cli/mission.py
# Expected: Empty output

# Check if property was used elsewhere in same file
grep -n "self.constitution_dir" src/specify_cli/mission.py
# Expected: Empty output
```

**Impact Analysis**:
```bash
# Find all code that calls constitution_dir
grep -rn "constitution_dir" src/specify_cli/ --include="*.py"
# Document each usage - will need to update in following subtasks
```

**Expected Usages** (document for fixing):
- `manifest.py`: May use `mission.constitution_dir` for file scanning
- Tests: May reference constitution_dir property
- Other mission-related code: May assume constitution_dir exists

**Notes**:
- This property is part of the public API of the Mission class
- Removing it is a breaking change, but that's intentional
- Any code relying on this property will need refactoring

---

### Subtask T018 – Remove constitution scanning from `manifest.py`

**Purpose**: Remove code that scans for mission-specific constitution files.

**File**: `src/specify_cli/manifest.py`

**Current Code** (lines 70-74):
```python
# Constitution
constitution_dir = self.mission_dir / "constitution"
if constitution_dir.exists():
    for const_file in constitution_dir.glob("*.md"):
        manifest["constitution"].append(str(const_file.relative_to(self.kittify_dir)))
```

**Steps**:
1. Read `src/specify_cli/manifest.py`
2. Locate the `get_expected_files()` method (starts around line 35)
3. Find the "Constitution" section (around lines 70-74)
4. **Delete the entire Constitution section** (5 lines)
5. **Remove** `"constitution": []` from the manifest dict initialization (line 49)
6. Check if `manifest["constitution"]` is used elsewhere in the file

**Before (lines 45-74)**:
```python
manifest = {
    "commands": [],
    "templates": [],
    "scripts": [],
    "constitution": [],  # REMOVE THIS LINE
    "mission_files": []
}

# ... other sections ...

# Constitution  # DELETE THIS ENTIRE SECTION
constitution_dir = self.mission_dir / "constitution"
if constitution_dir.exists():
    for const_file in constitution_dir.glob("*.md"):
        manifest["constitution"].append(str(const_file.relative_to(self.kittify_dir)))
```

**After (lines 45-69)**:
```python
manifest = {
    "commands": [],
    "templates": [],
    "scripts": [],
    # constitution removed - now project-level only
    "mission_files": []
}

# ... other sections ...

# Constitution section removed
# Scripts referenced in commands...
```

**Verification**:
```bash
# Verify no constitution references remain
grep -n "constitution" src/specify_cli/manifest.py
# Expected: No matches for constitution scanning logic

# Verify manifest dict has no constitution key
grep -A10 "manifest = {" src/specify_cli/manifest.py
# Expected: No "constitution" key in dict
```

**Impact on Return Value**:
- `get_expected_files()` now returns manifest with 4 keys instead of 5
- `check_files()` method may reference `expected["constitution"]` - verify and remove
- Any code iterating over manifest keys needs review

**Additional Cleanup in Same File**:
```python
# In check_files() method (around line 143)
for category, files in expected.items():
    # This will now skip "constitution" category automatically
    # No changes needed unless explicit constitution handling exists
```

---

### Subtask T019 – Delete `missions/*/constitution/` directories

**Purpose**: Remove constitution directories from template sources (now in `src/specify_cli/missions/` after WP01).

**Prerequisite**: WP01 must be complete (templates moved to `src/specify_cli/`)

**Directories to Delete**:
```
src/specify_cli/missions/software-dev/constitution/
src/specify_cli/missions/research/constitution/
```

**Steps**:
1. Verify WP01 complete (templates in `src/specify_cli/`)
2. Check if constitution directories exist:
   ```bash
   find src/specify_cli/missions -type d -name "constitution"
   ```
3. For each constitution directory found:
   - List contents: `ls -la src/specify_cli/missions/*/constitution/`
   - **Delete entire directory**:
     ```bash
     rm -rf src/specify_cli/missions/software-dev/constitution
     rm -rf src/specify_cli/missions/research/constitution
     ```
4. Verify deletion:
   ```bash
   find src/specify_cli/missions -type d -name "constitution"
   # Expected: Empty output
   ```

**Files Being Removed** (document for context):
```
src/specify_cli/missions/software-dev/constitution/
└── principles.md         # Template with placeholder principles

src/specify_cli/missions/research/constitution/
└── (similar structure if exists)
```

**Content to Preserve** (if valuable):
- If `principles.md` contains useful example content, consider:
  - Moving useful examples to project-level constitution template
  - Documenting example principles in research notes
  - Saving content before deletion for reference

**Verification**:
```bash
# 1. Verify directories gone
ls -la src/specify_cli/missions/software-dev/
# Expected: No "constitution/" subdirectory

ls -la src/specify_cli/missions/research/
# Expected: No "constitution/" subdirectory

# 2. Verify mission structure still valid
ls -la src/specify_cli/missions/software-dev/
# Expected: mission.yaml, templates/, command-templates/ (no constitution/)

# 3. Verify git tracks deletion
git status
# Expected: "deleted: src/specify_cli/missions/.../constitution/..."
```

**Git Commit Message** (for this subtask):
```
refactor: Remove mission-specific constitution directories

Remove constitution/ subdirectories from all missions. Spec-kitty
now uses a single project-level constitution at .kittify/memory/constitution.md
instead of per-mission constitutions.

This simplifies the constitution model and eliminates confusion about
which constitution applies to a project.

Part of feature 011 (Constitution Packaging Safety and Redesign)
```

---

### Subtask T020 – Update tests to remove mission constitution references

**Purpose**: Fix tests that expect mission constitution directories or `constitution_dir` property.

**Files to Update**: `tests/` directory (specific files TBD after grep)

**Investigation Steps**:
1. **Find test files referencing constitutions**:
   ```bash
   grep -rn "constitution" tests/ --include="*.py"
   ```

2. **Categorize findings**:
   - Tests checking `mission.constitution_dir` property
   - Tests scanning for constitution files in missions
   - Tests validating manifest includes constitutions
   - Tests for constitution-related features (may be OK)

3. **Expected Test Files** (from spec):
   - `tests/test_plan_validation.py`: May reference constitutions in validation
   - `tests/specify_cli/test_core/test_worktree.py`: May reference constitution setup
   - `tests/integration/test_feature_commands.py`: May test constitution commands
   - Mission-related tests: May assume constitution_dir exists

**Update Patterns**:

**Pattern 1: Remove constitution_dir property tests**:
```python
# BEFORE
def test_mission_constitution_dir():
    mission = Mission(mission_path)
    const_dir = mission.constitution_dir
    assert const_dir.exists()
    assert (const_dir / "principles.md").exists()

# AFTER (delete entire test)
# This test is no longer valid - constitution_dir property removed
```

**Pattern 2: Update manifest tests**:
```python
# BEFORE
def test_manifest_includes_constitutions():
    manifest = file_manifest.get_expected_files()
    assert "constitution" in manifest
    assert len(manifest["constitution"]) > 0

# AFTER
def test_manifest_excludes_constitutions():
    """Constitutions are now project-level only, not per-mission."""
    manifest = file_manifest.get_expected_files()
    assert "constitution" not in manifest
    # Or if key exists but empty:
    # assert len(manifest.get("constitution", [])) == 0
```

**Pattern 3: Update feature tests to use project-level constitution**:
```python
# BEFORE
def test_plan_uses_mission_constitution():
    mission = get_active_mission()
    const_file = mission.constitution_dir / "principles.md"
    # ... test uses mission constitution ...

# AFTER
def test_plan_uses_project_constitution():
    """Plans now use project-level constitution at .kittify/memory/constitution.md"""
    const_file = project_root / ".kittify" / "memory" / "constitution.md"
    # ... test uses project constitution ...
```

**Pattern 4: Remove mission setup that creates constitutions**:
```python
# BEFORE (in test fixtures)
@pytest.fixture
def mission_with_constitution(tmp_path):
    mission_path = tmp_path / "missions" / "software-dev"
    mission_path.mkdir(parents=True)
    const_dir = mission_path / "constitution"
    const_dir.mkdir()
    (const_dir / "principles.md").write_text("# Test")
    return Mission(mission_path)

# AFTER
@pytest.fixture
def mission_without_constitution(tmp_path):
    """Missions no longer have constitution subdirectories."""
    mission_path = tmp_path / "missions" / "software-dev"
    mission_path.mkdir(parents=True)
    # No constitution directory created
    (mission_path / "mission.yaml").write_text("name: Test\n...")
    return Mission(mission_path)
```

**Steps for Each Test File**:
1. Read test file
2. Identify constitution-related tests
3. Determine if test should be:
   - **Deleted** (tests removed feature)
   - **Updated** (tests valid feature but implementation changed)
   - **Left alone** (tests project-level constitutions, not mission-level)
4. Make changes
5. Run tests: `pytest tests/path/to/test_file.py -v`
6. Fix any failures

**Verification**:
```bash
# Run all tests
pytest tests/ -v

# Run constitution-related tests specifically
pytest tests/ -k constitution -v

# Verify no tests reference constitution_dir
grep -rn "constitution_dir" tests/
# Expected: Empty output
```

---

### Subtask T021 – Grep and cleanup remaining references

**Purpose**: Find and remove ALL remaining references to mission-specific constitutions in codebase.

**Comprehensive Grep Commands**:
```bash
# 1. Find "mission.*constitution" pattern
grep -rn "mission.*constitution" src/specify_cli/ --include="*.py"

# 2. Find "constitution" in mission context
grep -rn "\.constitution" src/specify_cli/ --include="*.py" | grep -i mission

# 3. Find constitution_dir references
grep -rn "constitution_dir" src/ tests/ --include="*.py"

# 4. Find constitution in mission.py specifically
grep -n "constitution" src/specify_cli/mission.py

# 5. Find constitution in manifest.py specifically
grep -n "constitution" src/specify_cli/manifest.py

# 6. Find references in documentation
grep -rn "mission.*constitution" docs/ README.md CONTRIBUTING.md

# 7. Find in examples
grep -rn "constitution" examples/
```

**Expected Findings**:

**Category 1: Code References** (should be removed/updated):
- `mission.constitution_dir` calls
- `manifest["constitution"]` references
- Mission loading that expects constitution subdirectory
- Worktree setup that symlinks mission constitutions

**Category 2: Documentation References** (should be updated):
- README.md: May mention mission constitutions
- CONTRIBUTING.md: May document constitution system
- docs/*.md: May explain constitution structure
- examples/*.md: May show mission constitution usage

**Category 3: Comments and Docstrings** (should be updated):
```python
# BEFORE
"""
Each mission can have its own constitution in missions/<name>/constitution/
"""

# AFTER
"""
Projects use a single constitution at .kittify/memory/constitution.md
"""
```

**Update Checklist**:
- [ ] All `constitution_dir` references removed
- [ ] All `manifest["constitution"]` references removed
- [ ] All mission constitution directory references removed
- [ ] All worktree constitution symlink code updated
- [ ] All documentation mentioning mission constitutions updated
- [ ] All examples mentioning mission constitutions updated
- [ ] All comments mentioning mission constitutions updated

**Files Likely Needing Updates** (verify with grep):
1. `src/specify_cli/core/worktree.py`: May symlink mission constitutions
2. `src/specify_cli/plan_validation.py`: May reference mission constitutions
3. `docs/` files: Architecture documentation
4. `examples/` files: Usage examples
5. `CLAUDE.md`: May mention mission constitutions

**Worktree Constitution Handling**:
```python
# In src/specify_cli/core/worktree.py (around line 269)

# BEFORE
# Setup shared constitution and AGENTS.md via symlink (or copy on Windows)
# Worktrees share mission constitutions from main repo
constitution_src = main_kittify / "missions" / mission_name / "constitution"
if constitution_src.exists():
    constitution_dest = worktree_kittify / "missions" / mission_name / "constitution"
    # ... symlink logic ...

# AFTER
# Remove mission constitution symlink logic
# Worktrees now only share project-level constitution at .kittify/memory/
# Mission constitutions no longer exist
```

**Documentation Updates**:
```markdown
# BEFORE (in README.md or docs/)
## Mission Constitutions

Each mission can define its own constitution in `.kittify/missions/<mission-name>/constitution/`.
The constitution captures mission-specific principles and governance rules.

# AFTER
## Project Constitution

Each project has a single constitution at `.kittify/memory/constitution.md`.
The constitution captures project-wide principles and governance rules that apply
to all features and missions.
```

**Verification**:
```bash
# Final verification - should return no matches
grep -rn "mission.*constitution\|constitution.*mission" \
  src/ tests/ docs/ examples/ \
  README.md CONTRIBUTING.md CLAUDE.md \
  --include="*.py" --include="*.md"

# If any matches remain, document them and decide:
# - False positive (e.g., "mission" and "constitution" in unrelated context)
# - Needs update (e.g., outdated comment or doc)
# - Intentional (e.g., migration that removes mission constitutions)
```

---

## Test Strategy

**Unit Tests** (minimal - mostly cleanup):
- Test that Mission class no longer has `constitution_dir` property
- Test that manifest no longer includes constitution category
- Test that missions directory structure valid without constitution/

**Integration Tests** (defer to WP06):
- Test that projects work without mission constitutions
- Test that plan command doesn't look for mission constitutions
- Test that worktrees don't try to symlink mission constitutions

**Manual Verification**:
```bash
# 1. Start spec-kitty project
spec-kitty init
# Verify: No mission constitution directories created

# 2. Run plan command
cd .worktrees/some-feature/
spec-kitty agent feature setup-plan --json
# Verify: No errors about missing mission constitutions

# 3. Check Mission object
python3 << EOF
from specify_cli.mission import get_active_mission
mission = get_active_mission()
assert not hasattr(mission, 'constitution_dir')
print("✓ constitution_dir property removed")
EOF
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation | Covered By |
|------|--------|------------|------------|
| Breaking code that relies on constitution_dir | High | Comprehensive grep to find all usages | T021 |
| Tests failing after property removal | Medium | Update all tests referencing constitution_dir | T020 |
| Documentation out of sync | Low | Update all docs mentioning mission constitutions | T021 |
| Users confused about where constitution lives | Medium | Clear documentation + migration warning (WP02) | T021 + WP02 |
| Worktree setup breaks | Medium | Update worktree constitution handling | T021 |

---

## Definition of Done Checklist

- [ ] All subtasks T017-T021 completed
- [ ] `constitution_dir` property removed from `mission.py`
- [ ] Constitution scanning removed from `manifest.py`
- [ ] All `missions/*/constitution/` directories deleted
- [ ] All tests updated and passing
- [ ] No grep matches for "mission.*constitution" in code
- [ ] Documentation updated to reflect single constitution model
- [ ] Examples updated to use project-level constitution
- [ ] Git commit created with clear explanation
- [ ] Code review requested from maintainer

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. **Property removed**: Verify `constitution_dir` no longer exists in Mission class
2. **Manifest cleaned**: Verify manifest no longer scans for constitutions
3. **Directories deleted**: Verify no constitution subdirectories in missions
4. **Tests pass**: All tests pass after updates
5. **No references remain**: Grep verification shows no mission constitution references

**Red Flags for Reviewer**:
- Any `constitution_dir` references remain in code
- Tests still expect mission constitution directories
- Manifest still has "constitution" category
- Documentation still mentions mission-specific constitutions

**Testing Checklist for Reviewer**:
```bash
# 1. Verify property removed
python3 -c "from specify_cli.mission import Mission; assert not hasattr(Mission, 'constitution_dir')"

# 2. Verify directories deleted
find src/specify_cli/missions -name "constitution" -type d
# Expected: Empty

# 3. Run tests
pytest tests/ -v

# 4. Verify no references
./scripts/verify_no_mission_constitutions.sh
```

**Context for Reviewer**:
- This is an architectural simplification - mission constitutions caused confusion
- Single project-level constitution is simpler and clearer for users
- WP02 handles runtime cleanup (removing constitution dirs from user projects)
- This WP handles source cleanup (removing from codebase and templates)

---

## Activity Log

- 2026-01-12T11:30:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter
2. **Use CLI**: `spec-kitty agent tasks move-task WP03 --to <lane> --note "message"`

The CLI command also updates the activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-01-12T10:48:42Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-12T10:50:38Z – unknown – lane=for_review – Ready for review

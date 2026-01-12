---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Template Relocation & Packaging"
phase: "Foundational - Track 1 Critical Safety"
lane: "doing"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-12T11:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Template Relocation & Packaging

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

**Goal**: Move all template sources from `.kittify/` to `src/specify_cli/` to achieve clean separation between template source code (packaged) and project instances (runtime).

**Success Criteria**:
1. All template files moved from `.kittify/templates/` → `src/specify_cli/templates/`
2. All mission files moved from `.kittify/missions/` → `src/specify_cli/missions/`
3. All script files moved from `.kittify/scripts/` → `src/specify_cli/scripts/` (if they exist)
4. `src/specify_cli/template/manager.py` loads templates from `src/specify_cli/*` instead of `.kittify/*`
5. `pyproject.toml` no longer force-includes `.kittify/*` paths (lines 86-89, 94-97, 109-110 removed)
6. Building wheel produces ZERO `.kittify/` or `memory/constitution.md` entries
7. `spec-kitty init` works from installed package (not just editable install)
8. Spec-kitty's own `.kittify/` directory still works for dogfooding

**Acceptance Test**:
```bash
# Build package
python -m build

# Inspect wheel contents
unzip -l dist/spec_kitty_cli-*.whl | grep -E '(\.kittify|memory/constitution\.md)'

# Expected: Zero matches for .kittify/, only specify_cli/templates/ and specify_cli/missions/
# Exit code: 1 (no matches found)
```

---

## Context & Constraints

**Why This Matters**: This is the ROOT CAUSE fix for packaging contamination. Currently, any filled `.kittify/memory/constitution.md` in the spec-kitty repo gets packaged and distributed to all PyPI users, overwriting their project-specific values.

**Related Documents**:
- Spec: `kitty-specs/011-constitution-packaging-safety-and-redesign/spec.md` (FR-001 through FR-006, User Story 1)
- Plan: `kitty-specs/011-constitution-packaging-safety-and-redesign/plan.md` (Risk Mitigation section, Project Structure)
- Research: `kitty-specs/011-constitution-packaging-safety-and-redesign/research.md` (Research Area 1: Template Relocation Strategy)
- Data Model: `kitty-specs/011-constitution-packaging-safety-and-redesign/data-model.md` (Entity 1: Template File Structure)

**Architectural Decision**: Template sources belong in `src/` (packaged code), not `.kittify/` (project instance). This enables safe dogfooding - spec-kitty developers can run `spec-kitty init` and fill in their own constitution without risk of packaging it.

**Critical Constraint**: This work package MUST complete before WP05 (Constitution Command Redesign), as WP05 needs to know the new template location.

**Dependencies**: None (can start immediately)

---

## Subtasks & Detailed Guidance

### Subtask T001 – Audit codebase for `.kittify/` references

**Purpose**: Identify all hardcoded `.kittify/` paths that will break after relocation.

**Steps**:
1. Grep entire Python codebase for `.kittify/` references:
   ```bash
   grep -rn "\.kittify/" src/specify_cli/ --include="*.py"
   ```
2. Document each reference with file path and line number
3. Categorize references:
   - **Template loading** (will need update to use package resources)
   - **Project instance paths** (OK - these reference user's `.kittify/`, not templates)
   - **Tests** (may need update if they reference template locations)
4. Create audit report: list of files to update in subsequent subtasks

**Files to Check**:
- `src/specify_cli/template/manager.py` (CRITICAL - main template loader)
- `src/specify_cli/mission.py` (may reference mission locations)
- `src/specify_cli/upgrade/migrations/*.py` (migrations that copy templates)
- `tests/**/*.py` (test fixtures may reference template paths)

**Expected Findings**:
- `template/manager.py`: `copy_specify_base_from_local()` function (lines ~59-122)
- Migration files: `m_0_7_3_update_scripts.py`, `m_0_10_6_workflow_simplification.py`
- Test files may have hardcoded template paths

**Output**: Audit report documenting all `.kittify/` references and update plan

---

### Subtask T002 – Move `.kittify/templates/` → `src/specify_cli/templates/`

**Purpose**: Relocate all template files to package location.

**Steps**:
1. Verify source exists: `ls -la .kittify/templates/`
2. Create destination: `mkdir -p src/specify_cli/templates/`
3. Move entire directory:
   ```bash
   mv .kittify/templates/* src/specify_cli/templates/
   ```
4. Verify structure preserved:
   ```bash
   ls -R src/specify_cli/templates/
   # Should contain: command-templates/, plan-template.md, spec-template.md,
   # task-prompt-template.md, git-hooks/, claudeignore-template, AGENTS.md
   ```
5. **DO NOT delete** `.kittify/templates/` yet - migrations may reference it

**Files Moved**:
```
.kittify/templates/command-templates/*.md  → src/specify_cli/templates/command-templates/
.kittify/templates/plan-template.md        → src/specify_cli/templates/
.kittify/templates/spec-template.md        → src/specify_cli/templates/
.kittify/templates/task-prompt-template.md → src/specify_cli/templates/
.kittify/templates/git-hooks/              → src/specify_cli/templates/git-hooks/
.kittify/templates/claudeignore-template   → src/specify_cli/templates/
.kittify/templates/AGENTS.md               → src/specify_cli/templates/
```

**Verification**:
```bash
# Count files before and after
find .kittify/templates -type f | wc -l  # Should be 0 after move
find src/specify_cli/templates -type f | wc -l  # Should match original count
```

**Notes**:
- Preserve file permissions and timestamps
- Verify no symlinks are broken by move
- Git will track this as rename if files are identical

---

### Subtask T003 – Move `.kittify/missions/` → `src/specify_cli/missions/`

**Purpose**: Relocate all mission definitions to package location.

**Steps**:
1. Verify source exists: `ls -la .kittify/missions/`
2. Create destination: `mkdir -p src/specify_cli/missions/`
3. Move entire directory:
   ```bash
   mv .kittify/missions/* src/specify_cli/missions/
   ```
4. Verify structure preserved:
   ```bash
   ls -R src/specify_cli/missions/
   # Should contain: software-dev/ and research/ subdirectories
   # Each with: mission.yaml, templates/, command-templates/, constitution/
   ```
5. **Note**: `constitution/` subdirectories will be deleted in WP03, but leave them for now

**Files Moved**:
```
.kittify/missions/software-dev/  → src/specify_cli/missions/software-dev/
.kittify/missions/research/      → src/specify_cli/missions/research/
```

**Verification**:
```bash
# Verify mission.yaml files present
find src/specify_cli/missions -name "mission.yaml" | wc -l  # Should be 2
```

**Notes**:
- Mission constitution directories will be removed in WP03
- Keep the `constitution/` subdirectories for now to avoid breaking existing code
- Tests may reference mission locations - will update after move complete

---

### Subtask T004 – Move `.kittify/scripts/` → `src/specify_cli/scripts/` (if exists)

**Purpose**: Relocate script files to package location (if they exist in `.kittify/`).

**Steps**:
1. Check if `.kittify/scripts/` exists:
   ```bash
   if [ -d .kittify/scripts ]; then echo "EXISTS"; else echo "NOT FOUND"; fi
   ```
2. If EXISTS:
   - Create destination: `mkdir -p src/specify_cli/scripts/`
   - Move directory: `mv .kittify/scripts/* src/specify_cli/scripts/`
   - Verify structure: `ls -R src/specify_cli/scripts/`
3. If NOT FOUND:
   - Check if `scripts/` already exists at repo root (legacy location)
   - If at repo root, verify `pyproject.toml` already packages it correctly
   - Document finding: "Scripts already in correct location" or "No scripts to move"

**Expected Locations**:
- `.kittify/scripts/bash/` → `src/specify_cli/scripts/bash/`
- `.kittify/scripts/powershell/` → `src/specify_cli/scripts/powershell/`

**Verification**:
```bash
# If scripts exist, verify contents
if [ -d src/specify_cli/scripts ]; then
  find src/specify_cli/scripts -name "*.sh" | wc -l
  find src/specify_cli/scripts -name "*.ps1" | wc -l
fi
```

**Notes**:
- Scripts may already be in `scripts/` at repo root (not `.kittify/scripts/`)
- Check `pyproject.toml` line 87 to see current packaging location
- If scripts are at repo root, they may already be packaged correctly

---

### Subtask T005 – Update `src/specify_cli/template/manager.py` to load from `src/specify_cli/*`

**Purpose**: Update template loading code to use new package resource locations.

**Files**: `src/specify_cli/template/manager.py`

**Current Code** (lines ~59-122, `copy_specify_base_from_local()`):
```python
# Copy from .kittify/memory/ for consistency with other .kittify paths
memory_src = repo_root / ".kittify" / "memory"
if memory_src.exists():
    memory_dest = specify_root / "memory"
    if memory_dest.exists():
        shutil.rmtree(memory_dest)
    shutil.copytree(memory_src, memory_dest)

# Copy from .kittify/scripts/ (not root /scripts/)
scripts_src = repo_root / ".kittify" / "scripts"
# ...

# Copy from .kittify/templates/ (not root /templates/)
templates_src = repo_root / ".kittify" / "templates"
# ...

missions_candidates = [
    repo_root / ".kittify" / "missions",
    repo_root / "src" / "specify_cli" / ".kittify" / "missions",
]
```

**New Code** (update paths):
```python
# Memory still comes from .kittify/ (that's OK - it's runtime, not template source)
memory_src = repo_root / ".kittify" / "memory"
# ...keep this unchanged

# Scripts now in src/specify_cli/scripts/
scripts_src = repo_root / "src" / "specify_cli" / "scripts"
if scripts_src.exists():
    scripts_dest = specify_root / "scripts"
    # ...copy logic

# Templates now in src/specify_cli/templates/
templates_src = repo_root / "src" / "specify_cli" / "templates"
if templates_src.exists():
    templates_dest = specify_root / "templates"
    # ...copy logic

# Missions now in src/specify_cli/missions/
missions_candidates = [
    repo_root / "src" / "specify_cli" / "missions",
]
```

**Steps**:
1. Read `src/specify_cli/template/manager.py`
2. Locate `copy_specify_base_from_local()` function (around line 59)
3. Update paths:
   - `".kittify" / "scripts"` → `"src" / "specify_cli" / "scripts"`
   - `".kittify" / "templates"` → `"src" / "specify_cli" / "templates"`
   - `".kittify" / "missions"` → `"src" / "specify_cli" / "missions"`
4. **DO NOT change** `.kittify/memory/` path - that's runtime data, not templates
5. Remove legacy fallback paths from `missions_candidates` list
6. Verify `copy_specify_base_from_package()` function already uses `files("specify_cli")` - should not need changes

**Verification**:
```python
# After changes, function should load from:
# - src/specify_cli/templates/ (template source)
# - src/specify_cli/missions/ (mission source)
# - src/specify_cli/scripts/ (script source)
# - .kittify/memory/ (runtime data - unchanged)
```

**Notes**:
- The `copy_specify_base_from_package()` function (line ~139) should already work correctly - it uses `files("specify_cli")` which loads from the package
- Only `copy_specify_base_from_local()` needs updates (development/editable install path)

---

### Subtask T006 – Remove `.kittify/*` force-includes from `pyproject.toml`

**Purpose**: Clean up packaging configuration to prevent packaging `.kittify/` runtime artifacts.

**Files**: `pyproject.toml`

**Lines to REMOVE**:
```toml
# Line 85-89: [tool.hatch.build.targets.wheel.force-include]
[tool.hatch.build.targets.wheel.force-include]
".kittify/templates" = "specify_cli/templates"      # Line 86 - REMOVE
"scripts" = "specify_cli/scripts"                    # Line 87 - VERIFY
".kittify/memory" = "specify_cli/memory"            # Line 88 - REMOVE (CRITICAL)
".kittify/missions" = "specify_cli/missions"        # Line 89 - REMOVE

# Lines 94-98: [tool.hatch.build.targets.sdist] include section
include = [
    "src/**/*",
    ".kittify/templates/**/*",                       # Line 94 - REMOVE
    "scripts/**/*",                                   # Line 95 - VERIFY
    ".kittify/memory/**/*",                          # Line 96 - REMOVE (CRITICAL)
    ".kittify/missions/software-dev/**/*",           # Line 97 - REMOVE
    ".kittify/missions/research/**/*",               # Line 98 - REMOVE
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "pyproject.toml",
]

# Lines 109-110: [tool.hatch.build.targets.sdist.force-include]
[tool.hatch.build.targets.sdist.force-include]
".kittify/missions/software-dev" = ".kittify/missions/software-dev"  # Line 109 - REMOVE
".kittify/missions/research" = ".kittify/missions/research"          # Line 110 - REMOVE
```

**After Changes**:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/specify_cli"]
# No force-includes needed - everything under src/ gets packaged automatically

[tool.hatch.build.targets.sdist]
include = [
    "src/**/*",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "pyproject.toml",
]
exclude = [
    ".kittify/active-mission",
]
# No force-includes section needed
```

**Steps**:
1. Read `pyproject.toml`
2. **DELETE** entire `[tool.hatch.build.targets.wheel.force-include]` section (lines 85-89)
3. **UPDATE** `[tool.hatch.build.targets.sdist]` include list to remove `.kittify/*` entries (lines 94-98)
4. **DELETE** entire `[tool.hatch.build.targets.sdist.force-include]` section (lines 109-110)
5. **VERIFY** `packages = ["src/specify_cli"]` remains (line 83) - this packages everything under src/
6. **NOTE**: Line 87 `"scripts"` may refer to repo root `scripts/` - check if this exists and should be kept

**Critical Impact**:
- Removing line 88 (`.kittify/memory`) prevents packaging filled constitutions
- Removing line 96 (`.kittify/memory/**/*`) prevents packaging filled constitutions in sdist
- This is the PRIMARY FIX for the packaging contamination issue

**Verification**:
```bash
# Build and inspect
python -m build
unzip -l dist/spec_kitty_cli-*.whl | grep -i memory
# Should return empty (no memory/ directory in wheel)
```

---

### Subtask T007 – Verify spec-kitty's own `.kittify/` still works for dogfooding

**Purpose**: Ensure spec-kitty developers can still use spec-kitty commands on the spec-kitty repo itself.

**Test Scenarios**:
1. **Run `spec-kitty init` in spec-kitty repo**:
   - Should create/update `.kittify/` structure
   - Should NOT overwrite template sources (now in src/)
   - Should symlink or copy missions from src/ to `.kittify/missions/`

2. **Fill in constitution**:
   ```bash
   # Manually edit or use command to fill
   echo "# Spec Kitty Constitution" > .kittify/memory/constitution.md
   echo "## Test principle" >> .kittify/memory/constitution.md
   ```
   - File should be created in `.kittify/memory/`
   - Should NOT affect src/ directory

3. **Run spec-kitty commands**:
   ```bash
   cd .worktrees/some-feature/
   # Commands should work with project .kittify/
   spec-kitty agent feature check-prerequisites
   ```

4. **Build package and verify**:
   ```bash
   python -m build
   unzip -l dist/spec_kitty_cli-*.whl | grep "constitution.md"
   # Should only show: specify_cli/templates/... (template), NOT memory/constitution.md
   ```

**Expected Behavior**:
- Spec-kitty's `.kittify/` at repo root is treated like any other project's `.kittify/`
- Template sources are safely in src/ and get packaged
- Runtime artifacts in `.kittify/` are NOT packaged
- Worktrees can share `.kittify/memory/` via symlinks (existing behavior)

**Failure Cases to Test**:
- Running `spec-kitty init` should not prompt to overwrite src/specify_cli/templates/
- Filled constitution should not appear in built package
- Commands should not fail due to missing `.kittify/templates/`

---

### Subtask T008 – Build wheel and inspect contents (verify no contamination)

**Purpose**: Prove that packaging contamination is fixed.

**Steps**:
1. Clean old build artifacts:
   ```bash
   rm -rf dist/ build/ *.egg-info
   ```

2. Build package:
   ```bash
   python -m build
   ```

3. Inspect wheel contents:
   ```bash
   unzip -l dist/spec_kitty_cli-*.whl > wheel_contents.txt
   cat wheel_contents.txt
   ```

4. **CRITICAL CHECKS**:
   ```bash
   # Check 1: No .kittify/ paths in wheel
   grep "\.kittify/" wheel_contents.txt
   # Expected: Empty output (exit code 1)

   # Check 2: No memory/constitution.md in wheel (except template)
   grep "constitution\.md" wheel_contents.txt
   # Expected: Only specify_cli/templates/.../constitution.md (template)

   # Check 3: Templates packaged correctly
   grep "specify_cli/templates/" wheel_contents.txt | wc -l
   # Expected: Multiple entries (all template files)

   # Check 4: Missions packaged correctly
   grep "specify_cli/missions/" wheel_contents.txt | wc -l
   # Expected: Multiple entries (mission files)
   ```

5. **SUCCESS CRITERIA**:
   - Zero matches for `.kittify/` paths
   - Only template version of constitution.md present
   - All templates under `specify_cli/templates/`
   - All missions under `specify_cli/missions/`
   - Package size reasonable (<5MB)

**Verification Script**:
```bash
#!/bin/bash
set -e

python -m build

WHEEL=$(ls dist/spec_kitty_cli-*.whl | head -1)
echo "Inspecting: $WHEEL"

# Extract contents list
unzip -l "$WHEEL" > /tmp/wheel_contents.txt

# Critical checks
echo "Check 1: .kittify/ paths (should be 0)"
grep -c "\.kittify/" /tmp/wheel_contents.txt || echo "✓ PASS: No .kittify/ paths"

echo "Check 2: memory/constitution.md (should not exist)"
if grep "specify_cli/memory/constitution" /tmp/wheel_contents.txt; then
    echo "✗ FAIL: memory/constitution.md found in package!"
    exit 1
else
    echo "✓ PASS: No memory/constitution.md in package"
fi

echo "Check 3: Templates present (should be >0)"
grep -c "specify_cli/templates/" /tmp/wheel_contents.txt

echo "Check 4: Missions present (should be >0)"
grep -c "specify_cli/missions/" /tmp/wheel_contents.txt

echo "✓ ALL CHECKS PASSED"
```

---

### Subtask T009 – Test `spec-kitty init` from installed package

**Purpose**: Verify template loading works from installed package, not just editable install.

**Steps**:
1. **Create test environment**:
   ```bash
   # Create fresh virtualenv
   python -m venv /tmp/test-spec-kitty
   source /tmp/test-spec-kitty/bin/activate
   ```

2. **Install from wheel** (not editable):
   ```bash
   pip install dist/spec_kitty_cli-*.whl
   ```

3. **Create test project**:
   ```bash
   mkdir /tmp/test-project
   cd /tmp/test-project
   git init
   ```

4. **Run `spec-kitty init`**:
   ```bash
   spec-kitty init
   # Select mission: software-dev
   # Select script type: bash (or powershell on Windows)
   ```

5. **Verify results**:
   ```bash
   ls -la .kittify/
   # Should contain: memory/, missions/, templates/, scripts/, AGENTS.md

   ls -la .kittify/templates/command-templates/
   # Should contain: constitution.md, plan.md, specify.md, etc.

   ls -la .kittify/missions/software-dev/
   # Should contain: mission.yaml, templates/, command-templates/

   cat .kittify/memory/constitution.md
   # Should be blank template, NOT filled-in spec-kitty constitution
   ```

6. **Run a command**:
   ```bash
   # Try running specify command (just to test loading works)
   spec-kitty agent feature setup-spec --help
   # Should not error about missing templates
   ```

7. **Cleanup**:
   ```bash
   deactivate
   rm -rf /tmp/test-spec-kitty /tmp/test-project
   ```

**Success Criteria**:
- `spec-kitty init` completes successfully
- All template files copied to project's `.kittify/`
- Constitution template is blank/placeholder (not spec-kitty's filled version)
- Commands can load templates without errors
- No references to package installation path in user's `.kittify/`

**Failure Scenarios to Watch For**:
- Error: "Template not found" → Template loading broken
- Error: "No such file or directory: .kittify/templates" → Path references not updated
- Constitution has spec-kitty's principles → Packaging contamination still present
- Command errors referencing src/ paths → Hardcoded development paths leaked

---

## Test Strategy

**No automated tests required** - this is infrastructure refactoring. Manual verification via subtasks T007, T008, T009 covers:

1. **Package inspection** (T008): Automated wheel content verification
2. **Dogfooding** (T007): Spec-kitty repo still usable for development
3. **User experience** (T009): Fresh install works correctly

**Integration Testing**: WP06 will perform end-to-end validation across all platforms.

---

## Risks & Mitigations

| Risk | Impact | Mitigation | Covered By |
|------|--------|------------|------------|
| Template loading breaks existing code | High | Comprehensive grep audit before moving files | T001 |
| Worktree symlinks break | Medium | Verify symlinks reference project `.kittify/`, not templates | T007 |
| Package size increases | Low | Verify src/ structure is clean, no duplicate files | T008 |
| Migration tests fail | Medium | Update migration tests after template move complete | Defer to WP02 |
| Existing installs break | High | Test from installed package, not just editable | T009 |
| Development workflow breaks | High | Test spec-kitty commands on spec-kitty repo | T007 |

**Critical Path Dependencies**: This WP must complete before WP05 (Constitution Command Redesign) can update the constitution template in its new location.

---

## Definition of Done Checklist

- [ ] All subtasks T001-T009 completed
- [ ] Template files moved to `src/specify_cli/templates/`
- [ ] Mission files moved to `src/specify_cli/missions/`
- [ ] Script files moved to `src/specify_cli/scripts/` (if applicable)
- [ ] `template/manager.py` updated to load from `src/specify_cli/*`
- [ ] `pyproject.toml` force-includes removed (lines 86-110)
- [ ] Wheel inspection shows zero `.kittify/` or `memory/constitution.md` entries
- [ ] `spec-kitty init` works from installed package
- [ ] Spec-kitty dogfooding verified (can fill constitution without packaging it)
- [ ] Git commit created with clear message explaining relocation
- [ ] Code review requested from maintainer

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. **Grep audit complete**: Reviewer should verify all `.kittify/` references identified and planned for update
2. **File move verified**: Check `git diff --summary` shows renames, not deletes+adds
3. **Template loading updated**: Verify `template/manager.py` paths updated correctly
4. **pyproject.toml clean**: Verify no `.kittify/*` force-includes remain
5. **Wheel inspection passed**: Verify inspection script output shows no contamination
6. **Init test passed**: Verify fresh install test created correct `.kittify/` structure

**Red Flags for Reviewer**:
- Any `.kittify/` paths remaining in pyproject.toml force-includes
- Wheel contains `specify_cli/memory/` directory
- Template loading uses hardcoded paths instead of package resources
- Git diff shows file deletes instead of renames (loses history)

**Context for Reviewer**:
- This is the primary fix for issue where spec-kitty's filled constitution gets packaged and distributed to all users
- Template sources now live in `src/` (packaged), project instances in `.kittify/` (runtime)
- This enables safe dogfooding - spec-kitty developers can use spec-kitty commands without contamination risk

---

## Activity Log

- 2026-01-12T11:30:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter
2. **Use CLI**: `spec-kitty agent tasks move-task WP01 --to <lane> --note "message"`

The CLI command also updates the activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-01-12T10:38:46Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-12T10:43:06Z – unknown – lane=for_review – Ready for review
- 2026-01-12T10:43:17Z – agent – lane=doing – Started review via workflow command

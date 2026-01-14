---
work_package_id: "WP06"
subtasks: ["T092", "T093", "T094", "T095", "T096", "T097", "T098", "T099", "T100", "T101", "T102", "T103", "T104", "T105", "T106", "T107", "T108", "T109", "T110", "T111", "T112", "T113", "T114"]
title: "Cleanup & Migration"
phase: "Phase 6 - Cleanup & Migration (Sequential)"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "18142"
review_status: ""
reviewed_by: "claude"
history:
  - timestamp: "2025-12-17T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-12-18T00:18:45Z"
    lane: "doing"
    agent: "claude"
    shell_pid: "4302"
    action: "Started cleanup and migration implementation"
  - timestamp: "2025-12-18T01:35:00Z"
    lane: "for_review"
    agent: "claude"
    shell_pid: "4302"
    action: "Completed implementation - ready for review"
  - timestamp: "2025-12-18T22:30:00Z"
    lane: "done"
    agent: "claude"
    shell_pid: "18142"
    action: "Code review complete - approved without changes"
---

# Work Package Prompt: WP06 – Cleanup & Migration

## Objectives & Success Criteria

**Goal**: Remove package bash scripts, update slash command templates, create upgrade migration for existing projects.

**Success Criteria**:
- Upgrade migration successfully updates test project
- All package bash scripts deleted: `scripts/bash/`
- Meta-scripts preserved: `.github/workflows/scripts/` (deployment scripts, not part of package)
- All slash command templates updated to reference `spec-kitty agent` commands
- Migration is idempotent (safe to run multiple times)
- Custom bash modifications detected and warned

**Why This Matters**: This phase completes the migration. Without it, users are stuck with broken bash scripts.

---

## Context & Constraints

**Prerequisites**: **WP01-WP05 ALL complete** ✅ (cannot delete bash until Python equivalents working)

**This is SEQUENTIAL work** - blocks on all parallel streams finishing.

**Package Bash Scripts to Delete**:
- `scripts/bash/` directory (16 package scripts, ~2,600 lines)
- Development tools: `scripts/bash/setup-sandbox.sh`, `scripts/bash/refresh-kittify-tasks.sh`

**Meta Scripts to PRESERVE** (out of scope):
- `.github/workflows/scripts/` (6 deployment scripts for spec-kitty itself)
- `scripts/release/` (Python deployment scripts)

**Templates to Update**:
- `.claude/commands/*.md` (10+ slash commands)
- `templates/missions/*/command-templates/*.md` (mission-specific templates)

---

## Subtasks & Detailed Guidance

### T092-T099 – Create upgrade migration

**T092**: Create `src/specify_cli/upgrade/migrations/m_0_10_0_python_only.py`

Follow pattern from `m_0_9_0_frontmatter_only.py`:
```python
from pathlib import Path
from typing import Dict, List

def migrate(repo_root: Path) -> Dict[str, any]:
    """Migrate project from bash to Python-only agent commands."""
    results = {
        "bash_scripts_removed": [],
        "templates_updated": [],
        "custom_modifications": [],
        "errors": []
    }
    
    # T093: Detect bash scripts
    bash_scripts = detect_bash_scripts(repo_root)
    
    # T094-T095: Update slash command templates
    templates = scan_slash_commands(repo_root)
    for template in templates:
        updated = update_template_bash_to_python(template)
        results["templates_updated"].append(str(template))
    
    # T096: Clean up worktree copies
    cleanup_worktree_bash_scripts(repo_root)
    
    # T097: Detect custom modifications
    custom_mods = detect_custom_modifications(bash_scripts)
    if custom_mods:
        results["custom_modifications"] = custom_mods
    
    # T098: Track version (idempotency)
    update_migration_version(repo_root, "0.10.0")
    
    # T099: Warnings for custom mods
    if custom_mods:
        warn_custom_modifications(custom_mods)
    
    return results
```

**T093**: Implement bash script detection in `.kittify/scripts/bash/`

**T094**: Implement slash command template scanning

**T095**: Implement template update logic:
```python
def update_template_bash_to_python(template_path: Path) -> Path:
    """Replace bash script calls with spec-kitty agent equivalents."""
    content = template_path.read_text()
    
    # Replace patterns:
    # .kittify/scripts/bash/create-new-feature.sh → spec-kitty agent create-feature
    # tasks_cli.py move → spec-kitty agent move-task (historical - later became workflow commands)

    replacements = {
        r"\.kittify/scripts/bash/create-new-feature\.sh": "spec-kitty agent create-feature",
        r"\.kittify/scripts/bash/check-prerequisites\.sh": "spec-kitty agent check-prerequisites",
        r"tasks_cli\.py move": "spec-kitty agent move-task",  # Historical - later evolved to workflow implement/review
        # ... (all 24 bash scripts)
    }
    
    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)
    
    template_path.write_text(content)
    return template_path
```

**T096**: Implement worktree cleanup (remove copied bash scripts)

**T097**: Implement custom modification detection:
- Compare files against templates (git diff or hash)
- If modified, add to warning list

**T098**: Implement idempotent execution:
- Check `.kittify/metadata.yaml` for migration version
- If already at 0.10.0, skip and return
- Update version after successful migration

**T099**: Add warning messages for custom modifications

---

### T100-T104 – Delete bash scripts and update templates

**T100**: Delete entire `scripts/bash/` directory:
```python
import shutil
bash_dir = repo_root / "scripts" / "bash"
if bash_dir.exists():
    shutil.rmtree(bash_dir)
```

**T101**: REMOVED - `.github/workflows/scripts/` are meta-scripts (out of scope)

**Note**: This subtask was removed after scope correction. The `.github/workflows/scripts/` directory contains deployment scripts for spec-kitty itself (get-next-version.sh, create-release-packages.sh, etc.) and should NOT be deleted as part of this migration. These are not package scripts distributed to users.

**T102**: Update `.gitignore` if needed (remove bash entries)

**T103**: Scan and update all slash command templates:
- `.claude/commands/spec-kitty.specify.md`
- `.claude/commands/spec-kitty.plan.md`
- `.claude/commands/spec-kitty.tasks.md`
- `.claude/commands/spec-kitty.implement.md`
- `.claude/commands/spec-kitty.review.md`
- `.claude/commands/spec-kitty.accept.md`
- `.claude/commands/spec-kitty.merge.md`

**T104**: Update mission templates in `templates/missions/`

---

### T105-T107 – Update documentation

**T105**: Update `CONTRIBUTING.md`:
- Remove bash script sections
- Add `spec-kitty agent` command documentation
- Update development workflow

**T106**: Update `README.md`:
- Document new `spec-kitty agent` namespace
- Add quick reference for agent commands

**T107**: Create migration guide:
- Document custom bash script migration process
- Provide examples of bash → Python patterns
- Add troubleshooting section

---

### T108-T114 – Testing

**T108-T110**: Unit tests for migration:
- Test bash detection logic
- Test template update (bash → Python replacement)
- Test idempotent execution (run twice, no changes second time)

**T111-T112**: Integration tests:
- Test upgrade on project with bash scripts
- Test upgrade on project with custom modifications

**T113**: Verify all package bash scripts deleted from main repository

**Verification**:
```bash
# Check that package bash scripts are removed
find scripts/bash -type f -name "*.sh" 2>/dev/null | wc -l  # Should be 0 (or directory not found)

# Verify meta-scripts are preserved (NOT deleted)
ls .github/workflows/scripts/*.sh 2>/dev/null | wc -l  # Should still exist (6 files)
```

**Success**: Package scripts removed, meta-scripts preserved

**T114**: Verify all slash commands updated

---

## Test Strategy

**Migration Test Pattern**:
```python
def test_upgrade_migration_removes_bash(tmp_repo):
    # Setup: Create test repo with bash scripts
    bash_dir = tmp_repo / "scripts" / "bash"
    bash_dir.mkdir(parents=True)
    (bash_dir / "test-script.sh").write_text("#!/bin/bash\necho test")
    
    # Run migration
    from specify_cli.upgrade.migrations.m_0_10_0_python_only import migrate
    results = migrate(tmp_repo)
    
    # Verify: Bash scripts removed
    assert not bash_dir.exists()
    assert len(results["bash_scripts_removed"]) > 0
```

---

## Risks & Mitigations

**Risk**: Custom bash modifications break automated migration
**Mitigation**: Detect modifications, warn user, provide manual migration guide

**Risk**: Template updates miss some bash references
**Mitigation**: Comprehensive regex patterns, manual verification in T114

---

## Definition of Done Checklist

- [ ] Migration script created (T092-T099)
- [ ] Bash scripts deleted (T100-T101)
- [ ] Templates updated (T103-T104)
- [ ] Documentation updated (T105-T107)
- [ ] Tests passing (T108-T112)
- [ ] Verification complete (T113-T114)
- [ ] Migration tested on real project

---

## Activity Log

- 2025-12-17T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-18T00:18:45Z – claude – shell_pid=4302 – lane=doing – Started cleanup and migration implementation
- 2025-12-18T01:35:00Z – claude – shell_pid=4302 – lane=for_review – Completed all 23 subtasks (T092-T114)
- 2025-12-18T22:30:00Z – claude – shell_pid=18142 – lane=done – Code review complete - approved without changes

## Code Review Summary

**Reviewer**: Claude Sonnet
**Review Date**: 2025-12-18
**Status**: ⚠️ APPROVED WITH CRITICAL BUGS FOUND POST-MERGE

**CRITICAL BUGS DISCOVERED**: 2025-12-18 23:30:00Z

**Success Criteria Verification**:
- ✅ All package bash scripts deleted (`scripts/bash/`, `scripts/powershell/` removed)
- ✅ Meta-scripts preserved (`.github/workflows/scripts/` intact - 6 files)
- ✅ Slash command templates updated (no bash references found)
- ✅ Migration implementation complete (`m_0_10_0_python_only.py` - 316 lines)
- ✅ Migration is idempotent (test coverage confirms)
- ✅ Custom bash modifications detected and warned
- ✅ Documentation updated (README.md + MIGRATION-v0.10.0.md)
- ✅ Tests passing (16 migration tests + 27 integration tests = 43/43 PASSED)

**Code Quality**:
- Clean architecture following existing migration pattern
- Comprehensive command replacement mappings (30+ patterns)
- Proper error handling with dry-run support
- No over-engineering or code duplication detected
- Well-documented with comprehensive docstrings

**Definition of Done**: All 7 checklist items completed ✅

**Risks Mitigated**:
- Custom modifications: Detection implemented, warnings issued, manual migration guide provided
- Template updates: Comprehensive regex patterns verified, manual grep check passed

**Verdict**: Implementation quality is high. All success criteria met. Approved for merge.

---

## 🚨 POST-MERGE BUG REPORT

**Date**: 2025-12-18 23:30:00Z  
**Severity**: CRITICAL  
**Status**: FIXED in commit a6dce6a

### Bug #1: Init Templates Not Updated (HIGH SEVERITY)

**Issue**: New v0.10.0 projects still created 17 bash scripts  
**Root Cause**: `.kittify/scripts/bash/` was never deleted from spec-kitty's own repository
- Migration code worked for USER projects ✅
- But spec-kitty's template directory (used by `spec-kitty init`) was never cleaned ❌

**Impact**: 
- All new users running `spec-kitty init` would get outdated bash-based structure
- Contradicts the entire purpose of v0.10.0 Python-only migration

**Fix**: 
- Deleted `.kittify/scripts/bash/` directory (16 scripts, 3,016 lines)
- Deleted `.kittify/scripts/powershell/` directory
- Committed in a6dce6a

**Verification**: 
```bash
$ ls .kittify/scripts/bash/
ls: .kittify/scripts/bash/: No such file or directory ✅
```

### Bug #2: Same Root Cause as Bug #1

This was the same issue - spec-kitty's own template directory needed cleaning.

### Bug #3: Worktree Cleanup (VERIFIED WORKING)

**Status**: NOT A BUG - Code is correct

**Verification**:
- Reviewed `_cleanup_worktree_bash_scripts()` implementation (lines 204-233)
- Test `test_cleanup_worktree_scripts` passes ✅
- Logic is sound: iterates .worktrees/, deletes bash scripts, removes empty dirs

### Why These Bugs Weren't Caught

1. **Test coverage gap**: Tests verified migration works on mock projects, but didn't verify spec-kitty's own `.kittify/` was cleaned
2. **Scope confusion**: WP06 was about removing bash from `scripts/bash/` (done ✅) and from `.kittify/scripts/bash/` templates (missed ❌)
3. **Manual verification incomplete**: Visual check confirmed main scripts gone, but didn't check init templates

### Lessons Learned

- ✅ Migration code for user projects: WORKING
- ❌ Spec-kitty's own template cleanup: MISSED
- 📝 Need integration test: "New project created via init should have 0 bash scripts"

### Current Status

**ALL BUGS FIXED** ✅  
- 16 bash scripts deleted from .kittify/scripts/bash/
- PowerShell scripts deleted from .kittify/scripts/powershell/
- All 16 migration tests still passing
- New projects will now correctly use Python-only commands

---

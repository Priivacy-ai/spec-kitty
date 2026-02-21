# Research: Constitution Packaging Safety and Redesign

**Phase**: 0 (Research & Discovery)
**Date**: 2026-01-12
**Feature**: 011-constitution-packaging-safety-and-redesign

## Overview

This document captures research findings for the four major goals of this feature:

1. Template relocation strategy (`.kittify/` → `src/specify_cli/`)
2. psutil patterns for cross-platform process management
3. Migration repair patterns for graceful failure handling
4. Constitution command redesign patterns

## Research Area 1: Template Relocation Strategy

### Decision: Move all template sources to src/specify_cli/

**Rationale:**

- **Clean separation**: Template source code (for packaging) vs project instances (for use)
- **Safe dogfooding**: Spec-kitty developers can run `spec-kitty init` without contaminating package
- **Root cause fix**: Eliminates packaging contamination at architectural level, not through .gitignore hacks
- **Standard Python packaging**: All package resources under src/ follows Python best practices

**Alternatives Considered:**

1. **Keep in .kittify/ with better .gitignore**
   - Rejected: Still fragile, developers must remember not to package certain files
   - Doesn't solve root cause, just mitigates symptoms

2. **Separate templates/ directory at root**
   - Rejected: Adds another top-level directory, fragments package structure
   - Still requires force-include mapping in pyproject.toml

3. **Use --template-root flag for dogfooding**
   - Rejected: Requires all developers to remember to use flag
   - Error-prone, doesn't prevent accidents

### Implementation Approach

**File Moves Required:**

```
.kittify/templates/          → src/specify_cli/templates/
.kittify/missions/           → src/specify_cli/missions/
.kittify/scripts/ (if there) → src/specify_cli/scripts/
```

**Code Updates Required:**

1. `src/specify_cli/template/manager.py`:
   - `copy_specify_base_from_local()`: Update paths from `.kittify/*` to `src/specify_cli/*`
   - `copy_specify_base_from_package()`: Already uses `files("specify_cli")`, should work
   - Remove legacy fallback paths

2. Search all Python files for `.kittify/` references:

   ```bash
   grep -r "\.kittify/" src/specify_cli/*.py
   ```

   Update to use package resource APIs (`importlib.resources.files()`)

3. `pyproject.toml`:
   - **REMOVE** lines 86-89: `[tool.hatch.build.targets.wheel.force-include]`
   - **REMOVE** lines 94-97: `.kittify/templates/**/*`, `.kittify/memory/**/*`, `.kittify/missions/**/*`
   - **REMOVE** lines 109-110: `.kittify/missions/*` force-includes
   - **KEEP** only: `packages = ["src/specify_cli"]` (line 83)

4. Test migrations:
   - Migrations that copy templates need to use package resources
   - Update `m_0_7_3_update_scripts.py`, `m_0_10_6_workflow_simplification.py` to reference new locations

**Verification:**

```bash
# Build package
python -m build

# Extract and inspect wheel
unzip -l dist/spec_kitty_cli-*.whl | grep -E '(\.kittify|memory/constitution\.md)'

# Expected: Zero matches for .kittify/, only specify_cli/templates/ and specify_cli/missions/
```

**Risk Mitigation:**

- Grep entire codebase for hardcoded `.kittify/` paths before moving files
- Test `spec-kitty init` from installed package (not editable install)
- Verify worktree symlinks still work (they reference `.kittify/memory/` in project root, not package)

---

## Research Area 2: psutil Cross-Platform Process Management

### Decision: Use psutil.Process() for all process operations

**Rationale:**

- **Cross-platform**: Works identically on Windows, macOS, Linux
- **No signal compatibility issues**: psutil abstracts away POSIX vs Windows differences
- **Better process control**: Can check if process exists, get children, graceful vs force termination
- **Maintained library**: Active development, well-tested across platforms

**Alternatives Considered:**

1. **Platform detection with signal module**

   ```python
   if platform.system() == 'Windows':
       # Use subprocess.terminate() or TerminateProcess
   else:
       os.kill(pid, signal.SIGKILL)
   ```

   - Rejected: Fragile, requires maintaining two code paths
   - Windows still has edge cases (services, permissions, process trees)

2. **subprocess.Popen with platform-specific terminate()**
   - Rejected: Only works if we started the process with subprocess
   - Dashboard may be started by external tools or manually

3. **Direct Windows API via ctypes**
   - Rejected: Requires Windows-specific expertise
   - More code to maintain, error-prone

### Implementation Pattern

**Install psutil:**

```toml
# pyproject.toml
dependencies = [
    ...
    "psutil>=5.9.0",
]
```

**Replace signal.SIGKILL patterns:**

**Before:**

```python
import signal
import os

# Check if process alive
os.kill(pid, 0)

# Kill process
os.kill(pid, signal.SIGKILL)
```

**After:**

```python
import psutil

# Check if process alive
try:
    proc = psutil.Process(pid)
    is_alive = proc.is_running()
except psutil.NoSuchProcess:
    is_alive = False

# Graceful termination
try:
    proc = psutil.Process(pid)
    proc.terminate()  # SIGTERM on POSIX, TerminateProcess on Windows
    proc.wait(timeout=3)  # Wait up to 3 seconds
except psutil.TimeoutExpired:
    proc.kill()  # Force kill if graceful failed
except psutil.NoSuchProcess:
    pass  # Already dead
```

**Key Benefits:**

- `proc.is_running()` works on all platforms (no signal 0 trick)
- `proc.terminate()` is cross-platform graceful shutdown
- `proc.kill()` is cross-platform force kill
- `proc.wait(timeout=N)` prevents hanging on unresponsive processes
- Automatic handling of process-not-found errors

**Files to Update:**

- `src/specify_cli/dashboard/lifecycle.py`:
  - Line 188: `os.kill(pid, signal.SIGKILL)` → `psutil.Process(pid).kill()`
  - Line 289: Same replacement
  - Line 354: Same replacement
  - Line 381: Same replacement
  - Line 464: `os.kill(pid, signal.SIGTERM)` → `psutil.Process(pid).terminate()`
  - Line 470: `os.kill(pid, signal.SIGKILL)` → `psutil.Process(pid).kill()`
  - Line 499: Same replacement
  - Line 100: `os.kill(pid, 0)` → `psutil.Process(pid).is_running()`

**Testing:**

- Unit tests: Mock psutil.Process, verify calls
- Integration test: Start dashboard, verify terminate/kill work
- Windows smoke test: Run on Windows 10/11, verify no ERR_EMPTY_RESPONSE

---

## Research Area 3: Migration Repair Patterns

### Decision: Graceful failure with skip logic for missing files

**Rationale:**

- **Idempotency**: Migrations should be safe to run multiple times
- **Robustness**: Handle cases where files were manually deleted or never existed
- **Forward compatibility**: Later migrations can clean up what earlier ones couldn't

**Problem Pattern Identified:**

1. **m_0_7_3_update_scripts.py** (lines 44-55):
   - `can_apply()` checks if template scripts exist in package
   - Fails if bash scripts no longer in package (removed in later version)
   - **Fix**: Return `(True, "")` if scripts missing, let `apply()` handle gracefully

2. **m_0_10_6_workflow_simplification.py** (lines 78-94):
   - `can_apply()` checks mission templates before copying them
   - But templates aren't copied until `apply()` runs
   - **Fix**: Always return `(True, "")`, let `apply()` copy templates first

3. **m_0_10_2_update_slash_commands.py**:
   - Needs to remove legacy .toml files
   - Should verify in spec, but likely doesn't clean up .toml files
   - **Fix**: Add explicit .toml removal in `apply()`

4. **m_0_10_0_python_only.py**:
   - Should remove `.kittify/scripts/tasks/` directory (obsolete Python helpers)
   - Needs to verify it actually does this
   - **Fix**: Ensure directory removal is explicit

### Implementation Pattern

**Graceful can_apply():**

```python
def can_apply(self, project_path: Path) -> tuple[bool, str]:
    """Check if migration can be applied.

    Return (True, "") if:
    - Files exist and need updating
    - Files don't exist (already cleaned up or never existed)

    Only return (False, "reason") for structural issues.
    """
    # Check if project structure allows migration
    kittify_dir = project_path / ".kittify"
    if not kittify_dir.exists():
        return False, "No .kittify directory (not a spec-kitty project)"

    # Always allow migration - let apply() handle missing files
    return True, ""
```

**Robust apply():**

```python
def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
    """Apply migration with graceful handling of missing files."""
    changes = []
    warnings = []
    errors = []

    # Try to copy template, skip if source doesn't exist
    template_source = pkg_root / "templates" / "file.md"
    if not template_source.exists():
        warnings.append("Template file.md not in package (already removed or never existed)")
        # Migration succeeds even if template missing
    else:
        # Copy template...
        changes.append("Updated file.md")

    # Always succeed unless catastrophic failure
    success = len(errors) == 0
    return MigrationResult(success=success, changes_made=changes, warnings=warnings, errors=errors)
```

**New Migration: m_0_10_12_constitution_cleanup.py**

Purpose: Remove mission-specific constitution directories

```python
@MigrationRegistry.register
class ConstitutionCleanupMigration(BaseMigration):
    """Remove mission-specific constitution directories.

    As of 0.10.12, spec-kitty uses only project-level constitutions
    at .kittify/memory/constitution.md. Mission-specific constitutions
    in .kittify/missions/*/constitution/ are removed.
    """

    migration_id = "0.10.12_constitution_cleanup"
    description = "Remove mission-specific constitution directories"
    target_version = "0.10.12"

    def detect(self, project_path: Path) -> bool:
        """Check if any mission has a constitution directory."""
        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            return False

        for mission_dir in missions_dir.iterdir():
            if mission_dir.is_dir():
                constitution_dir = mission_dir / "constitution"
                if constitution_dir.exists():
                    return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Always applicable - removal is safe."""
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Remove constitution directories from all missions."""
        changes = []
        warnings = []

        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            return MigrationResult(success=True, changes_made=[], warnings=[], errors=[])

        for mission_dir in missions_dir.iterdir():
            if not mission_dir.is_dir():
                continue

            constitution_dir = mission_dir / "constitution"
            if constitution_dir.exists():
                if dry_run:
                    changes.append(f"Would remove {mission_dir.name}/constitution/")
                else:
                    shutil.rmtree(constitution_dir)
                    changes.append(f"Removed {mission_dir.name}/constitution/")

        if changes:
            warnings.append(
                "Mission-specific constitutions removed. "
                "Use project-level constitution at .kittify/memory/constitution.md instead. "
                "Run /spec-kitty.constitution to create one if needed."
            )

        return MigrationResult(success=True, changes_made=changes, warnings=warnings, errors=[])
```

---

## Research Area 4: Constitution Command Redesign

### Decision: Phase-based discovery with skip options

**Rationale:**

- **Flexibility**: Users can skip phases they don't need
- **Guided workflow**: Phases group related questions logically
- **Minimal vs comprehensive**: Natural distinction (skip most phases vs complete all)
- **Consistency**: Matches `/spec-kitty.plan` workflow structure

**Phase Structure:**

**Phase 1: Technical Standards**

- Questions: Languages/frameworks, testing requirements, code quality tools
- Skip option: "Skip technical standards phase"
- Minimal path: Usually complete this phase (3-4 questions)

**Phase 2: Code Quality**

- Questions: PR requirements, review process, quality gates
- Skip option: "Skip code quality phase"
- Minimal path: Often skip this phase

**Phase 3: Tribal Knowledge**

- Questions: Team conventions, lessons learned, historical decisions
- Skip option: "Skip tribal knowledge phase"
- Minimal path: Often skip this phase

**Phase 4: Governance**

- Questions: Amendment process, compliance, versioning
- Skip option: "Skip governance phase"
- Minimal path: Use defaults (simple governance rules)

**Workflow Pattern:**

```markdown
## Phase 1: Technical Standards

Let's start by capturing your technical standards. These are the non-negotiable
requirements that all features must follow.

**You can skip this phase if:** Your project has no specific technical requirements
beyond standard practices for your stack.

Options:
A) Answer questions about technical standards
B) Skip this phase entirely
C) Use recommended defaults

[User selects A]

Question 1/4: What languages and frameworks are required for this project?
[User answers: Python 3.11+, FastAPI]

Question 2/4: What testing framework and coverage requirements?
[User answers: pytest, 80% coverage]

...

Phase 1 complete. Moving to Phase 2: Code Quality...
```

**Template Update:**

Current: `.kittify/templates/command-templates/constitution.md` (placeholder-filling)
New: `src/specify_cli/templates/command-templates/constitution.md` (phase-based discovery)

Key changes:

- Remove placeholder-filling approach (lines 64-127)
- Add phase-based discovery workflow
- Add skip logic for each phase
- Generate final constitution from accumulated answers
- Present summary before writing

**Implementation Notes:**

- Constitution command runs from main repo (not worktree)
- Writes to `.kittify/memory/constitution.md` at project root
- Should work whether or not user has run `spec-kitty init` yet
- No longer needs to update "dependent templates" (that's a template maintenance task, not user-facing)

---

## Summary

All research areas have clear decisions and implementation approaches:

1. **Template Relocation**: Move to `src/specify_cli/`, update manager.py, remove pyproject.toml force-includes
2. **psutil Integration**: Replace all os.kill/signal usage with psutil.Process() methods
3. **Migration Repairs**: Graceful can_apply(), robust apply(), new constitution cleanup migration
4. **Constitution Redesign**: Phase-based discovery with skip options, minimal vs comprehensive paths

No unresolved clarifications remain. Ready to proceed to Phase 1 (Design).

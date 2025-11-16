---
work_package_id: "WP07"
subtasks:
  - "T049"
  - "T050"
  - "T051"
  - "T052"
  - "T053"
  - "T054"
  - "T055"
  - "T056"
title: "Path Convention Validation"
phase: "Phase 4 - Integration"
lane: "done"
assignee: "codex"
agent: "codex"
shell_pid: "60030"
review_status: ""
reviewed_by: "codex"
history:
  - timestamp: "2025-01-16T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 – Path Convention Validation

## Objectives & Success Criteria

**Goal**: Implement path convention validation that ensures project structure matches mission-declared paths, with progressive enforcement (warnings at switch, errors at acceptance).

**Success Criteria**:
- Path validation module exists at `src/specify_cli/validators/paths.py`
- Validates mission.yaml paths section against actual project directories
- Progressive enforcement: warnings (non-blocking) at mission switch, errors (blocking) at acceptance
- Clear error messages with actionable suggestions ("mkdir -p src/")
- Integration with mission switch command and acceptance workflow
- All 8 subtasks (T049-T056) completed

## Context & Constraints

**Problem Statement**: Mission.yaml declares path conventions but nothing enforces them:

**Current State** (documentation-only):
```yaml
# software-dev mission.yaml
paths:
  workspace: "src/"
  tests: "tests/"
  deliverables: "contracts/"
  documentation: "docs/"
```

Projects can violate these conventions without detection. Commands reference paths that may not exist.

**Desired State** (enforced):
- Mission switch checks paths, warns if missing (non-blocking)
- Acceptance checks paths, errors if missing (blocking)
- Clear suggestions: "Create directory: mkdir -p src/"

**Supporting Documents**:
- Spec: `kitty-specs/005-refactor-mission-system/spec.md` (User Story 5, FR-020 through FR-023)
- Plan: `kitty-specs/005-refactor-mission-system/plan.md` (Architecture Decision #4: Progressive enforcement)
- Data Model: `kitty-specs/005-refactor-mission-system/data-model.md` (PathValidationResult model)

**Design Decisions**:
- **Timing**: Option D - Progressive (warn at switch, error at acceptance)
- **Rationale**: User-friendly (supports incremental setup), catches issues early
- **Implementation**: strict parameter toggles warning vs error behavior

**Path Conventions by Mission**:

**Software-Dev**:
- workspace: `src/`
- tests: `tests/`
- deliverables: `contracts/`
- documentation: `docs/`

**Research**:
- workspace: `research/`
- data: `data/`
- deliverables: `findings/`
- documentation: `reports/`

## Subtasks & Detailed Guidance

### Subtask T049 – Create paths.py module

**Purpose**: Establish path validation module.

**Steps**:
1. Create file: `src/specify_cli/validators/paths.py`
2. Add module docstring and imports:
   ```python
   """Path convention validation for spec-kitty missions.

   Validates that project directory structure matches mission-declared
   path conventions (e.g., src/, tests/, data/).

   Supports progressive enforcement:
   - Non-strict (warnings): Used at mission switch (user-friendly)
   - Strict (errors): Used at acceptance (enforced gates)
   """

   from __future__ import annotations

   from dataclasses import dataclass
   from pathlib import Path
   from typing import Dict, List

   from specify_cli.mission import Mission
   ```

3. Define exception:
   ```python
   class PathValidationError(Exception):
       """Raised when path validation fails in strict mode."""
       pass
   ```

**Files**: `src/specify_cli/validators/paths.py` (new)

**Parallel?**: No (foundation)

**Notes**: Simple module structure. Import Mission to access path configuration.

---

### Subtask T050 – Define PathValidationResult dataclass

**Purpose**: Create typed result object for path validation.

**Steps**:
1. Add dataclass to paths.py (from data-model.md):
   ```python
   @dataclass
   class PathValidationResult:
       """Result of path convention validation."""
       mission_name: str
       required_paths: Dict[str, str]  # key → path (e.g., "workspace" → "src/")
       existing_paths: List[str]  # Paths that exist
       missing_paths: List[str]  # Paths that don't exist
       warnings: List[str]  # Warning messages
       suggestions: List[str]  # Suggested fixes

       @property
       def is_valid(self) -> bool:
           """True if all required paths exist."""
           return len(self.missing_paths) == 0

       def format_warnings(self) -> str:
           """Format warnings for display."""
           if not self.warnings:
               return ""

           output = ["Path Convention Warnings:"]
           for warning in self.warnings:
               output.append(f"  - {warning}")

           output.append("")
           output.append("Suggestions:")
           for suggestion in self.suggestions:
               output.append(f"  - {suggestion}")

           return "\n".join(output)

       def format_errors(self) -> str:
           """Format as errors (for strict mode)."""
           if not self.missing_paths:
               return ""

           output = ["Path Convention Errors:"]
           for warning in self.warnings:
               output.append(f"  - {warning}")

           output.append("")
           output.append("Required Actions:")
           for suggestion in self.suggestions:
               output.append(f"  - {suggestion}")

           output.append("")
           output.append("These directories are required by the active mission.")

           return "\n".join(output)
   ```

**Files**: `src/specify_cli/validators/paths.py`

**Parallel?**: No (required by validation functions)

**Notes**: Two format methods - warnings for switch, errors for acceptance.

---

### Subtask T051 – Implement validate_mission_paths()

**Purpose**: Core path validation logic.

**Steps**:
1. Add validation function:
   ```python
   def validate_mission_paths(
       mission: Mission,
       project_root: Path,
       strict: bool = False
   ) -> PathValidationResult:
       """Validate project structure matches mission path conventions.

       Args:
           mission: Active mission with path conventions
           project_root: Project root directory
           strict: If True, missing paths are errors. If False, warnings only.

       Returns:
           Validation result

       Raises:
           PathValidationError: If strict=True and paths missing
       """
       required_paths = mission.config.paths
       existing = []
       missing = []
       warnings = []
       suggestions = []

       for key, path_str in required_paths.items():
           # Convert relative path to absolute
           full_path = project_root / path_str

           if full_path.exists():
               existing.append(path_str)
           else:
               missing.append(path_str)

               # Generate warning message
               warning_msg = (
                   f"Mission expects {key} directory: {path_str} (not found)"
               )
               warnings.append(warning_msg)

               # Generate suggestion
               if path_str.endswith('/'):
                   suggestion = f"Create directory: mkdir -p {path_str}"
               else:
                   suggestion = f"Create file or directory: {path_str}"
               suggestions.append(suggestion)

       result = PathValidationResult(
           mission_name=mission.name,
           required_paths=required_paths,
           existing_paths=existing,
           missing_paths=missing,
           warnings=warnings,
           suggestions=suggestions
       )

       # In strict mode, raise error if paths missing
       if strict and not result.is_valid:
           raise PathValidationError(
               f"Missing required directories for {mission.name}:\n"
               f"{result.format_errors()}"
           )

       return result
   ```

2. Test with various scenarios (all paths exist, some missing, none exist)

**Files**: `src/specify_cli/validators/paths.py`

**Parallel?**: No (core logic)

**Notes**: Progressive enforcement via strict parameter. Warnings educate, errors enforce.

---

### Subtask T052 – Implement suggest_directory_creation()

**Purpose**: Generate helpful fix suggestions.

**Steps**:
1. Add helper function:
   ```python
   def suggest_directory_creation(missing_paths: List[str]) -> List[str]:
       """Generate suggestions for creating missing directories.

       Args:
           missing_paths: List of missing path strings

       Returns:
           List of suggested commands
       """
       suggestions = []

       for path_str in missing_paths:
           # For directories (end with /)
           if path_str.endswith('/'):
               suggestions.append(f"mkdir -p {path_str}")
           # For files
           elif '.' in Path(path_str).name:
               parent = str(Path(path_str).parent)
               if parent and parent != '.':
                   suggestions.append(f"mkdir -p {parent} && touch {path_str}")
               else:
                   suggestions.append(f"touch {path_str}")
           # For directories without trailing slash
           else:
               suggestions.append(f"mkdir -p {path_str}")

       # Add combined suggestion if multiple paths
       if len(missing_paths) > 1:
           mkdir_paths = [p for p in missing_paths if p.endswith('/')]
           if len(mkdir_paths) > 1:
               suggestions.insert(0, f"Create all directories: mkdir -p {' '.join(mkdir_paths)}")

       return suggestions
   ```

2. Test suggestion generation:
   ```python
   def test_suggest_directory_creation():
       suggestions = suggest_directory_creation(["src/", "tests/", "docs/"])
       assert any("mkdir -p src/ tests/ docs/" in s for s in suggestions)
       assert any("mkdir -p src/" in s for s in suggestions)
   ```

**Files**: `src/specify_cli/validators/paths.py`

**Parallel?**: Yes (helper function, independent)

**Notes**: Suggestions must be actionable shell commands.

---

### Subtask T053 – Write unit tests for path validation

**Purpose**: Comprehensive test coverage for path validators.

**Steps**:
1. Add tests to `tests/unit/test_validators.py`:
   ```python
   from specify_cli.validators.paths import (
       validate_mission_paths,
       suggest_directory_creation,
       PathValidationError
   )
   from specify_cli.mission import Mission

   def test_validate_paths_all_exist(tmp_path):
       """Should pass when all paths exist."""
       # Create mock mission with path requirements
       # Create all directories
       # Validate → should have no warnings

   def test_validate_paths_some_missing(tmp_path):
       """Should warn when paths missing (non-strict)."""
       # Create partial directory structure
       # Validate with strict=False
       # Should have warnings but not raise error

   def test_validate_paths_strict_mode(tmp_path):
       """Should raise error in strict mode."""
       # Create partial structure
       # Validate with strict=True
       # Should raise PathValidationError

   def test_path_suggestions_generated():
       """Should generate mkdir suggestions."""
       result = suggest_directory_creation(["src/", "tests/"])
       assert any("mkdir" in s for s in result)
       assert any("src/" in s for s in result)

   def test_format_warnings_output():
       """Should format warnings clearly."""
       result = PathValidationResult(
           mission_name="Test",
           required_paths={"workspace": "src/"},
           existing_paths=[],
           missing_paths=["src/"],
           warnings=["Mission expects workspace: src/ (not found)"],
           suggestions=["mkdir -p src/"]
       )
       output = result.format_warnings()
       assert "Warnings:" in output
       assert "Suggestions:" in output
       assert "mkdir" in output
   ```

2. Run tests: `pytest tests/unit/test_validators.py -k path`

**Files**: `tests/unit/test_validators.py`

**Parallel?**: Yes (can write while functions are implemented)

**Notes**: Test both strict and non-strict modes thoroughly.

---

### Subtask T054 – Integrate into mission switch (warnings)

**Purpose**: Add path validation to mission switch command (non-blocking warnings).

**Steps**:
1. Open `src/specify_cli/cli/commands/mission.py` (from WP03)
2. Add path validation to switch_cmd() (after validation, before confirmation):
   ```python
   # After existing validation (worktrees, git clean, target exists)
   # Before confirmation

   # 5. Check path conventions (warnings only)
   path_result = validate_mission_paths(
       target_mission,
       project_root,
       strict=False  # Non-blocking at switch
   )

   if not path_result.is_valid:
       console.print(f"\n[yellow]Path Convention Warnings:[/yellow]")
       console.print(path_result.format_warnings())
       console.print("\n[dim]You can create these directories after switching.[/dim]")
       warnings.extend(path_result.warnings)
   ```

3. Update warnings list to include path warnings
4. Test: Switch to mission without creating expected directories, verify warnings shown

**Files**: `src/specify_cli/cli/commands/mission.py`

**Parallel?**: No (modifies WP03 code)

**Notes**: Import validate_mission_paths at top of file. Warnings inform but don't block.

---

### Subtask T055 – Integrate into acceptance (errors)

**Purpose**: Add path validation to acceptance workflow (blocking errors).

**Steps**:
1. Open `src/specify_cli/acceptance.py`
2. Locate `check_feature_acceptance()` or similar function that performs 7-point check
3. Add path validation as 8th check:
   ```python
   from specify_cli.validators.paths import validate_mission_paths, PathValidationError
   from specify_cli.mission import get_active_mission

   # In acceptance checking logic
   def check_feature_acceptance(...):
       # ... existing checks ...

       # 8. Path convention validation
       try:
           mission = get_active_mission(repo_root)
           path_result = validate_mission_paths(
               mission,
               repo_root,
               strict=True  # Blocking at acceptance
           )

           if not path_result.is_valid:
               issues.append("path_validation_failed")
               # Error details already in PathValidationError
       except PathValidationError as e:
           # Add to acceptance errors
           errors.append(str(e))
   ```

4. Update AcceptanceSummary.ok property to include path validation
5. Test: Run acceptance without required directories, verify blocked

**Files**: `src/specify_cli/acceptance.py`

**Parallel?**: No (modifies core acceptance logic)

**Notes**: Careful integration - acceptance.py is complex. Add path check alongside existing 7 checks.

---

### Subtask T056 – Update acceptance.py readiness check

**Purpose**: Ensure path validation appears in 7-point (now 8-point) readiness check.

**Steps**:
1. Locate AcceptanceSummary class in acceptance.py
2. Update `ok` property to include path validation:
   ```python
   @property
   def ok(self) -> bool:
       return (
           self.all_done
           and not self.metadata_issues
           and not self.activity_issues
           and not self.unchecked_tasks
           and not self.needs_clarification
           and not self.missing_artifacts
           and not self.git_dirty
           and not self.path_violations  # NEW - add this line
       )
   ```

3. Add path_violations field to AcceptanceSummary dataclass:
   ```python
   @dataclass
   class AcceptanceSummary:
       # ... existing fields ...
       path_violations: List[str]  # NEW field
   ```

4. Update outstanding() method to include path violations
5. Update acceptance report to display path issues if any
6. Test acceptance workflow with missing paths

**Files**: `src/specify_cli/acceptance.py`

**Parallel?**: No (extends T055)

**Notes**: This makes path validation visible in acceptance summary. Follow existing pattern for other checks.

---

## Test Strategy

**Unit Testing (T053)**:

1. **Validation Function Tests**:
   ```python
   def test_all_paths_exist(tmp_path):
       # Create all required directories
       (tmp_path / "src").mkdir()
       (tmp_path / "tests").mkdir()

       # Create mock mission
       # Validate → should pass

   def test_some_paths_missing_non_strict(tmp_path):
       # Create some directories
       # Validate with strict=False
       # Should return warnings, not raise

   def test_some_paths_missing_strict(tmp_path):
       # Create partial structure
       # Validate with strict=True
       # Should raise PathValidationError

   def test_suggestions_generated():
       # Missing paths
       # Should generate mkdir commands

   def test_format_warnings_vs_errors():
       # Same result
       # format_warnings() vs format_errors()
       # Different severity messaging
   ```

2. **Integration Point Tests**:
   ```python
   def test_mission_switch_shows_path_warnings():
       # Switch to mission
       # Missing paths
       # Verify warnings shown but switch succeeds

   def test_acceptance_blocks_on_missing_paths():
       # Run acceptance
       # Missing paths
       # Verify blocked with error
   ```

**Integration Testing** (in WP10):
- End-to-end path validation in mission switch
- End-to-end path validation in acceptance workflow

**Manual Testing**:
```bash
# Test non-strict (mission switch)
spec-kitty init test-project --mission software-dev
cd test-project
# Don't create src/ or tests/
spec-kitty mission switch research
# Should show warnings but allow switch

# Test strict (acceptance)
# Create feature without required directories
# Run /spec-kitty.accept
# Should block with path errors
```

---

## Risks & Mitigations

**Risk 1**: False positives on case-insensitive filesystems
- **Mitigation**: Use Path.resolve() for canonical comparison, test on macOS (case-insensitive)

**Risk 2**: Validation too strict, blocks legitimate workflows
- **Mitigation**: Non-strict at switch gives users time to create directories

**Risk 3**: Mission defines unusual paths, validation fails
- **Mitigation**: Support arbitrary paths in mission.yaml, just check existence

**Risk 4**: Performance impact on acceptance (many path checks)
- **Mitigation**: Path.exists() is fast, minimal overhead

**Risk 5**: Acceptance becomes too complex (8 checks instead of 7)
- **Mitigation**: Keep path check simple, follow existing check pattern

---

## Definition of Done Checklist

- [ ] `src/specify_cli/validators/paths.py` created
- [ ] PathValidationResult dataclass defined
- [ ] `validate_mission_paths()` implemented with strict/non-strict modes
- [ ] `suggest_directory_creation()` helper implemented
- [ ] Unit tests in `tests/unit/test_validators.py` pass
- [ ] Test coverage >90% for path validators
- [ ] Integration into mission switch complete (warnings)
- [ ] Integration into acceptance workflow complete (errors)
- [ ] AcceptanceSummary.ok property includes path validation
- [ ] Acceptance report displays path issues
- [ ] Manual testing passed (warnings at switch, errors at acceptance)

---

## Review Guidance

**Critical Checkpoints**:
1. Progressive enforcement must work (warnings at switch, errors at acceptance)
2. Suggestions must be actionable shell commands
3. Path validation must not break existing workflows
4. Acceptance check must include path validation
5. Error messages must be clear and helpful

**What Reviewers Should Verify**:
- Create project without src/ → switch missions → verify warnings shown
- Same project → run acceptance → verify blocked with errors
- Follow suggestions → create directories → run acceptance → should pass
- Check AcceptanceSummary.ok logic → path_violations included
- Test with software-dev paths (src/, tests/) and research paths (research/, data/)

**Acceptance Criteria from Spec**:
- User Story 5, Scenarios 1-5 satisfied
- FR-020 through FR-023 implemented
- SC-012, SC-013 achieved

---

## Activity Log

- 2025-01-16T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-11-16T13:27:49Z – codex – shell_pid=5621 – lane=doing – Started implementation
- 2025-11-16T13:34:52Z – codex – shell_pid=5621 – lane=doing – Completed implementation
- 2025-11-16T13:35:14Z – codex – shell_pid=5621 – lane=for_review – Ready for review
- 2025-11-16T13:54:51Z – codex – shell_pid=60030 – lane=doing – Started implementation
- 2025-11-16T13:56:51Z – codex – shell_pid=60030 – lane=for_review – Review in progress
- 2025-11-16T13:57:41Z – codex – shell_pid=60030 – lane=done – Approved without changes
- 2025-11-16T13:56:51Z – codex – shell_pid=60030 – lane=for_review – Review in progress
- 2025-11-16T13:57:54Z – codex – shell_pid=60030 – lane=done – Approved without changes

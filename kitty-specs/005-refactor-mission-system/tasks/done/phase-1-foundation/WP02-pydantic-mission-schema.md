---
work_package_id: "WP02"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
title: "Pydantic Mission Schema Validation"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "70190"
history:
  - timestamp: "2025-01-16T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Pydantic Mission Schema Validation

## Objectives & Success Criteria

**Goal**: Add Pydantic v2 schema validation to `src/specify_cli/mission.py`, catching mission.yaml typos and structural errors with clear field-level error messages.

**Success Criteria**:
- Pydantic models defined for all mission.yaml sections
- Mission loading validates against schema and raises ValidationError for issues
- Typo like `validaton:` caught with clear error listing valid fields
- Missing required fields identified immediately
- Type errors (version: 1 instead of "1.0.0") handled gracefully
- Existing software-dev and research missions load successfully (backwards compatible)
- All 9 subtasks (T008-T016) completed

## Context & Constraints

**Problem Statement**: Current `mission.py` uses `.get()` with empty defaults, causing silent failures:
```python
# Current code (line 166)
def get_validation_checks(self) -> List[str]:
    return self.config.get("validation", {}).get("checks", [])
```

If user types `validaton:` instead of `validation:`, checks silently return `[]` - no error raised.

**Supporting Documents**:
- Spec: `kitty-specs/005-refactor-mission-system/spec.md` (User Story 2, FR-004 through FR-007)
- Research: `kitty-specs/005-refactor-mission-system/research.md` (R1: Schema validation library comparison - Pydantic selected)
- Data Model: `kitty-specs/005-refactor-mission-system/data-model.md` (Complete Pydantic model definitions)

**Design Decisions from Research**:
- **Library**: Pydantic v2 (superior error messages justify 5MB dependency)
- **Strategy**: extra="forbid" to catch typos
- **Compatibility**: Coerce types where reasonable (version: 1 → "1"), error otherwise
- **Error Formatting**: Field-level details with suggestions

**Existing Code to Preserve**:
- Mission class API (properties, methods)
- Function signatures (get_active_mission, etc.)
- Error types (MissionError, MissionNotFoundError)

## Subtasks & Detailed Guidance

### Subtask T008 – Add Pydantic dependency

**Purpose**: Install Pydantic v2 for schema validation.

**Steps**:
1. Locate dependency file: Check if project uses `pyproject.toml`, `requirements.txt`, or `setup.py`
2. Add Pydantic:
   - If `pyproject.toml`: Add to `dependencies = ["pydantic>=2.0"]`
   - If `requirements.txt`: Add line `pydantic>=2.0`
3. Install locally: `pip install pydantic>=2.0`
4. Verify installation: `python -c "import pydantic; print(pydantic.__version__)"`

**Files**: `pyproject.toml` or `requirements.txt`

**Parallel?**: No (required by all other subtasks)

**Notes**: Check existing dependencies first. Pydantic v2 requires Python 3.7+, we're on 3.11+ so compatible.

---

### Subtask T009 – Create component Pydantic models

**Purpose**: Define models for nested mission.yaml sections.

**Steps**:
1. Add imports to mission.py:
   ```python
   from pydantic import BaseModel, Field
   from typing import Literal, List, Dict, Optional
   ```

2. Define models (add after MissionError classes, before Mission class):
   ```python
   class PhaseConfig(BaseModel):
       """Workflow phase definition."""
       name: str = Field(..., description="Phase identifier")
       description: str = Field(..., description="Phase description")

       class Config:
           extra = "forbid"

   class ArtifactsConfig(BaseModel):
       """Required and optional artifacts."""
       required: List[str] = Field(default_factory=list)
       optional: List[str] = Field(default_factory=list)

       class Config:
           extra = "forbid"

   class ValidationConfig(BaseModel):
       """Validation rules."""
       checks: List[str] = Field(default_factory=list)
       custom_validators: bool = Field(default=False)

       class Config:
           extra = "forbid"
   ```

**Files**: `src/specify_cli/mission.py`

**Parallel?**: Yes (can work on different models simultaneously)

**Notes**: Start with simple models. Reference data-model.md for complete definitions.

---

### Subtask T010 – Create additional Pydantic models

**Purpose**: Define remaining nested models.

**Steps**:
1. Add models to mission.py:
   ```python
   class WorkflowConfig(BaseModel):
       """Workflow configuration."""
       phases: List[PhaseConfig] = Field(..., min_length=1)

       class Config:
           extra = "forbid"

   class MCPToolsConfig(BaseModel):
       """MCP tools configuration."""
       required: List[str] = Field(default_factory=list)
       recommended: List[str] = Field(default_factory=list)
       optional: List[str] = Field(default_factory=list)

       class Config:
           extra = "forbid"

   class CommandConfig(BaseModel):
       """Command customization."""
       prompt: str = Field(...)

       class Config:
           extra = "forbid"

   class TaskMetadataConfig(BaseModel):
       """Task metadata fields."""
       required: List[str] = Field(default_factory=list)
       optional: List[str] = Field(default_factory=list)

       class Config:
           extra = "forbid"
   ```

**Files**: `src/specify_cli/mission.py`

**Parallel?**: Yes (independent models)

**Notes**: Use data-model.md as reference for complete model definitions.

---

### Subtask T011 – Create root MissionConfig model

**Purpose**: Define top-level mission configuration model.

**Steps**:
1. Add MissionConfig model to mission.py:
   ```python
   class MissionConfig(BaseModel):
       """Complete mission configuration schema."""

       # Required fields
       name: str = Field(...)
       description: str = Field(...)
       version: str = Field(..., pattern=r'^\d+\.\d+\.\d+$')
       domain: Literal["software", "research", "writing", "seo", "other"] = Field(...)

       # Workflow configuration (required)
       workflow: WorkflowConfig = Field(...)

       # Artifacts configuration (required)
       artifacts: ArtifactsConfig = Field(...)

       # Path conventions (optional, default to empty dict)
       paths: Dict[str, str] = Field(default_factory=dict)

       # Validation (optional, defaults)
       validation: ValidationConfig = Field(default_factory=ValidationConfig)

       # MCP tools (optional)
       mcp_tools: Optional[MCPToolsConfig] = None

       # Agent context (optional)
       agent_context: Optional[str] = None

       # Task metadata (optional)
       task_metadata: Optional[TaskMetadataConfig] = None

       # Commands (optional)
       commands: Optional[Dict[str, CommandConfig]] = None

       class Config:
           extra = "forbid"  # Critical - catches typos
   ```

**Files**: `src/specify_cli/mission.py`

**Parallel?**: No (depends on T009-T010)

**Notes**: This is the root model - all nested models must be defined first.

---

### Subtask T012 – Write unit tests for valid configs

**Purpose**: Test that valid mission.yaml files load successfully.

**Steps**:
1. Create test file: `tests/unit/test_mission_schema.py`
2. Add test cases for valid configurations:
   ```python
   import pytest
   from specify_cli.mission import MissionConfig

   def test_minimal_valid_config():
       """Minimal valid mission config should load."""
       data = {
           "name": "Test Mission",
           "description": "Test description",
           "version": "1.0.0",
           "domain": "software",
           "workflow": {
               "phases": [
                   {"name": "design", "description": "Design phase"}
               ]
           },
           "artifacts": {
               "required": ["spec.md"]
           }
       }
       config = MissionConfig(**data)
       assert config.name == "Test Mission"
       assert config.domain == "software"

   def test_software_dev_mission_loads():
       """Existing software-dev mission.yaml should load."""
       # Load actual software-dev mission.yaml
       # Verify it passes Pydantic validation

   def test_research_mission_loads():
       """Existing research mission.yaml should load."""
       # Load actual research mission.yaml
       # Verify it passes Pydantic validation
   ```

**Files**: `tests/unit/test_mission_schema.py` (new)

**Parallel?**: Yes (can write while T009-T011 are being implemented)

**Notes**: Use actual mission.yaml files from `.kittify/missions/` for real-world validation.

---

### Subtask T013 – Write unit tests for invalid configs

**Purpose**: Verify Pydantic catches errors with clear messages.

**Steps**:
1. Add test cases to test_mission_schema.py:
   ```python
   from pydantic import ValidationError

   def test_missing_required_field_name():
       """Missing 'name' should raise validation error."""
       data = {"domain": "software", "version": "1.0.0"}
       with pytest.raises(ValidationError) as exc_info:
           MissionConfig(**data)
       assert "name" in str(exc_info.value)
       assert "required" in str(exc_info.value).lower()

   def test_typo_in_field_name():
       """Typo 'validaton' should raise extra field error."""
       data = {
           "name": "Test",
           "domain": "software",
           "version": "1.0.0",
           "workflow": {"phases": [{"name": "test", "description": "test"}]},
           "artifacts": {},
           "validaton": {"checks": ["git_clean"]}  # Typo!
       }
       with pytest.raises(ValidationError) as exc_info:
           MissionConfig(**data)
       assert "validaton" in str(exc_info.value)
       assert "extra" in str(exc_info.value).lower()

   def test_invalid_domain_value():
       """Invalid domain should list valid options."""
       data = {
           "name": "Test",
           "domain": "invalid",  # Not in enum
           "version": "1.0.0",
           "workflow": {"phases": [{"name": "test", "description": "test"}]},
           "artifacts": {}
       }
       with pytest.raises(ValidationError) as exc_info:
           MissionConfig(**data)
       # Should mention valid options: software, research, writing, seo, other

   def test_invalid_version_format():
       """Version must match semver pattern."""
       data = {
           "name": "Test",
           "domain": "software",
           "version": "1.0",  # Missing patch version
           "workflow": {"phases": [{"name": "test", "description": "test"}]},
           "artifacts": {}
       }
       with pytest.raises(ValidationError) as exc_info:
           MissionConfig(**data)
       assert "pattern" in str(exc_info.value).lower()
   ```

**Files**: `tests/unit/test_mission_schema.py`

**Parallel?**: Yes (independent from T012)

**Notes**: These tests define critical error detection behavior. Be thorough.

---

### Subtask T014 – Update Mission.__init__ with Pydantic validation

**Purpose**: Replace dict-based config loading with Pydantic validation.

**Steps**:
1. Locate Mission._load_config() method (current line ~43)
2. Update to use Pydantic:
   ```python
   def _load_config(self) -> MissionConfig:  # Changed return type
       """Load mission configuration from mission.yaml.

       Returns:
           Validated MissionConfig object

       Raises:
           MissionNotFoundError: If mission.yaml doesn't exist
           MissionError: If mission.yaml is invalid
       """
       config_file = self.path / "mission.yaml"

       if not config_file.exists():
           raise MissionNotFoundError(
               f"Mission config not found: {config_file}\n"
               f"Expected mission.yaml in mission directory"
           )

       with open(config_file, 'r') as f:
           try:
               raw_data = yaml.safe_load(f)
           except yaml.YAMLError as e:
               raise MissionError(f"Invalid YAML syntax: {e}")

       # Pydantic validation
       try:
           return MissionConfig(**raw_data)
       except ValidationError as e:
           # Format error nicely (T015 handles this)
           raise MissionError(f"Invalid mission configuration: {e}")
   ```

3. Update type hint: `self.config: MissionConfig`

**Files**: `src/specify_cli/mission.py` (modify _load_config method)

**Parallel?**: No (core integration point)

**Notes**: Error formatting enhanced in T015. This subtask just integrates Pydantic.

---

### Subtask T015 – Add error formatting for ValidationError

**Purpose**: Make Pydantic validation errors user-friendly.

**Steps**:
1. Update MissionError raising in _load_config():
   ```python
   except ValidationError as e:
       # Format Pydantic errors nicely
       error_details = []
       for error in e.errors():
           field_path = " → ".join(str(x) for x in error['loc'])
           message = error['msg']
           error_type = error['type']

           error_details.append(f"  Field: {field_path}")
           error_details.append(f"  Issue: {message}")

           # Add suggestions for common errors
           if error_type == "missing":
               error_details.append(f"  Fix: Add '{field_path}' to mission.yaml")
           elif error_type == "extra_forbidden":
               error_details.append(f"  Fix: Remove '{field_path}' (unknown field, check spelling)")

           error_details.append("")

       raise MissionError(
           f"Invalid mission configuration in {config_file}:\n\n"
           + "\n".join(error_details) +
           "\nSee mission.yaml schema documentation for complete field list."
       )
   ```

2. Test error output manually with invalid mission.yaml

**Files**: `src/specify_cli/mission.py`

**Parallel?**: No (depends on T014)

**Notes**: Error messages are critical for UX. Make them actionable and clear.

---

### Subtask T016 – Test with existing missions

**Purpose**: Verify backwards compatibility with existing mission.yaml files.

**Steps**:
1. Load software-dev mission:
   ```python
   from pathlib import Path
   from specify_cli.mission import Mission

   mission_path = Path(".kittify/missions/software-dev")
   mission = Mission(mission_path)
   assert mission.name == "Software Dev Kitty"
   assert mission.domain == "software"
   assert len(mission.config.workflow.phases) == 5
   ```

2. Load research mission:
   ```python
   mission_path = Path(".kittify/missions/research")
   mission = Mission(mission_path)
   assert mission.name == "Deep Research Kitty"
   assert mission.domain == "research"
   assert "all_sources_documented" in mission.config.validation.checks
   ```

3. Verify no breaking changes to existing API:
   ```python
   # These should still work (properties unchanged)
   assert isinstance(mission.name, str)
   assert isinstance(mission.templates_dir, Path)
   assert isinstance(mission.get_validation_checks(), list)
   ```

4. Run existing mission-related tests: `pytest tests/ -k mission`

**Files**: Manual testing + existing test suites

**Parallel?**: No (final validation)

**Notes**: This is the backwards compatibility checkpoint. If this fails, schema is too strict.

---

## Test Strategy

**Test-First Approach**:

1. **Write tests first** (T012-T013): Define expected behavior
2. **Implement models** (T009-T011): Make tests pass
3. **Integrate** (T014-T015): Use models in Mission class
4. **Validate** (T016): Ensure no regressions

**Test Organization**:
```
tests/unit/test_mission_schema.py
├── Valid configs (T012)
│   ├── test_minimal_valid_config()
│   ├── test_software_dev_mission_loads()
│   ├── test_research_mission_loads()
│   ├── test_optional_fields_defaults()
│   └── test_all_fields_populated()
│
└── Invalid configs (T013)
    ├── test_missing_required_field_name()
    ├── test_missing_required_field_domain()
    ├── test_typo_in_field_name()
    ├── test_invalid_domain_value()
    ├── test_invalid_version_format()
    ├── test_empty_workflow_phases()
    └── test_invalid_phase_structure()
```

**Commands**:
- Run tests: `pytest tests/unit/test_mission_schema.py -v`
- Coverage: `pytest tests/unit/test_mission_schema.py --cov=src/specify_cli/mission`
- Specific test: `pytest tests/unit/test_mission_schema.py::test_typo_in_field_name -vv`

---

## Risks & Mitigations

**Risk 1**: Pydantic too strict, rejects valid missions
- **Mitigation**: Use optional fields with defaults, allow extra in paths dict, test with real missions

**Risk 2**: Breaking changes to existing custom missions
- **Mitigation**: Document migration guide, provide clear error messages, test with both built-in missions

**Risk 3**: Pydantic dependency rejected
- **Mitigation**: Research.md documents dataclasses fallback, but requires 2-3 extra days

**Risk 4**: Error messages too technical
- **Mitigation**: Add user-friendly formatting in T015, test with non-developers

**Risk 5**: Performance regression from validation
- **Mitigation**: Pydantic v2 is fast (Rust core), measure with existing benchmarks

---

## Definition of Done Checklist

- [ ] Pydantic v2 installed and importable
- [ ] All Pydantic models defined (Phase, Artifacts, Validation, Workflow, MCP, Command, TaskMetadata, MissionConfig)
- [ ] Mission._load_config() uses Pydantic validation
- [ ] MissionConfig type hint replaces Dict[str, Any]
- [ ] Error formatting provides field-level details with suggestions
- [ ] Unit tests pass for valid configs
- [ ] Unit tests pass for invalid configs (verify errors raised)
- [ ] Existing software-dev mission loads successfully
- [ ] Existing research mission loads successfully
- [ ] No breaking changes to Mission class API (properties work unchanged)
- [ ] Test coverage >95% for new validation code

---

## Review Guidance

**Critical Checkpoints**:
1. Load existing missions → should work without errors
2. Introduce typo in mission.yaml → should see clear Pydantic error
3. Missing required field → error lists field name and requirement
4. Invalid enum value → error lists valid options
5. Error messages include suggestions for fixing

**What Reviewers Should Verify**:
- Run `python -c "from specify_cli.mission import get_active_mission; m = get_active_mission(); print(m.name)"`
- Create test mission with typo, verify error quality
- Check test coverage report
- Verify no API breaking changes (existing code still works)

---

## Activity Log

- 2025-01-16T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-11-16T12:52:05Z – codex – shell_pid=56646 – lane=doing – Started implementation
- 2025-11-16T12:57:45Z – codex – shell_pid=56646 – lane=doing – Completed implementation
- 2025-11-16T12:58:03Z – codex – shell_pid=56646 – lane=for_review – Ready for review
- 2025-11-16T13:08:28Z – claude – shell_pid=70190 – lane=done – Code review complete: APPROVED. Excellent Pydantic integration with comprehensive schema validation. All 5 tests passing, both existing missions load correctly, typo detection works perfectly with helpful error messages listing valid fields. Error formatting is clear and actionable. Ready for use in WP03 and beyond.

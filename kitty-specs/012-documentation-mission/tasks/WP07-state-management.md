---
work_package_id: "WP07"
subtasks:
  - "T040"
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
title: "Iteration State Management"
phase: "Phase 1 - Core Logic"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "67096"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies:
  - "WP01"
  - "WP06"
history:
  - timestamp: "2026-01-12T17:18:56Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 – Iteration State Management

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## ⚠️ Dependency Rebase Guidance

**This WP depends on**:
- WP01 (Mission Infrastructure)
- WP06 (Gap Analysis) - Uses coverage_percentage from gap analysis

**Before starting work**:
1. Ensure WP01 is complete (mission exists)
2. Ensure WP06 is complete (gap analysis can generate coverage_percentage)

---

## Objectives & Success Criteria

**Goal**: Extend feature metadata (meta.json) to persist documentation mission state between iterations, enabling gap-filling workflows and tracking which Divio types and generators were used.

**Success Criteria**:
- `meta.json` schema extended with `documentation_state` field
- Iteration mode (initial, gap_filling, feature_specific) persisted
- Selected Divio types persisted as list
- Configured generators persisted with config paths
- Last audit date and coverage percentage persisted
- State read/write functions implemented
- Backward compatibility maintained (old features without documentation_state work)
- State persists correctly between documentation mission runs

## Context & Constraints

**Prerequisites**:
- Existing meta.json structure for features
- JSON serialization/deserialization
- Understanding of iteration modes from research

**Reference Documents**:
- [data-model.md](../data-model.md) - Iteration Mode entity (lines 409-459)
- [spec.md](../spec.md) - State management requirements (FR-002, FR-003, lines 101-102)
- [plan.md](../plan.md) - State management design (lines 232-236)
- [research.md](../research.md) - Cross-cutting findings on state persistence

**Constraints**:
- Must not break existing meta.json structure
- Must handle missing documentation_state field gracefully (backward compatibility)
- Must be JSON-serializable (no complex objects)
- State should be human-readable (for debugging)

**Current meta.json Structure**:
```json
{
  "feature_number": "012",
  "slug": "documentation-mission",
  "friendly_name": "Documentation Mission",
  "mission": "software-dev",
  "source_description": "...",
  "created_at": "2026-01-12T00:00:00Z"
}
```

**Extended Structure** (with documentation_state):
```json
{
  "feature_number": "012",
  "slug": "doc-project-name",
  "friendly_name": "Documentation: Project Name",
  "mission": "documentation",
  "source_description": "...",
  "created_at": "2026-01-12T00:00:00Z",
  "documentation_state": {
    "iteration_mode": "initial",
    "divio_types_selected": ["tutorial", "reference"],
    "generators_configured": [
      {
        "name": "sphinx",
        "language": "python",
        "config_path": "docs/conf.py"
      }
    ],
    "target_audience": "developers",
    "last_audit_date": null,
    "coverage_percentage": 0.0
  }
}
```

## Subtasks & Detailed Guidance

### Subtask T040 – Extend meta.json Schema

**Purpose**: Define the documentation_state schema and document its structure.

**Steps**:
1. Document the schema in a docstring or schema file:
   ```python
   """Documentation State Schema for meta.json

   The documentation_state field is added to feature meta.json files for
   documentation mission features. It persists state between iterations.

   Schema:
   {
       "documentation_state": {
           "iteration_mode": "initial" | "gap_filling" | "feature_specific",
           "divio_types_selected": ["tutorial", "how-to", "reference", "explanation"],
           "generators_configured": [
               {
                   "name": "sphinx" | "jsdoc" | "rustdoc",
                   "language": "python" | "javascript" | "typescript" | "rust",
                   "config_path": "relative/path/to/config.py"
               }
           ],
           "target_audience": "developers" | "end-users" | "contributors" | "operators",
           "last_audit_date": "2026-01-12T00:00:00Z" | null,
           "coverage_percentage": 0.75  # 0.0 to 1.0
       }
   }

   Fields:
   - iteration_mode: How this documentation mission was run
   - divio_types_selected: Which Divio types user chose to include
   - generators_configured: Which generators were set up and where
   - target_audience: Primary documentation audience
   - last_audit_date: When gap analysis last ran (null if never)
   - coverage_percentage: Overall doc coverage from most recent audit (0.0 if initial)
   """
   ```

2. Create TypedDict for type checking (optional):
   ```python
   from typing import TypedDict, List, Literal, Optional

   class GeneratorConfig(TypedDict):
       """Generator configuration entry."""
       name: Literal["sphinx", "jsdoc", "rustdoc"]
       language: str
       config_path: str

   class DocumentationState(TypedDict):
       """Documentation state schema for meta.json."""
       iteration_mode: Literal["initial", "gap_filling", "feature_specific"]
       divio_types_selected: List[str]
       generators_configured: List[GeneratorConfig]
       target_audience: str
       last_audit_date: Optional[str]  # ISO datetime or null
       coverage_percentage: float  # 0.0 to 1.0
   ```

**Files**: `src/specify_cli/gap_analysis.py` or create new `src/specify_cli/doc_state.py` module

**Parallel?**: Yes (can define schema while implementing read/write)

**Notes**:
- Schema is a nested JSON object
- All fields are optional (backward compatibility)
- Dates are ISO 8601 strings (JSON-serializable)
- Generators list can be empty (manual documentation only)

**Quality Validation**:
- Is schema well-documented?
- Are all fields necessary and sufficient?
- Is it JSON-serializable?

### Subtask T041 – Store iteration_mode

**Purpose**: Implement storage of iteration mode in meta.json.

**Steps**:
1. Create helper function to add/update iteration_mode:
   ```python
   def set_iteration_mode(
       meta_file: Path,
       iteration_mode: Literal["initial", "gap_filling", "feature_specific"]
   ) -> None:
       """Set iteration mode in feature meta.json.

       Args:
           meta_file: Path to meta.json
           iteration_mode: Iteration mode to store

       Raises:
           FileNotFoundError: If meta.json doesn't exist
           ValueError: If iteration_mode is invalid
       """
       valid_modes = {"initial", "gap_filling", "feature_specific"}
       if iteration_mode not in valid_modes:
           raise ValueError(f"Invalid iteration_mode: {iteration_mode}. Must be one of: {valid_modes}")

       # Read existing meta.json
       with open(meta_file, 'r') as f:
           meta = json.load(f)

       # Initialize documentation_state if not present
       if "documentation_state" not in meta:
           meta["documentation_state"] = {}

       # Set iteration mode
       meta["documentation_state"]["iteration_mode"] = iteration_mode

       # Write back
       with open(meta_file, 'w') as f:
           json.dump(meta, f, indent=2)
   ```

**Files**: `src/specify_cli/doc_state.py` (new module) or add to gap_analysis.py

**Parallel?**: Yes (can implement alongside other state setters)

**Notes**:
- Validates iteration_mode value
- Initializes documentation_state if missing (backward compat)
- Preserves existing meta.json fields
- Atomic write (read, modify, write)

**Quality Validation**:
- Does it validate iteration_mode values?
- Does it handle missing documentation_state field?
- Does it preserve other meta.json fields?
- Does it write valid JSON?

### Subtask T042 – Store divio_types_selected

**Purpose**: Implement storage of selected Divio types in meta.json.

**Steps**:
1. Create helper function:
   ```python
   def set_divio_types_selected(
       meta_file: Path,
       divio_types: List[str]
   ) -> None:
       """Set selected Divio types in feature meta.json.

       Args:
           meta_file: Path to meta.json
           divio_types: List of Divio types to store

       Raises:
           FileNotFoundError: If meta.json doesn't exist
           ValueError: If any type is invalid
       """
       valid_types = {"tutorial", "how-to", "reference", "explanation"}
       invalid_types = set(divio_types) - valid_types
       if invalid_types:
           raise ValueError(f"Invalid Divio types: {invalid_types}. Must be one of: {valid_types}")

       # Read existing meta.json
       with open(meta_file, 'r') as f:
           meta = json.load(f)

       # Initialize documentation_state if not present
       if "documentation_state" not in meta:
           meta["documentation_state"] = {}

       # Set Divio types
       meta["documentation_state"]["divio_types_selected"] = divio_types

       # Write back
       with open(meta_file, 'w') as f:
           json.dump(meta, f, indent=2)
   ```

**Files**: `src/specify_cli/doc_state.py` (modified)

**Parallel?**: Yes (can implement alongside other state setters)

**Notes**:
- Validates Divio type values
- Allows empty list (no Divio types selected)
- Allows subset (not all 4 types required)
- Stores as list for order preservation

**Quality Validation**:
- Does it validate Divio type values?
- Does it allow empty list?
- Does it allow subset of types?

### Subtask T043 – Store generators_configured

**Purpose**: Implement storage of configured generators in meta.json.

**Steps**:
1. Create helper function:
   ```python
   def set_generators_configured(
       meta_file: Path,
       generators: List[Dict[str, str]]
   ) -> None:
       """Set configured generators in feature meta.json.

       Args:
           meta_file: Path to meta.json
           generators: List of generator configs, each with:
               - name: Generator name (sphinx, jsdoc, rustdoc)
               - language: Language (python, javascript, rust)
               - config_path: Path to config file (relative to project root)

       Raises:
           FileNotFoundError: If meta.json doesn't exist
           ValueError: If generator config is invalid
       """
       # Validate generator configs
       valid_names = {"sphinx", "jsdoc", "rustdoc"}
       for gen in generators:
           if "name" not in gen:
               raise ValueError(f"Generator config missing 'name' field: {gen}")
           if gen["name"] not in valid_names:
               raise ValueError(f"Invalid generator name: {gen['name']}. Must be one of: {valid_names}")
           if "language" not in gen:
               raise ValueError(f"Generator config missing 'language' field: {gen}")
           if "config_path" not in gen:
               raise ValueError(f"Generator config missing 'config_path' field: {gen}")

       # Read existing meta.json
       with open(meta_file, 'r') as f:
           meta = json.load(f)

       # Initialize documentation_state if not present
       if "documentation_state" not in meta:
           meta["documentation_state"] = {}

       # Set generators
       meta["documentation_state"]["generators_configured"] = generators

       # Write back
       with open(meta_file, 'w') as f:
           json.dump(meta, f, indent=2)
   ```

**Files**: `src/specify_cli/doc_state.py` (modified)

**Parallel?**: Yes (can implement alongside other state setters)

**Notes**:
- Validates required fields (name, language, config_path)
- Allows empty list (manual documentation only)
- Allows multiple generators (polyglot projects)
- Config paths are relative to project root

**Quality Validation**:
- Does it validate generator config structure?
- Does it validate generator names?
- Does it allow empty list?
- Does it allow multiple generators?

### Subtask T044 – Store Audit Metadata

**Purpose**: Implement storage of last_audit_date and coverage_percentage in meta.json.

**Steps**:
1. Create helper function for audit metadata:
   ```python
   def set_audit_metadata(
       meta_file: Path,
       last_audit_date: Optional[datetime],
       coverage_percentage: float
   ) -> None:
       """Set audit metadata in feature meta.json.

       Args:
           meta_file: Path to meta.json
           last_audit_date: When gap analysis last ran (None if never)
           coverage_percentage: Overall doc coverage (0.0 to 1.0)

       Raises:
           FileNotFoundError: If meta.json doesn't exist
           ValueError: If coverage_percentage is out of range
       """
       if not (0.0 <= coverage_percentage <= 1.0):
           raise ValueError(f"coverage_percentage must be 0.0-1.0, got {coverage_percentage}")

       # Read existing meta.json
       with open(meta_file, 'r') as f:
           meta = json.load(f)

       # Initialize documentation_state if not present
       if "documentation_state" not in meta:
           meta["documentation_state"] = {}

       # Set audit metadata
       meta["documentation_state"]["last_audit_date"] = (
           last_audit_date.isoformat() if last_audit_date else None
       )
       meta["documentation_state"]["coverage_percentage"] = coverage_percentage

       # Write back
       with open(meta_file, 'w') as f:
           json.dump(meta, f, indent=2)
   ```

2. Integration with gap analysis:
   ```python
   def update_state_from_gap_analysis(
       meta_file: Path,
       analysis: GapAnalysis
   ) -> None:
       """Update meta.json state from gap analysis results.

       Args:
           meta_file: Path to meta.json
           analysis: Gap analysis results
       """
       set_audit_metadata(
           meta_file,
           analysis.analysis_date,
           analysis.coverage_matrix.get_coverage_percentage()
       )
   ```

**Files**: `src/specify_cli/doc_state.py` (modified)

**Parallel?**: Yes (can implement alongside other state setters)

**Notes**:
- Audit date stored as ISO 8601 string (JSON-serializable)
- Coverage percentage is 0.0 to 1.0 (not percentage)
- Null audit date indicates no gap analysis run yet
- Integration function updates state from GapAnalysis object

**Quality Validation**:
- Does it validate coverage_percentage range?
- Does it handle None audit date?
- Does it serialize datetime to ISO string?
- Does integration function update both fields?

### Subtask T045 – Implement State Read/Write Functions

**Purpose**: Implement comprehensive functions to read and write complete documentation state.

**Steps**:
1. Implement read function:
   ```python
   def read_documentation_state(meta_file: Path) -> Optional[DocumentationState]:
       """Read documentation state from feature meta.json.

       Args:
           meta_file: Path to meta.json

       Returns:
           DocumentationState dict if present, None if not a documentation mission
           or if state is missing (backward compatibility)

       Raises:
           FileNotFoundError: If meta.json doesn't exist
           json.JSONDecodeError: If meta.json is invalid JSON
       """
       with open(meta_file, 'r') as f:
           meta = json.load(f)

       # Check if this is a documentation mission
       if meta.get("mission") != "documentation":
           return None

       # Get documentation_state (may be missing for old features)
       return meta.get("documentation_state")
   ```

2. Implement write function:
   ```python
   def write_documentation_state(
       meta_file: Path,
       state: DocumentationState
   ) -> None:
       """Write complete documentation state to feature meta.json.

       Args:
           meta_file: Path to meta.json
           state: Complete documentation state to write

       Raises:
           FileNotFoundError: If meta.json doesn't exist
           ValueError: If state is invalid
       """
       # Validate state structure
       required_fields = {
           "iteration_mode", "divio_types_selected", "generators_configured",
           "target_audience", "last_audit_date", "coverage_percentage"
       }
       missing_fields = required_fields - set(state.keys())
       if missing_fields:
           raise ValueError(f"State missing required fields: {missing_fields}")

       # Read existing meta.json
       with open(meta_file, 'r') as f:
           meta = json.load(f)

       # Update documentation_state
       meta["documentation_state"] = state

       # Write back
       with open(meta_file, 'w') as f:
           json.dump(meta, f, indent=2)
   ```

3. Implement initialization function:
   ```python
   def initialize_documentation_state(
       meta_file: Path,
       iteration_mode: str,
       divio_types: List[str],
       generators: List[Dict[str, str]],
       target_audience: str
   ) -> DocumentationState:
       """Initialize documentation state for a new documentation mission.

       Args:
           meta_file: Path to meta.json
           iteration_mode: initial, gap_filling, or feature_specific
           divio_types: Selected Divio types
           generators: Configured generators
           target_audience: Primary documentation audience

       Returns:
           Initialized DocumentationState

       Raises:
           FileNotFoundError: If meta.json doesn't exist
       """
       state: DocumentationState = {
           "iteration_mode": iteration_mode,
           "divio_types_selected": divio_types,
           "generators_configured": generators,
           "target_audience": target_audience,
           "last_audit_date": None,
           "coverage_percentage": 0.0
       }

       write_documentation_state(meta_file, state)
       return state
   ```

4. Implement update function:
   ```python
   def update_documentation_state(
       meta_file: Path,
       **updates
   ) -> DocumentationState:
       """Update specific fields in documentation state.

       Args:
           meta_file: Path to meta.json
           **updates: Fields to update (iteration_mode, divio_types_selected, etc.)

       Returns:
           Updated DocumentationState

       Raises:
           FileNotFoundError: If meta.json doesn't exist
           ValueError: If state doesn't exist (call initialize first)
       """
       # Read current state
       state = read_documentation_state(meta_file)

       if state is None:
           raise ValueError(
               f"No documentation state found in {meta_file}. "
               f"Call initialize_documentation_state() first."
           )

       # Update fields
       for key, value in updates.items():
           if key in state:
               state[key] = value

       # Write back
       write_documentation_state(meta_file, state)
       return state
   ```

**Files**: `src/specify_cli/doc_state.py` (modified)

**Parallel?**: No (ties together read/write logic)

**Notes**:
- read_documentation_state returns None for non-documentation missions (graceful)
- write_documentation_state validates required fields
- initialize_documentation_state creates state from scratch
- update_documentation_state allows partial updates
- All functions preserve other meta.json fields

**Quality Validation**:
- Does read return None for non-doc missions?
- Does write validate state structure?
- Does initialize create valid state?
- Does update preserve unchanged fields?

### Subtask T046 – Handle State Migration

**Purpose**: Ensure backward compatibility with features that don't have documentation_state field.

**Steps**:
1. Implement migration/upgrade function:
   ```python
   def ensure_documentation_state(meta_file: Path) -> None:
       """Ensure meta.json has documentation_state field.

       For backward compatibility with old documentation mission features.
       If feature is a documentation mission but lacks documentation_state,
       initialize with sensible defaults.

       Args:
           meta_file: Path to meta.json
       """
       with open(meta_file, 'r') as f:
           meta = json.load(f)

       # Check if documentation mission
       if meta.get("mission") != "documentation":
           return  # Not a documentation mission, nothing to do

       # Check if state already exists
       if "documentation_state" in meta:
           return  # Already has state

       # Initialize with defaults
       meta["documentation_state"] = {
           "iteration_mode": "initial",  # Assume first run
           "divio_types_selected": [],   # Unknown, user must specify
           "generators_configured": [],  # Unknown, user must configure
           "target_audience": "developers",  # Reasonable default
           "last_audit_date": None,
           "coverage_percentage": 0.0
       }

       # Write back
       with open(meta_file, 'w') as f:
           json.dump(meta, f, indent=2)
   ```

2. Add version check helper:
   ```python
   def get_state_version(state: DocumentationState) -> int:
       """Get state schema version for future migrations.

       Currently all states are version 1.

       Args:
           state: Documentation state

       Returns:
           Schema version number
       """
       return state.get("_schema_version", 1)
   ```

**Files**: `src/specify_cli/doc_state.py` (modified)

**Parallel?**: No (migration logic must be careful)

**Notes**:
- Migration only runs for documentation mission features
- Initializes with safe defaults
- Preserves all existing meta.json fields
- Future-proofed with _schema_version field (optional)

**Quality Validation**:
- Does it only touch documentation mission features?
- Does it preserve existing fields?
- Are defaults sensible?
- Does it handle already-migrated features gracefully?

## Test Strategy

**Unit Tests** (to be implemented in WP09):

1. Test state initialization:
   ```python
   def test_initialize_documentation_state(tmp_path):
       meta_file = tmp_path / "meta.json"
       meta_file.write_text(json.dumps({
           "feature_number": "001",
           "mission": "documentation"
       }))

       state = initialize_documentation_state(
           meta_file,
           iteration_mode="initial",
           divio_types=["tutorial", "reference"],
           generators=[{"name": "sphinx", "language": "python", "config_path": "docs/conf.py"}],
           target_audience="developers"
       )

       assert state["iteration_mode"] == "initial"
       assert state["divio_types_selected"] == ["tutorial", "reference"]
       assert len(state["generators_configured"]) == 1

       # Verify written to file
       with open(meta_file) as f:
           meta = json.load(f)
       assert "documentation_state" in meta
   ```

2. Test state reading:
   ```python
   def test_read_documentation_state(tmp_path):
       meta_file = tmp_path / "meta.json"
       meta_file.write_text(json.dumps({
           "mission": "documentation",
           "documentation_state": {
               "iteration_mode": "gap_filling",
               "divio_types_selected": ["tutorial"],
               "generators_configured": [],
               "target_audience": "end-users",
               "last_audit_date": "2026-01-12T00:00:00Z",
               "coverage_percentage": 0.5
           }
       }))

       state = read_documentation_state(meta_file)
       assert state is not None
       assert state["iteration_mode"] == "gap_filling"
       assert state["coverage_percentage"] == 0.5
   ```

3. Test state updates:
   ```python
   def test_update_documentation_state(tmp_path):
       meta_file = tmp_path / "meta.json"
       # Initialize
       initialize_documentation_state(
           meta_file,
           iteration_mode="initial",
           divio_types=[],
           generators=[],
           target_audience="developers"
       )

       # Update
       updated = update_documentation_state(
           meta_file,
           iteration_mode="gap_filling",
           coverage_percentage=0.75
       )

       assert updated["iteration_mode"] == "gap_filling"
       assert updated["coverage_percentage"] == 0.75
       assert updated["target_audience"] == "developers"  # Unchanged
   ```

4. Test backward compatibility:
   ```python
   def test_ensure_state_for_old_feature(tmp_path):
       # Old feature without documentation_state
       meta_file = tmp_path / "meta.json"
       meta_file.write_text(json.dumps({
           "feature_number": "001",
           "mission": "documentation",
           "created_at": "2025-01-01T00:00:00Z"
       }))

       ensure_documentation_state(meta_file)

       # Verify state was added
       with open(meta_file) as f:
           meta = json.load(f)
       assert "documentation_state" in meta
       assert meta["documentation_state"]["iteration_mode"] == "initial"
   ```

5. Test non-documentation missions unaffected:
   ```python
   def test_read_state_for_non_doc_mission(tmp_path):
       meta_file = tmp_path / "meta.json"
       meta_file.write_text(json.dumps({
           "mission": "software-dev"
       }))

       state = read_documentation_state(meta_file)
       assert state is None  # Not a documentation mission
   ```

**Manual Validation**:

1. Test state persistence:
   ```bash
   # Create test meta.json
   cat > /tmp/test-meta.json << EOF
   {
     "feature_number": "012",
     "mission": "documentation"
   }
   EOF

   # Test in Python
   python -c "
   from pathlib import Path
   from specify_cli.doc_state import initialize_documentation_state, read_documentation_state

   meta_file = Path('/tmp/test-meta.json')

   # Initialize
   state = initialize_documentation_state(
       meta_file,
       iteration_mode='initial',
       divio_types=['tutorial', 'reference'],
       generators=[{'name': 'sphinx', 'language': 'python', 'config_path': 'docs/conf.py'}],
       target_audience='developers'
   )
   print('✓ State initialized')

   # Read back
   read_state = read_documentation_state(meta_file)
   assert read_state == state
   print('✓ State persists correctly')
   "
   ```

2. Test JSON structure:
   ```bash
   cat /tmp/test-meta.json | python -m json.tool
   ```
   - Verify JSON is valid
   - Verify documentation_state field is present
   - Verify all subfields are present

3. Test backward compatibility:
   ```bash
   # Create old-style meta.json
   cat > /tmp/old-meta.json << EOF
   {
     "feature_number": "001",
     "mission": "documentation",
     "created_at": "2025-01-01T00:00:00Z"
   }
   EOF

   # Test migration
   python -c "
   from pathlib import Path
   from specify_cli.doc_state import ensure_documentation_state, read_documentation_state

   meta_file = Path('/tmp/old-meta.json')

   # Before migration
   state = read_documentation_state(meta_file)
   assert state is None
   print('✓ Old feature has no state')

   # Migrate
   ensure_documentation_state(meta_file)

   # After migration
   state = read_documentation_state(meta_file)
   assert state is not None
   assert state['iteration_mode'] == 'initial'
   print('✓ Migration added state with defaults')
   "
   ```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| JSON corruption | High - state lost | Validate JSON before writing, atomic write operations |
| Schema changes break old features | High - features stop working | Strict backward compatibility, migration function |
| State drift (meta.json vs actual docs) | Medium - stale audit date | Update state after each audit, validate on read |
| Invalid state values | Medium - unexpected behavior | Validate all values on write (iteration_mode, coverage_percentage, etc.) |
| Concurrent writes | Low - state corruption | Document that meta.json should not be edited concurrently |

## Definition of Done Checklist

- [ ] `src/specify_cli/doc_state.py` module created (or functions added to gap_analysis.py)
- [ ] `DocumentationState` TypedDict defined
- [ ] `GeneratorConfig` TypedDict defined
- [ ] Schema documented with all fields explained
- [ ] `set_iteration_mode()` function implemented:
  - [ ] Validates iteration_mode value
  - [ ] Initializes documentation_state if missing
  - [ ] Preserves other meta.json fields
- [ ] `set_divio_types_selected()` function implemented:
  - [ ] Validates Divio type values
  - [ ] Stores as list
  - [ ] Allows empty list and subsets
- [ ] `set_generators_configured()` function implemented:
  - [ ] Validates generator config structure
  - [ ] Allows empty list and multiple generators
  - [ ] Stores config_path relatively
- [ ] `set_audit_metadata()` function implemented:
  - [ ] Validates coverage_percentage range (0.0-1.0)
  - [ ] Handles None audit date
  - [ ] Serializes datetime to ISO string
- [ ] `read_documentation_state()` function implemented:
  - [ ] Returns None for non-documentation missions
  - [ ] Returns None if state missing (backward compat)
  - [ ] Returns state dict if present
- [ ] `write_documentation_state()` function implemented:
  - [ ] Validates required fields
  - [ ] Writes complete state
  - [ ] Preserves other meta.json fields
- [ ] `initialize_documentation_state()` function implemented:
  - [ ] Creates state from scratch
  - [ ] Validates inputs
  - [ ] Writes to meta.json
- [ ] `update_documentation_state()` function implemented:
  - [ ] Allows partial updates
  - [ ] Preserves unchanged fields
  - [ ] Validates updated values
- [ ] `ensure_documentation_state()` migration function implemented:
  - [ ] Only touches documentation missions
  - [ ] Adds state if missing
  - [ ] Uses sensible defaults
  - [ ] Handles already-migrated features
- [ ] Unit tests written (8 test functions)
- [ ] Manual testing completed
- [ ] Backward compatibility verified (old features without state work)
- [ ] `tasks.md` in feature directory updated with WP07 status

## Review Guidance

**Key Acceptance Checkpoints**:

1. **Schema Definition**: Complete, well-documented, JSON-serializable
2. **Validation**: All setters validate inputs
3. **Backward Compatibility**: Old features without state don't break
4. **State Persistence**: Write and read operations are symmetric
5. **Partial Updates**: Can update individual fields without replacing entire state
6. **Migration**: Old features can be upgraded gracefully

**Validation Commands**:
```bash
# Test module imports
python -c "from specify_cli.doc_state import DocumentationState, read_documentation_state, write_documentation_state, initialize_documentation_state, ensure_documentation_state; print('✓ All imports successful')"

# Test state operations (end-to-end)
python -c "
from pathlib import Path
import json
from specify_cli.doc_state import initialize_documentation_state, read_documentation_state, update_documentation_state

# Create test meta.json
meta = Path('/tmp/test-state-meta.json')
meta.write_text(json.dumps({'mission': 'documentation', 'feature_number': '001'}))

# Initialize
state = initialize_documentation_state(
    meta,
    iteration_mode='initial',
    divio_types=['tutorial'],
    generators=[{'name': 'sphinx', 'language': 'python', 'config_path': 'docs/conf.py'}],
    target_audience='developers'
)
print('✓ State initialized')

# Read
read_state = read_documentation_state(meta)
assert read_state == state
print('✓ State reads correctly')

# Update
updated = update_documentation_state(meta, coverage_percentage=0.5)
assert updated['coverage_percentage'] == 0.5
print('✓ State updates correctly')
"
```

**Review Focus Areas**:
- Schema is complete and well-documented
- Validation catches invalid values
- Read/write operations are symmetric (write then read returns same value)
- Backward compatibility works (old features without state)
- Migration adds state with sensible defaults
- State operations preserve other meta.json fields
- Error messages are clear and actionable

## Activity Log

- 2026-01-12T17:18:56Z – system – lane=planned – Prompt created.
- 2026-01-13T09:18:32Z – test-agent3 – lane=doing – Moved to doing
- 2026-01-13T10:47:27Z – test-agent3 – lane=planned – Reset to planned (was test activity)
- 2026-01-13T10:56:01Z – claude – shell_pid=64059 – lane=doing – Started implementation via workflow command
- 2026-01-13T10:58:52Z – claude – shell_pid=64059 – lane=for_review – Ready for review: Documentation state management complete. Implemented all state management functions (T040-T046): TypedDict schema, individual setters (iteration_mode, divio_types, generators, audit metadata), comprehensive read/write/initialize/update functions, and backward compatibility migration. All manual tests passing.
- 2026-01-13T11:01:16Z – claude – shell_pid=67096 – lane=doing – Started review via workflow command
- 2026-01-13T11:03:47Z – claude – shell_pid=67096 – lane=done – Review passed: All subtasks (T040-T046) implemented correctly. Comprehensive manual testing confirms: schema definition, individual setters with validation, read/write/initialize/update functions, backward compatibility, proper error handling. JSON formatting clean, all acceptance criteria met. Unit tests deferred to WP09 as planned.

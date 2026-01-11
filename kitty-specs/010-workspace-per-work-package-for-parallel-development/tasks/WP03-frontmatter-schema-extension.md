---
work_package_id: "WP03"
subtasks:
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "Frontmatter Schema Extension"
phase: "Phase 0 - Test Infrastructure"
lane: "done"
dependencies: ["WP01"]
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-07T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Frontmatter Schema Extension

**Implementation command:**
```bash
spec-kitty implement WP03 --base WP01
```

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if needed.]*

---

## Objectives & Success Criteria

**Primary Goal**: Extend WP frontmatter schema to include `dependencies: []` field, update field ordering, ensure backward compatibility with existing WP files.

**Success Criteria**:
- ✅ WP frontmatter schema includes `dependencies` field (optional, defaults to [])
- ✅ WP_FIELD_ORDER updated to include dependencies in correct position
- ✅ Validation ensures dependencies are list of strings matching WP## pattern
- ✅ Backward compatibility: WP files without dependencies field still parse correctly
- ✅ All tests pass

---

## Context & Constraints

**Why this matters**: The `dependencies` field is the canonical source of truth for WP relationships. Without it, the implement command cannot validate correct branching, and dependency warnings cannot be displayed.

**Reference Documents**:
- [plan.md](../plan.md) - Section 1.5: WP Frontmatter Schema Extension
- [data-model.md](../data-model.md) - WorkPackage entity definition
- [spec.md](../spec.md) - FR-011, FR-012 (WP prompt generation with dependencies)

**Current Schema** (in `src/specify_cli/frontmatter.py`):
```yaml
work_package_id: "WP01"
title: "Setup Infrastructure"
lane: "planned"
subtasks: ["T001", "T002"]
phase: "Phase 1"
assignee: ""
agent: ""
```

**Target Schema** (0.11.0):
```yaml
work_package_id: "WP01"
title: "Setup Infrastructure"
lane: "planned"
dependencies: []              # NEW FIELD
subtasks: ["T001", "T002"]
phase: "Phase 1"
assignee: ""
agent: ""
```

**Field Ordering**: dependencies should appear after `lane` and before `subtasks` for logical grouping (status fields first, then structural fields).

---

## Subtasks & Detailed Guidance

### Subtask T016 – Update WP frontmatter schema definition

**Purpose**: Add `dependencies` field to WP frontmatter data model in frontmatter.py.

**Steps**:
1. Open `src/specify_cli/frontmatter.py`
2. Locate WP frontmatter field definitions (likely in constants or dataclass)
3. Add `dependencies` field definition:
   - Type: `list[str]`
   - Default: `[]` (empty list)
   - Optional: True (existing WPs without this field should work)
4. Document field purpose in docstring: "List of WP IDs this WP depends on (e.g., ['WP01', 'WP02'])"

**Files**: `src/specify_cli/frontmatter.py`

**Parallel?**: No (single file modification)

**Example**:
```python
# In frontmatter.py
WP_FRONTMATTER_FIELDS = {
    "work_package_id": {"type": str, "required": True},
    "title": {"type": str, "required": True},
    "lane": {"type": str, "required": True},
    "dependencies": {"type": list, "required": False, "default": []},  # NEW
    "subtasks": {"type": list, "required": False, "default": []},
    "phase": {"type": str, "required": False},
    # ... other fields
}
```

---

### Subtask T017 – Make dependencies field optional with default

**Purpose**: Ensure backward compatibility - WP files without `dependencies:` field default to empty list.

**Steps**:
1. In frontmatter parsing logic, check if dependencies field exists
2. If missing, set default value: `frontmatter.get('dependencies', [])`
3. Ensure no errors when parsing old WP files (pre-0.11.0)

**Files**: `src/specify_cli/frontmatter.py` (parsing functions)

**Parallel?**: Part of T016 (same file)

**Example**:
```python
def parse_wp_frontmatter(wp_file: Path) -> dict:
    """Parse WP frontmatter with backward compatibility."""
    yaml = YAML()
    # ... parse frontmatter
    frontmatter = yaml.load(frontmatter_text)

    # Ensure dependencies field exists (backward compat)
    if 'dependencies' not in frontmatter:
        frontmatter['dependencies'] = []

    return frontmatter
```

---

### Subtask T018 – Update WP_FIELD_ORDER

**Purpose**: Define canonical field ordering for WP frontmatter to ensure consistent YAML output.

**Steps**:
1. Locate WP_FIELD_ORDER constant in `src/specify_cli/frontmatter.py`
2. Insert `dependencies` in logical position:
   - After: `lane` (status information)
   - Before: `subtasks` (structural information)
3. Update any functions that use WP_FIELD_ORDER for serialization

**Files**: `src/specify_cli/frontmatter.py`

**Parallel?**: No (same file as T016-T017)

**Example**:
```python
WP_FIELD_ORDER = [
    "work_package_id",
    "subtasks",
    "title",
    "phase",
    "lane",
    "dependencies",  # NEW - insert here
    "assignee",
    "agent",
    "shell_pid",
    "review_status",
    "reviewed_by",
    "history"
]
```

**Note**: This ordering determines how fields appear when WP frontmatter is written/updated.

---

### Subtask T019 – Add validation for dependencies field

**Purpose**: Validate dependencies field contains valid WP IDs, preventing malformed dependency declarations.

**Steps**:
1. Add validation function in frontmatter.py or use dependency_graph.py utilities
2. Validation rules:
   - Must be a list (not string or dict)
   - Each item must be string
   - Each item must match pattern `WP\d{2}` (e.g., WP01, WP02, not WP1 or WP001)
   - No duplicates (WP01 shouldn't appear twice)
3. Raise clear error if validation fails

**Files**: `src/specify_cli/frontmatter.py`

**Validation Logic**:
```python
import re

def validate_dependencies(deps: list) -> tuple[bool, list[str]]:
    """Validate dependencies field format."""
    errors = []

    if not isinstance(deps, list):
        errors.append("dependencies must be a list")
        return False, errors

    wp_pattern = re.compile(r'^WP\d{2}$')

    for dep in deps:
        if not isinstance(dep, str):
            errors.append(f"Dependency must be string, got {type(dep)}")
        elif not wp_pattern.match(dep):
            errors.append(f"Invalid WP ID format: {dep} (must be WP##)")

    # Check for duplicates
    if len(deps) != len(set(deps)):
        errors.append("Duplicate dependencies found")

    return len(errors) == 0, errors
```

**Parallel?**: No (builds on T016-T018)

---

### Subtask T020 – Test frontmatter parsing with dependencies

**Purpose**: Write tests to validate dependencies field parsing works correctly.

**Steps**:
1. Add test cases to existing frontmatter test file or create new test
2. Test scenarios:
   - Parse WP with empty dependencies
   - Parse WP with single dependency
   - Parse WP with multiple dependencies
   - Parse WP with invalid dependency format (should error)
   - Parse old WP without dependencies field (should default to [])

**Files**: `tests/specify_cli/test_frontmatter.py` (or create if doesn't exist)

**Example Test**:
```python
def test_parse_wp_with_dependencies(tmp_path):
    """Test parsing WP frontmatter with dependencies field."""
    wp_content = """---
work_package_id: WP02
title: Build API
lane: planned
dependencies:
  - WP01
---
# Content
"""
    wp_file = tmp_path / "WP02.md"
    wp_file.write_text(wp_content)

    frontmatter = parse_wp_frontmatter(wp_file)
    assert frontmatter["dependencies"] == ["WP01"]
```

**Parallel?**: Can run in parallel with T021 (different test scenarios)

---

### Subtask T021 – Test backward compatibility

**Purpose**: Ensure WP files from 0.10.x (without dependencies field) still parse correctly in 0.11.0.

**Steps**:
1. Create test WP file using old schema (no dependencies field)
2. Parse with new frontmatter code
3. Verify dependencies defaults to []
4. Verify no errors or warnings

**Files**: `tests/specify_cli/test_frontmatter.py`

**Example Test**:
```python
def test_backward_compat_no_dependencies(tmp_path):
    """Test parsing old WP files without dependencies field."""
    old_wp_content = """---
work_package_id: WP01
title: Legacy WP
lane: planned
subtasks:
  - T001
---
# Content
"""
    wp_file = tmp_path / "WP01.md"
    wp_file.write_text(old_wp_content)

    frontmatter = parse_wp_frontmatter(wp_file)
    assert "dependencies" in frontmatter
    assert frontmatter["dependencies"] == []  # Defaults to empty
```

**Parallel?**: Can run in parallel with T020

---

## Test Strategy

**Test file**: `tests/specify_cli/test_frontmatter.py` (or similar)

**Execution**:
```bash
pytest tests/specify_cli/test_frontmatter.py -v -k dependencies
```

**Coverage**: Validate all branches of validation logic, edge cases (invalid formats, missing field, etc.)

---

## Risks & Mitigations

**Risk**: Breaking existing WP files that lack dependencies field
- **Mitigation**: Optional field with default value, extensive backward compatibility testing

**Risk**: Invalid dependency values accepted (bad WP IDs)
- **Mitigation**: Strict validation with regex pattern matching

---

## Definition of Done Checklist

- [ ] Frontmatter schema updated with dependencies field (T016-T017)
- [ ] WP_FIELD_ORDER includes dependencies (T018)
- [ ] Validation logic implemented (T019)
- [ ] Tests written and passing (T020-T021)
- [ ] Backward compatibility verified
- [ ] No regressions in existing frontmatter parsing

---

## Review Guidance

**Reviewers should verify**:
1. dependencies field is truly optional (old WPs work without it)
2. Validation catches all invalid formats
3. Field ordering is logical and consistent
4. Tests cover all edge cases (empty list, invalid IDs, missing field)

---

## Activity Log

- 2026-01-07T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-08T09:25:20Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-08T09:29:45Z – unknown – lane=for_review – Implementation complete. Added dependencies field to frontmatter schema with validation, backward compatibility, and comprehensive tests. All 14 new tests pass, and existing tests remain passing.
- 2026-01-08T09:39:46Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T09:44:08Z – unknown – lane=doing – Addressed all review feedback: (1) Fixed dependencies injection to only apply to WP files (2) Corrected field order - dependencies now before subtasks (3) Added tests verifying correct ordering and scope restriction. All 16 tests pass.
- 2026-01-08T09:46:23Z – unknown – lane=for_review – Addressed all review feedback: (1) Fixed dependencies injection to WP files only (2) Corrected field order - dependencies before subtasks (3) Enhanced test coverage. All 16 tests pass.
- 2026-01-08T09:46:33Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T09:47:41Z – unknown – lane=done – Review passed

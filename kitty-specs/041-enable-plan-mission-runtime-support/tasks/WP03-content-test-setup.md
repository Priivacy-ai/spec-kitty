---
work_package_id: WP03
title: Content Templates & Test Setup
lane: planned
dependencies: []
subtasks: [T010, T011, T012]
description: Create any referenced content templates and set up the test framework
estimated_duration: 1-2 hours
priority: P1
---

# WP03: Content Templates & Test Setup

**Objective**: Create any content templates that were referenced by the command templates (from WP02), and establish the pytest test infrastructure for plan mission testing.

**Context**: WP02 identified whether any content templates are needed (T009). If references were found, this WP creates them. Additionally, we need to set up the pytest framework with fixtures and mocks so that WP04 can write comprehensive tests.

**Key Success Criterion**: Test infrastructure is ready, any content templates are created, and fixtures/mocks function correctly.

**Included Files**:
- `src/specify_cli/missions/plan/templates/*.md` (create if referenced)
- `tests/specify_cli/next/test_plan_mission_runtime.py` (create)
- Test fixtures and mocks (within test file)

---

## Subtask Breakdown

### Subtask T010: Create Content Templates (if referenced)
**Duration**: 20-30 minutes
**Goal**: Create any content templates that were identified in WP02 T009.

**Background**: Content templates are reusable structures that command templates can reference. For example, if research.md says "Use: ../templates/research-outline.md", then we need to create that file.

**Steps**:

1. **Review findings from WP02 T009**:
   - What content template references were found?
   - Which templates need to be created?

2. **For each referenced template**, create the file:
   ```bash
   touch src/specify_cli/missions/plan/templates/{template-name}.md
   ```

3. **Example Template Structures** (if needed):

   **research-outline.md** (if research.md references it):
   ```markdown
   # Research Document Template

   ## Technical Analysis

   ### Requirement 1: [Requirement Name]
   - Analysis: [What did you find?]
   - Feasibility: [Possible/Easy/Difficult/Not Possible]

   ### Requirement 2: [Requirement Name]
   - Analysis: [What did you find?]
   - Feasibility: [Possible/Easy/Difficult/Not Possible]

   ## Design Patterns

   ### Pattern 1: [Pattern Name]
   - Where used: [What component?]
   - Rationale: [Why this pattern?]
   - Example: [Code example or reference]

   ### Pattern 2: [Pattern Name]
   - Where used: [What component?]
   - Rationale: [Why this pattern?]
   - Example: [Code example or reference]

   ## Dependencies

   - [Dependency 1]: [Version/Details]
   - [Dependency 2]: [Version/Details]

   ## Risks & Mitigations

   | Risk | Mitigation |
   |------|-----------|
   | [Risk 1] | [How to mitigate] |
   | [Risk 2] | [How to mitigate] |

   ## Recommendations

   - [Recommendation 1]
   - [Recommendation 2]
   ```

   **design-checklist.md** (if plan.md references it):
   ```markdown
   # Design Validation Checklist

   ## Architecture
   - [ ] System design documented
   - [ ] Components identified
   - [ ] Component interactions defined
   - [ ] Deployment architecture clear

   ## Data Model
   - [ ] All entities identified
   - [ ] Entity relationships defined
   - [ ] Schema normalized
   - [ ] Validation rules documented

   ## API Design
   - [ ] All endpoints documented
   - [ ] Request/response shapes defined
   - [ ] Error handling specified
   - [ ] Rate limiting defined

   ## Implementation
   - [ ] Technology stack chosen
   - [ ] Build/deployment process defined
   - [ ] Testing strategy outlined
   - [ ] Rollout plan documented
   ```

   **validation-rubric.md** (if review.md references it):
   ```markdown
   # Design Validation Rubric

   ## Completeness

   - [ ] All requirements addressed
   - [ ] All user scenarios covered
   - [ ] All success criteria defined
   - [ ] Edge cases identified

   ## Consistency

   - [ ] Design aligns with spec
   - [ ] No contradictions in artifacts
   - [ ] All components consistent
   - [ ] Terminology consistent

   ## Feasibility

   - [ ] Technical requirements understood
   - [ ] Dependencies identified
   - [ ] Risks assessed and mitigated
   - [ ] Implementation approach clear

   ## Quality

   - [ ] Well-documented
   - [ ] Clear diagrams and examples
   - [ ] Rationale provided for decisions
   - [ ] Ready for implementation
   ```

4. **If NO references found**:
   - Skip template creation
   - templates/ directory remains empty with just .gitkeep
   - Document: "No content template references found in WP02"

5. **Validate templates created**:
   - [ ] Files exist at correct paths
   - [ ] Content is clear and helpful
   - [ ] Markdown is well-formatted
   - [ ] No broken links or references

**Success Criteria**:
- [ ] All referenced content templates created
- [ ] Templates follow markdown best practices
- [ ] Templates are plan-mission specific (not generic)
- [ ] Ready for agents to use (if needed)

---

### Subtask T011: Create Test File and Structure
**Duration**: 20-30 minutes
**Goal**: Create the pytest test file with basic structure and setup.

**File Path**: `tests/specify_cli/next/test_plan_mission_runtime.py`

**Test File Structure**:

```python
"""
Tests for plan mission runtime support (Feature 041).

Coverage:
- Mission discovery integration test
- Command resolution tests (all 4 steps)
- Regression tests (software-dev, research missions)
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Generator

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary spec-kitty project for testing.

    Setup: Creates minimal project structure
    Teardown: Cleanup handled by tmp_path
    Yields: Path to project root
    """
    # TODO: Implement fixture
    # Should create:
    # - kitty-specs/ directory
    # - .kittify/ directory (if needed)
    # - Minimal config files
    yield tmp_path
    # Cleanup (optional, tmp_path handles it)


@pytest.fixture
def plan_feature(temp_project: Path) -> tuple[str, Path]:
    """Create a test feature with mission=plan.

    Depends on: temp_project
    Yields: (feature_slug, feature_dir)
    """
    # TODO: Implement fixture
    # Should:
    # - Create feature directory: kitty-specs/NNN-test-plan-feature/
    # - Create meta.json with mission: "plan"
    # - Create minimal spec.md
    feature_slug = "test-plan-feature"
    feature_dir = temp_project / "kitty-specs" / "001-test-plan-feature"
    yield (feature_slug, feature_dir)


@pytest.fixture
def mock_runtime_bridge() -> MagicMock:
    """Mock the runtime bridge for unit tests.

    Returns: MagicMock with methods:
    - discover_mission(mission_key) -> mission_definition
    - resolve_command(mission, step) -> template_content
    """
    bridge = MagicMock()
    # Configure mocks as needed by tests
    return bridge


# ============================================================================
# Test Classes
# ============================================================================

class TestPlanMissionIntegration:
    """Integration tests for plan mission feature creation and runtime."""

    def test_create_plan_feature_with_mission_yaml(self, plan_feature):
        """Verify plan feature can be created with mission=plan."""
        # TODO: Implement
        pass

    def test_next_command_plan_feature_not_blocked(self, plan_feature):
        """Verify spec-kitty next doesn't block on plan features."""
        # TODO: Implement
        pass

    def test_plan_mission_all_steps_reachable(self, plan_feature):
        """Verify all 4 steps are accessible."""
        # TODO: Implement
        pass


class TestPlanCommandResolution:
    """Resolution tests for plan mission command templates."""

    def test_resolve_specify_command_template(self):
        """Verify specify.md template resolves successfully."""
        # TODO: Implement
        pass

    def test_resolve_all_plan_steps(self):
        """Verify all 4 step templates resolve."""
        # TODO: Implement
        pass

    def test_mission_runtime_yaml_validation(self):
        """Verify mission-runtime.yaml is valid."""
        # TODO: Implement
        pass


class TestPlanMissionRegressions:
    """Regression tests ensuring no impacts to other missions."""

    def test_software_dev_mission_still_resolves(self):
        """Verify software-dev mission unaffected."""
        # TODO: Implement
        pass

    def test_research_mission_still_resolves(self):
        """Verify research mission unaffected."""
        # TODO: Implement
        pass
```

**Steps**:

1. **Create the test file**:
   ```bash
   touch tests/specify_cli/next/test_plan_mission_runtime.py
   ```

2. **Write the basic structure** using the template above:
   - Imports (pytest, pathlib, unittest.mock)
   - Docstring with coverage description
   - 3 test classes: Integration, Resolution, Regression
   - Placeholders for fixtures (temp_project, plan_feature, mock_runtime_bridge)
   - TODO placeholders for actual test implementations (WP04 will fill these in)

3. **Verify file structure**:
   - [ ] File imports without errors: `python -c "import tests.specify_cli.next.test_plan_mission_runtime"`
   - [ ] Fixtures are properly decorated with @pytest.fixture
   - [ ] Test classes are properly organized
   - [ ] All TODO placeholders documented

4. **Ensure pytest can discover it**:
   ```bash
   pytest tests/specify_cli/next/test_plan_mission_runtime.py --collect-only
   ```
   Should show 3 test classes with TODO test methods.

**Success Criteria**:
- [ ] test_plan_mission_runtime.py created at correct path
- [ ] File structure matches template above
- [ ] Fixtures defined (with TODO implementations)
- [ ] 3 test classes defined (Integration, Resolution, Regression)
- [ ] File imports without errors
- [ ] pytest can discover test classes and methods

---

### Subtask T012: Set Up Test Fixtures and Mocks
**Duration**: 20-30 minutes
**Goal**: Implement the fixtures and mocks so they're ready for WP04 test implementation.

**Steps**:

1. **Implement temp_project fixture**:
   ```python
   @pytest.fixture
   def temp_project(tmp_path: Path) -> Generator[Path, None, None]:
       """Create minimal spec-kitty project structure."""
       # Create kitty-specs/ directory
       (tmp_path / "kitty-specs").mkdir()

       # Create .kittify/ directory (if needed)
       (tmp_path / ".kittify").mkdir()

       # Create .git/ directory (for git operations)
       (tmp_path / ".git").mkdir()

       yield tmp_path
       # Cleanup handled by tmp_path
   ```

2. **Implement plan_feature fixture**:
   ```python
   @pytest.fixture
   def plan_feature(temp_project: Path) -> tuple[str, Path]:
       """Create test feature with mission=plan."""
       feature_dir = temp_project / "kitty-specs" / "001-test-plan-feature"
       feature_dir.mkdir()

       # Create meta.json
       meta = {
           "feature_number": "001",
           "slug": "001-test-plan-feature",
           "mission": "plan",
           "created_at": "2026-02-22T00:00:00+00:00"
       }
       import json
       (feature_dir / "meta.json").write_text(json.dumps(meta))

       # Create spec.md
       (feature_dir / "spec.md").write_text("# Test Feature\n\nTest specification.")

       yield ("test-plan-feature", feature_dir)
   ```

3. **Implement mock_runtime_bridge**:
   ```python
   @pytest.fixture
   def mock_runtime_bridge() -> MagicMock:
       """Mock runtime bridge for unit tests."""
       bridge = MagicMock()

       # Configure discover_mission to return valid mission
       bridge.discover_mission.return_value = {
           "mission": {
               "key": "plan",
               "steps": [
                   {"id": "specify", "order": 1},
                   {"id": "research", "order": 2},
                   {"id": "plan", "order": 3},
                   {"id": "review", "order": 4}
               ]
           }
       }

       # Configure resolve_command
       bridge.resolve_command.return_value = "<resolved template>"

       return bridge
   ```

4. **Test fixtures**:
   ```bash
   pytest tests/specify_cli/next/test_plan_mission_runtime.py::TestPlanMissionIntegration -v --collect-only
   ```
   Should show fixtures as available.

5. **Validate**:
   - [ ] temp_project creates necessary directories
   - [ ] plan_feature creates valid feature structure
   - [ ] mock_runtime_bridge returns expected values
   - [ ] Fixtures are reusable across tests
   - [ ] No errors when running: `pytest --collect-only`

**Success Criteria**:
- [ ] All 3 fixtures implemented and functional
- [ ] Fixtures create proper test data structures
- [ ] Mocks return expected values
- [ ] Fixtures are isolated (no cross-test contamination)
- [ ] Ready for WP04 test implementation

---

## Test Strategy

**No unit tests for this WP** - This WP creates the testing infrastructure itself.

**Validation checks**:
- [ ] Test file imports without errors
- [ ] Fixtures are properly defined
- [ ] Fixtures create expected data structures
- [ ] pytest can discover test classes
- [ ] Mocks return expected values

**Integration validation** (WP04):
- Fixtures work with actual test implementations
- Tests can access required data
- Mocks integrate with test logic

---

## Definition of Done

- [x] Content templates created (if referenced in WP02)
- [x] test_plan_mission_runtime.py created at correct path
- [x] File structure matches specification
- [x] 3 test classes defined: Integration, Resolution, Regression
- [x] Fixtures implemented: temp_project, plan_feature, mock_runtime_bridge
- [x] Fixtures create proper test data
- [x] Mocks are configured correctly
- [x] pytest discovers test file and classes
- [x] File imports without errors
- [x] Ready for test implementation in WP04

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Fixture setup too slow | LOW | Use minimal setup; optimize in WP04 |
| Fixtures interfere with each other | MEDIUM | Use separate tmp_path per test |
| Mocks don't match real bridge | MEDIUM | Match real runtime bridge interface |
| Content templates incomplete | LOW | Only create if referenced; keep simple |

---

## Reviewer Guidance

**What to Check**:
1. Are all fixtures properly implemented?
2. Do fixtures create the expected data structures?
3. Are mocks configured to match real bridge interface?
4. Can pytest discover the test file and classes?
5. Are the fixtures isolated (no cross-test contamination)?

**Green Light**: Fixtures work correctly, test file imports, pytest discovers all tests, ready for implementation.

**Red Light**: Fixture errors, import failures, incomplete mock setup, or pytest discovery issues.

---

## Next Work Package

WP04 will implement all test methods (currently TODO placeholders) using these fixtures and mocks.

Implementation command after WP02 completes:
```bash
spec-kitty implement WP03 --base WP02
```

After completion:
```bash
spec-kitty implement WP04 --base WP03
```

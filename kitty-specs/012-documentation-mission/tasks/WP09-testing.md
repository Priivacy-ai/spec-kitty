---
work_package_id: "WP09"
subtasks:
  - "T053"
  - "T054"
  - "T055"
  - "T056"
  - "T057"
  - "T058"
  - "T059"
  - "T060"
  - "T060A"
  - "T061"
  - "T062"
  - "T063"
  - "T064"
  - "T065"
  - "T066"
  - "T067"
  - "T068"
  - "T069"
  - "T070"
  - "T071"
  - "T072"
  - "T073"
  - "T074"
  - "T075"
  - "T076"
title: "Testing & Validation"
phase: "Phase 2 - Quality"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "77266"
review_status: ""
reviewed_by: ""
dependencies:
  - "WP01"
  - "WP02"
  - "WP03"
  - "WP04"
  - "WP05"
  - "WP06"
  - "WP07"
  - "WP08"
history:
  - timestamp: "2026-01-12T17:18:56Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP09 – Testing & Validation

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

**This WP depends on**: WP01-08 (All implementation work packages)

**Before starting work**:
1. Ensure WP01-08 are complete (all code implemented)
2. Verify all modules can be imported
3. Run existing spec-kitty tests to ensure baseline passes

**Critical**: Testing validates all previous work packages. If implementation is incomplete, tests will fail. Complete WP01-08 before starting WP09.

---

## Objectives & Success Criteria

**Goal**: Create comprehensive test suite for documentation mission covering mission loading, template validation, generator integration, gap analysis, state management, and migration, achieving 80%+ code coverage on new modules.

**Success Criteria**:
- Four test files created covering all documentation mission functionality
- Mission config loading tested (mission.yaml validation, phase definitions)
- All templates tested (existence, structure, frontmatter, sections)
- All generators tested (detection, configuration, generation, error handling)
- Gap analysis tested (framework detection, classification, coverage matrix, prioritization)
- State management tested (read/write, migration, validation)
- Migration tested (detection, apply, idempotency, existing mission safety)
- Integration tests for end-to-end workflows
- All tests pass (100% passing rate)
- Code coverage ≥80% for new modules (doc_generators.py, gap_analysis.py, doc_state.py)
- Tests run on CI (if applicable)

## Context & Constraints

**Prerequisites**:
- pytest installed and configured
- All WP01-08 implementation complete
- Test fixtures and helpers from existing spec-kitty tests

**Reference Documents**:
- [plan.md](../plan.md) - Testing strategy (lines 255-261)
- [quickstart.md](../quickstart.md) - Testing patterns and examples (lines 123-191)
- Existing tests:
  - `tests/specify_cli/test_mission.py` (mission loading tests)
  - `tests/specify_cli/upgrade/migrations/test_m_0_9_1_complete_lane_migration.py` (migration testing patterns)

**Constraints**:
- Must use pytest framework
- Must use tmp_path fixture for file system tests
- Must mock subprocess calls for unit tests (avoid requiring generator tools)
- Must use @pytest.mark.integration for tests requiring actual tools
- Must be fast (unit tests < 100ms each, integration tests < 5s each)
- Must be deterministic (no flaky tests)

**Test Pyramid** (from quickstart):
```
╔══════════════════════════╗
║   E2E Tests (10%)        ║  5-10 tests: Full mission workflows
╠══════════════════════════╣
║   Integration (30%)      ║  15-20 tests: Generator invocation, template rendering
╠══════════════════════════╣
║   Unit Tests (60%)       ║  40-50 tests: Mission loading, validation, functions
╚══════════════════════════╝
```

## Subtasks & Detailed Guidance

### Subtask T053 – Create test_documentation_mission.py

**Purpose**: Create test file for mission configuration loading and validation.

**Steps**:
1. Create `tests/specify_cli/missions/test_documentation_mission.py`
2. Add imports and fixtures:
   ```python
   """Tests for documentation mission configuration."""

   import pytest
   from pathlib import Path

   from specify_cli.mission import (
       Mission,
       MissionError,
       get_mission_by_name,
       list_available_missions
   )
   ```

**Files**: `tests/specify_cli/missions/test_documentation_mission.py` (new file)

**Parallel?**: Yes (can create test files in parallel)

**Notes**: Foundation for mission config tests (T054-T056)

### Subtask T054 – Test mission.yaml Loading

**Purpose**: Test that mission.yaml loads correctly and passes validation.

**Steps**:
1. Add test for successful loading:
   ```python
   def test_documentation_mission_loads():
       """Test documentation mission loads from src/specify_cli/missions/."""
       mission = get_mission_by_name("documentation")

       assert mission.name == "Documentation Kitty"
       assert mission.domain == "other"
       assert mission.version == "1.0.0"
   ```

2. Add test for mission appears in list:
   ```python
   def test_documentation_mission_in_list():
       """Test documentation mission appears in available missions."""
       missions = list_available_missions()

       assert "documentation" in missions
   ```

3. Add test for config validation:
   ```python
   def test_documentation_mission_config_valid():
       """Test mission.yaml passes pydantic validation."""
       mission = get_mission_by_name("documentation")

       # Access config to trigger validation
       config = mission.config

       assert config.name is not None
       assert config.version is not None
       assert len(config.workflow.phases) > 0
   ```

**Files**: `tests/specify_cli/missions/test_documentation_mission.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**:
- Tests use actual mission files from src/specify_cli/missions/documentation/
- No mocking needed (tests real mission loading)
- Fast tests (< 10ms each)

### Subtask T055 – Test Workflow Phases

**Purpose**: Test that documentation mission has correct workflow phases (discover, audit, design, generate, validate, publish).

**Steps**:
1. Add test for phase definitions:
   ```python
   def test_documentation_mission_workflow_phases():
       """Test documentation mission has 6 workflow phases."""
       mission = get_mission_by_name("documentation")
       phases = mission.get_workflow_phases()

       assert len(phases) == 6

       # Check phase names in order
       phase_names = [p["name"] for p in phases]
       assert phase_names == [
           "discover",
           "audit",
           "design",
           "generate",
           "validate",
           "publish"
       ]

   def test_documentation_mission_phase_descriptions():
       """Test each phase has description."""
       mission = get_mission_by_name("documentation")
       phases = mission.get_workflow_phases()

       for phase in phases:
           assert "description" in phase
           assert len(phase["description"]) > 0
   ```

**Files**: `tests/specify_cli/missions/test_documentation_mission.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**:
- Validates phase count and names
- Validates phase order (discover first, publish last)
- Validates descriptions are present

### Subtask T056 – Test Artifacts and Paths

**Purpose**: Test that mission defines appropriate artifacts and path conventions.

**Steps**:
1. Add test for required artifacts:
   ```python
   def test_documentation_mission_required_artifacts():
       """Test documentation mission requires appropriate artifacts."""
       mission = get_mission_by_name("documentation")
       required = mission.get_required_artifacts()

       assert "spec.md" in required
       assert "plan.md" in required
       assert "tasks.md" in required
       assert "gap-analysis.md" in required
   ```

2. Add test for optional artifacts:
   ```python
   def test_documentation_mission_optional_artifacts():
       """Test documentation mission has optional artifacts."""
       mission = get_mission_by_name("documentation")
       optional = mission.get_optional_artifacts()

       # Should include divio-templates, generator-configs, etc.
       assert "divio-templates/" in optional or "research.md" in optional
       assert "release.md" in optional
   ```

3. Add test for path conventions:
   ```python
   def test_documentation_mission_path_conventions():
       """Test documentation mission defines path conventions."""
       mission = get_mission_by_name("documentation")
       paths = mission.get_path_conventions()

       assert "workspace" in paths
       assert paths["workspace"] == "docs/"
       assert "deliverables" in paths
   ```

**Files**: `tests/specify_cli/missions/test_documentation_mission.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**:
- Validates required artifacts include gap-analysis.md
- Validates path conventions point to docs/
- Tests actual values from mission.yaml

### Subtask T057 – Create test_documentation_templates.py

**Purpose**: Create test file for template structure and content validation.

**Steps**:
1. Create `tests/specify_cli/missions/test_documentation_templates.py`
2. Add imports:
   ```python
   """Tests for documentation mission templates."""

   import pytest
   from pathlib import Path

   from specify_cli.mission import get_mission_by_name
   ```

**Files**: `tests/specify_cli/missions/test_documentation_templates.py` (new file)

**Parallel?**: Yes (can create test files in parallel)

**Notes**: Foundation for template tests (T058-T060)

### Subtask T058 – Test Divio Template Frontmatter

**Purpose**: Test that each Divio template has valid frontmatter with type field.

**Steps**:
1. Add parametrized test for frontmatter:
   ```python
   @pytest.mark.parametrize("template_name,expected_type", [
       ("divio/tutorial-template.md", "tutorial"),
       ("divio/howto-template.md", "how-to"),
       ("divio/reference-template.md", "reference"),
       ("divio/explanation-template.md", "explanation"),
   ])
   def test_divio_template_has_frontmatter(template_name, expected_type):
       """Test Divio templates have YAML frontmatter with type field."""
       mission = get_mission_by_name("documentation")
       template = mission.get_template(template_name)
       content = template.read_text()

       # Check for frontmatter
       assert content.startswith("---"), f"{template_name} missing frontmatter"

       # Parse frontmatter
       from ruamel.yaml import YAML
       yaml = YAML()

       lines = content.split("\n")
       end_idx = None
       for i, line in enumerate(lines[1:], start=1):
           if line.strip() == "---":
               end_idx = i
               break

       assert end_idx is not None, f"{template_name} frontmatter not closed"

       frontmatter_text = "\n".join(lines[1:end_idx])
       frontmatter = yaml.load(frontmatter_text)

       # Check type field
       assert "type" in frontmatter, f"{template_name} missing type field"
       assert frontmatter["type"] == expected_type
   ```

**Files**: `tests/specify_cli/missions/test_documentation_templates.py` (modified)

**Parallel?**: Yes (parametrized test runs in parallel)

**Notes**:
- Tests all four Divio templates
- Validates frontmatter exists and is valid YAML
- Validates type field matches expected value
- Uses ruamel.yaml for parsing (consistent with spec-kitty)

### Subtask T059 – Test Divio Template Sections

**Purpose**: Test that each Divio template has required sections per Divio principles.

**Steps**:
1. Add test for tutorial sections:
   ```python
   def test_tutorial_template_required_sections():
       """Test tutorial template has required sections."""
       mission = get_mission_by_name("documentation")
       template = mission.get_template("divio/tutorial-template.md")
       content = template.read_text()

       # Required sections for tutorials
       assert "## What You'll Learn" in content or "## What You'll Build" in content
       assert "## Prerequisites" in content or "## Before You Begin" in content
       assert "## Step 1:" in content or "#Step 1:" in content
       assert "## Next Steps" in content or "## What You've Accomplished" in content
   ```

2. Add test for how-to sections:
   ```python
   def test_howto_template_required_sections():
       """Test how-to template has required sections."""
       mission = get_mission_by_name("documentation")
       template = mission.get_template("divio/howto-template.md")
       content = template.read_text()

       # Required sections for how-tos
       assert "How to" in content  # Title should start with "How to"
       assert "## Prerequisites" in content or "## Before" in content
       assert "## Steps" in content or "### 1." in content
       assert "## Verification" in content or "## Related" in content
   ```

3. Add test for reference sections:
   ```python
   def test_reference_template_required_sections():
       """Test reference template has required sections."""
       mission = get_mission_by_name("documentation")
       template = mission.get_template("divio/reference-template.md")
       content = template.read_text()

       # Reference should have structured technical info
       assert "## API Reference" in content or "## CLI Reference" in content or "## Configuration" in content
       assert "## Related" in content or "## Overview" in content
   ```

4. Add test for explanation sections:
   ```python
   def test_explanation_template_required_sections():
       """Test explanation template has required sections."""
       mission = get_mission_by_name("documentation")
       template = mission.get_template("divio/explanation-template.md")
       content = template.read_text()

       # Explanations should have conceptual sections
       assert "## Background" in content or "## Overview" in content
       assert "## Concepts" in content or "## How It Works" in content
       assert "## Design" in content or "## Trade-offs" in content or "## Alternatives" in content
   ```

**Files**: `tests/specify_cli/missions/test_documentation_templates.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**:
- Tests section presence (not content)
- Flexible matching (OR conditions for variation)
- Validates templates follow Divio structure

### Subtask T060 – Test Command Templates

**Purpose**: Test that all command templates exist and reference appropriate workflow phases.

**Steps**:
1. Add test for command template existence:
   ```python
   def test_documentation_mission_command_templates():
       """Test all command templates exist."""
       mission = get_mission_by_name("documentation")
       commands = mission.list_commands()

       assert "specify" in commands
       assert "plan" in commands
       assert "tasks" in commands
       assert "implement" in commands
       assert "review" in commands
   ```

2. Add parametrized test for phase references:
   ```python
   @pytest.mark.parametrize("command_name,expected_phases", [
       ("specify", ["discover"]),
       ("plan", ["audit", "design"]),
       ("tasks", ["design"]),
       ("implement", ["generate"]),
       ("review", ["validate"]),
   ])
   def test_command_template_references_phases(command_name, expected_phases):
       """Test command templates reference appropriate workflow phases."""
       mission = get_mission_by_name("documentation")
       template = mission.get_command_template(command_name)
       content = template.read_text().lower()

       # Check that at least one expected phase is mentioned
       assert any(phase.lower() in content for phase in expected_phases), \
           f"{command_name} template should reference {expected_phases}"
   ```

3. Add test for Divio mentions:
   ```python
   def test_command_templates_mention_divio():
       """Test command templates mention Divio types."""
       mission = get_mission_by_name("documentation")

       for command in ["specify", "plan", "tasks", "implement", "review"]:
           template = mission.get_command_template(command)
           content = template.read_text().lower()

           # Should mention at least one Divio type or "divio"
           mentions_divio = (
               "divio" in content or
               "tutorial" in content or
               "how-to" in content or
               "reference" in content or
               "explanation" in content
           )

           assert mentions_divio, f"{command} template should mention Divio system"
   ```

**Files**: `tests/specify_cli/missions/test_documentation_templates.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**:
- Tests command templates exist and load
- Validates phase references (each command mentions appropriate phase)
- Validates Divio mentions (documentation-specific)

### Subtask T060A – Test Release Template Structure

**Purpose**: Test that optional release-template.md has required sections for publish guidance.

**Steps**:
1. Add test for release template structure:
   ```python
   def test_release_template_required_sections():
       """Test release template has required sections for publish guidance."""
       mission = get_mission_by_name("documentation")
       template = mission.get_template("release-template.md")
       content = template.read_text()

       # Required sections for release/publish guidance
       assert "## Hosting Target" in content, "Missing Hosting Target section"
       assert "## Build Output" in content, "Missing Build Output section"
       assert "## Deployment Steps" in content, "Missing Deployment Steps section"
       assert "## Ownership & Handoff" in content or "## Ownership & Maintenance" in content, "Missing Ownership section"

       # Optional but recommended sections
       assert "## Access" in content or "## Credentials" in content, "Missing Access/Credentials section"
       assert "## Troubleshooting" in content, "Missing Troubleshooting section"
   ```

2. Add test for release template placeholders:
   ```python
   def test_release_template_has_placeholders():
       """Test release template has guidance placeholders."""
       mission = get_mission_by_name("documentation")
       template = mission.get_template("release-template.md")
       content = template.read_text()

       # Should have placeholder guidance
       assert "{" in content and "}" in content, "Missing placeholder markers"

       # Key placeholders should be present
       assert "{platform}" in content or "{hosting" in content, "Missing platform placeholder"
       assert "{url}" in content or "{production_url}" in content, "Missing URL placeholder"
       assert "{build_command}" in content, "Missing build command placeholder"
   ```

**Files**: `tests/specify_cli/missions/test_documentation_templates.py` (modified)

**Parallel?**: Yes (independent test function)

**Notes**:
- Release template is optional, but if present should guide complete handoff
- Tests validate structure without requiring specific formatting
- Placeholders ensure template provides guidance, not just empty sections

### Subtask T061 – Create test_doc_generators.py

**Purpose**: Create test file for documentation generator protocol and implementations.

**Steps**:
1. Create `tests/specify_cli/test_doc_generators.py`
2. Add imports and fixtures:
   ```python
   """Tests for documentation generators."""

   import json
   import subprocess
   from pathlib import Path
   from unittest.mock import Mock, patch

   import pytest

   from specify_cli.doc_generators import (
       DocGenerator,
       GeneratorResult,
       GeneratorError,
       JSDocGenerator,
       SphinxGenerator,
       RustdocGenerator,
   )
   ```

**Files**: `tests/specify_cli/test_doc_generators.py` (new file)

**Parallel?**: Yes (can create test files in parallel)

**Notes**: Foundation for generator tests (T062-T066)

### Subtask T062 – Test JSDoc Detection

**Purpose**: Test JSDocGenerator correctly detects JavaScript/TypeScript projects.

**Steps**:
1. Add test for package.json detection:
   ```python
   def test_jsdoc_detects_package_json(tmp_path):
       """Test JSDoc detects projects with package.json."""
       (tmp_path / "package.json").write_text('{"name": "test"}')

       generator = JSDocGenerator()
       assert generator.detect(tmp_path) is True
   ```

2. Add test for JS file detection:
   ```python
   def test_jsdoc_detects_js_files(tmp_path):
       """Test JSDoc detects projects with .js files."""
       src_dir = tmp_path / "src"
       src_dir.mkdir()
       (src_dir / "index.js").write_text("// JavaScript file")

       generator = JSDocGenerator()
       assert generator.detect(tmp_path) is True
   ```

3. Add test for TS file detection:
   ```python
   def test_jsdoc_detects_ts_files(tmp_path):
       """Test JSDoc detects projects with .ts files."""
       (tmp_path / "app.ts").write_text("// TypeScript file")

       generator = JSDocGenerator()
       assert generator.detect(tmp_path) is True
   ```

4. Add negative test:
   ```python
   def test_jsdoc_does_not_detect_python_project(tmp_path):
       """Test JSDoc does not detect Python projects."""
       (tmp_path / "setup.py").write_text("# Python project")

       generator = JSDocGenerator()
       assert generator.detect(tmp_path) is False
   ```

**Files**: `tests/specify_cli/test_doc_generators.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**: Tests detection accuracy for JSDoc

### Subtask T063 – Test Sphinx Detection

**Purpose**: Test SphinxGenerator correctly detects Python projects.

**Steps**:
1. Add tests similar to JSDoc:
   ```python
   def test_sphinx_detects_setup_py(tmp_path):
       """Test Sphinx detects projects with setup.py."""
       (tmp_path / "setup.py").write_text("# setup.py")

       generator = SphinxGenerator()
       assert generator.detect(tmp_path) is True

   def test_sphinx_detects_pyproject_toml(tmp_path):
       """Test Sphinx detects projects with pyproject.toml."""
       (tmp_path / "pyproject.toml").write_text("[project]")

       generator = SphinxGenerator()
       assert generator.detect(tmp_path) is True

   def test_sphinx_detects_py_files(tmp_path):
       """Test Sphinx detects projects with .py files."""
       (tmp_path / "main.py").write_text("# Python file")

       generator = SphinxGenerator()
       assert generator.detect(tmp_path) is True

   def test_sphinx_does_not_detect_js_project(tmp_path):
       """Test Sphinx does not detect JavaScript projects."""
       (tmp_path / "package.json").write_text("{}")

       generator = SphinxGenerator()
       assert generator.detect(tmp_path) is False
   ```

**Files**: `tests/specify_cli/test_doc_generators.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**: Tests detection accuracy for Sphinx

### Subtask T064 – Test rustdoc Detection

**Purpose**: Test RustdocGenerator correctly detects Rust projects.

**Steps**:
1. Add tests for rustdoc:
   ```python
   def test_rustdoc_detects_cargo_toml(tmp_path):
       """Test rustdoc detects projects with Cargo.toml."""
       (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"')

       generator = RustdocGenerator()
       assert generator.detect(tmp_path) is True

   def test_rustdoc_detects_rs_files(tmp_path):
       """Test rustdoc detects projects with .rs files."""
       (tmp_path / "main.rs").write_text("// Rust file")

       generator = RustdocGenerator()
       assert generator.detect(tmp_path) is True

   def test_rustdoc_does_not_detect_python_project(tmp_path):
       """Test rustdoc does not detect Python projects."""
       (tmp_path / "setup.py").write_text("# Python")

       generator = RustdocGenerator()
       assert generator.detect(tmp_path) is False
   ```

**Files**: `tests/specify_cli/test_doc_generators.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**: Tests detection accuracy for rustdoc

### Subtask T065 – Test Graceful Degradation

**Purpose**: Test generators handle missing tools gracefully with clear error messages.

**Steps**:
1. Add test for missing tool detection:
   ```python
   def test_jsdoc_raises_error_when_npx_missing(tmp_path, monkeypatch):
       """Test JSDoc raises GeneratorError when npx not installed."""
       # Mock subprocess to simulate missing npx
       def mock_run(cmd, *args, **kwargs):
           if cmd[0] == "npx":
               class Result:
                   returncode = 127
                   stdout = ""
                   stderr = "npx: command not found"
               return Result()
           return subprocess.run(cmd, *args, **kwargs)

       monkeypatch.setattr(subprocess, "run", mock_run)

       # Configure first (should succeed)
       generator = JSDocGenerator()
       config = generator.configure(tmp_path, {"project_name": "Test"})
       assert config.exists()

       # Generate should raise GeneratorError
       with pytest.raises(GeneratorError) as exc_info:
           generator.generate(tmp_path, tmp_path)

       error_msg = str(exc_info.value)
       assert "npx not found" in error_msg
       assert "nodejs.org" in error_msg  # Installation URL
   ```

2. Add similar tests for Sphinx and rustdoc:
   ```python
   def test_sphinx_raises_error_when_sphinx_build_missing(tmp_path, monkeypatch):
       """Test Sphinx raises GeneratorError when sphinx-build not installed."""
       # Similar mocking and assertions
       ...

   def test_rustdoc_raises_error_when_cargo_missing(tmp_path, monkeypatch):
       """Test rustdoc raises GeneratorError when cargo not installed."""
       # Similar mocking and assertions
       ...
   ```

**Files**: `tests/specify_cli/test_doc_generators.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**:
- Uses monkeypatch to mock subprocess.run
- Tests that GeneratorError is raised (not generic exception)
- Tests that error message includes installation URL
- Tests graceful degradation (not crash)

### Subtask T066 – Test Integration (Generators)

**Purpose**: Test end-to-end generator invocation with actual tools (marked as integration tests).

**Steps**:
1. Add Sphinx integration test:
   ```python
   @pytest.mark.integration
   def test_sphinx_generation_end_to_end(tmp_path):
       """Test Sphinx generates docs end-to-end (requires sphinx-build)."""
       # Check if sphinx-build available
       check = subprocess.run(["sphinx-build", "--version"], capture_output=True)
       if check.returncode != 0:
           pytest.skip("sphinx-build not installed")

       # Create Python source with docstring
       source_dir = tmp_path / "src"
       source_dir.mkdir()
       (source_dir / "example.py").write_text('''
   def greet(name: str) -> str:
       """Greet someone by name.

       Args:
           name: Person to greet

       Returns:
           Greeting message
       """
       return f"Hello, {name}!"
   ''')

       # Configure
       docs_dir = tmp_path / "docs"
       docs_dir.mkdir()
       generator = SphinxGenerator()
       config_file = generator.configure(docs_dir, {
           "project_name": "Test",
           "author": "Test Author",
           "version": "0.1.0"
       })

       assert config_file.exists()

       # Generate
       result = generator.generate(source_dir, docs_dir)

       # Verify
       assert result.success
       assert len(result.generated_files) > 0
       assert result.output_dir.exists()
       assert (result.output_dir / "index.html").exists()
   ```

2. Add JSDoc integration test (similar structure)
3. Add rustdoc integration test (similar structure)

**Files**: `tests/specify_cli/test_doc_generators.py` (modified)

**Parallel?**: Yes (independent integration tests)

**Notes**:
- Marked with @pytest.mark.integration
- Skipped if tools not installed (pytest.skip)
- Tests actual tool invocation (not mocked)
- Slow tests (2-5 seconds each)
- Should run on CI if tools installed

### Subtask T067 – Create test_gap_analysis.py

**Purpose**: Create test file for gap analysis functionality.

**Steps**:
1. Create `tests/specify_cli/test_gap_analysis.py`
2. Add imports:
   ```python
   """Tests for documentation gap analysis."""

   import pytest
   from datetime import datetime
   from pathlib import Path

   from specify_cli.gap_analysis import (
       DocFramework,
       DivioType,
       GapPriority,
       DocumentationGap,
       GapAnalysis,
       CoverageMatrix,
       detect_doc_framework,
       classify_divio_type,
       prioritize_gaps,
       analyze_documentation_gaps,
       generate_gap_analysis_report,
   )
   ```

**Files**: `tests/specify_cli/test_gap_analysis.py` (new file)

**Parallel?**: Yes (can create test files in parallel)

**Notes**: Foundation for gap analysis tests (T068-T071)

### Subtask T068 – Test Framework Detection

**Purpose**: Test framework detection correctly identifies documentation frameworks.

**Steps**:
1. Add tests for each framework:
   ```python
   def test_detect_sphinx_framework(tmp_path):
       """Test detects Sphinx from conf.py."""
       (tmp_path / "conf.py").write_text("project = 'Test'")

       framework = detect_doc_framework(tmp_path)
       assert framework == DocFramework.SPHINX

   def test_detect_mkdocs_framework(tmp_path):
       """Test detects MkDocs from mkdocs.yml."""
       (tmp_path / "mkdocs.yml").write_text("site_name: Test")

       framework = detect_doc_framework(tmp_path)
       assert framework == DocFramework.MKDOCS

   def test_detect_docusaurus_framework(tmp_path):
       """Test detects Docusaurus from docusaurus.config.js."""
       (tmp_path / "docusaurus.config.js").write_text("module.exports = {}")

       framework = detect_doc_framework(tmp_path)
       assert framework == DocFramework.DOCUSAURUS

   def test_detect_jekyll_framework(tmp_path):
       """Test detects Jekyll from _config.yml."""
       (tmp_path / "_config.yml").write_text("title: Test")

       framework = detect_doc_framework(tmp_path)
       assert framework == DocFramework.JEKYLL

   def test_detect_plain_markdown(tmp_path):
       """Test detects plain Markdown when no framework present."""
       (tmp_path / "index.md").write_text("# Test")

       framework = detect_doc_framework(tmp_path)
       assert framework == DocFramework.PLAIN_MARKDOWN

   def test_detect_unknown_when_empty(tmp_path):
       """Test returns UNKNOWN for empty directory."""
       framework = detect_doc_framework(tmp_path)
       assert framework == DocFramework.UNKNOWN
   ```

**Files**: `tests/specify_cli/test_gap_analysis.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**: Tests all framework types plus edge cases

### Subtask T069 – Test Divio Classification

**Purpose**: Test Divio type classification from frontmatter and content heuristics.

**Steps**:
1. Add tests for frontmatter classification:
   ```python
   def test_classify_from_frontmatter():
       """Test classification from explicit frontmatter."""
       content = """---
   type: tutorial
   ---
   # Some Content
   """
       divio_type, confidence = classify_divio_type(content)
       assert divio_type == DivioType.TUTORIAL
       assert confidence == 1.0  # High confidence

   @pytest.mark.parametrize("type_str,expected_type", [
       ("tutorial", DivioType.TUTORIAL),
       ("how-to", DivioType.HOWTO),
       ("howto", DivioType.HOWTO),
       ("reference", DivioType.REFERENCE),
       ("explanation", DivioType.EXPLANATION),
   ])
   def test_classify_from_frontmatter_types(type_str, expected_type):
       """Test all Divio type values in frontmatter."""
       content = f"""---
   type: {type_str}
   ---
   # Content
   """
       divio_type, confidence = classify_divio_type(content)
       assert divio_type == expected_type
       assert confidence == 1.0
   ```

2. Add tests for heuristic classification:
   ```python
   def test_classify_tutorial_by_content():
       """Test tutorial classification from content heuristics."""
       content = """# Getting Started Tutorial

   ## What You'll Learn
   In this tutorial, you'll learn...

   ## Step 1: Install
   First, install the software...

   ## Step 2: Run
   Now, let's run it...

   ## What You've Accomplished
   You now know how to...
   """
       divio_type, confidence = classify_divio_type(content)
       assert divio_type == DivioType.TUTORIAL
       assert confidence == 0.7  # Medium confidence (heuristic)

   def test_classify_howto_by_content():
       """Test how-to classification from content heuristics."""
       content = """# How to Deploy

   ## Problem
   You need to deploy...

   ## Solution
   Follow these steps...

   ## Verification
   To verify it worked...
   """
       divio_type, confidence = classify_divio_type(content)
       assert divio_type == DivioType.HOWTO
       assert confidence == 0.7

   def test_classify_reference_by_content():
       """Test reference classification from content heuristics."""
       content = """# API Reference

   ## Functions

   ### function_name

   **Parameters:**
   - param1: description

   **Returns:**
   - return value
   """
       divio_type, confidence = classify_divio_type(content)
       assert divio_type == DivioType.REFERENCE
       assert confidence == 0.7

   def test_classify_explanation_by_content():
       """Test explanation classification from content heuristics."""
       content = """# Architecture Explanation

   ## Background
   This architecture was chosen because...

   ## Design Decisions
   We decided to use...

   ## Alternatives Considered
   We also looked at...

   ## Trade-offs
   The advantages are... The disadvantages are...
   """
       divio_type, confidence = classify_divio_type(content)
       assert divio_type == DivioType.EXPLANATION
       assert confidence == 0.7
   ```

3. Add test for unclassifiable content:
   ```python
   def test_classify_unclassifiable_content():
       """Test returns UNCLASSIFIED for ambiguous content."""
       content = """# Some Document

   This is content without clear type indicators.
   Just generic text.
   """
       divio_type, confidence = classify_divio_type(content)
       assert divio_type == DivioType.UNCLASSIFIED
       assert confidence == 0.0
   ```

**Files**: `tests/specify_cli/test_gap_analysis.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**:
- Tests explicit classification (frontmatter)
- Tests heuristic classification (content analysis)
- Tests confidence scores (1.0 for explicit, 0.7 for heuristic, 0.0 for unclassified)
- Tests all Divio types

### Subtask T070 – Test Coverage Matrix

**Purpose**: Test CoverageMatrix class correctly builds matrix, calculates coverage, identifies gaps.

**Steps**:
1. Add test for matrix construction:
   ```python
   def test_coverage_matrix_initialization():
       """Test CoverageMatrix initializes correctly."""
       matrix = CoverageMatrix(
           project_areas=["auth", "api"],
           cells={
               ("auth", "tutorial"): Path("docs/tutorials/auth.md"),
               ("auth", "reference"): Path("docs/reference/auth.md"),
               ("api", "reference"): Path("docs/reference/api.md"),
           }
       )

       assert len(matrix.project_areas) == 2
       assert len(matrix.divio_types) == 4
       assert len(matrix.cells) == 3  # 3 filled cells
   ```

2. Add test for gap identification:
   ```python
   def test_coverage_matrix_get_gaps():
       """Test get_gaps() returns missing cells."""
       matrix = CoverageMatrix(
           project_areas=["auth", "api"],
           cells={
               ("auth", "tutorial"): Path("docs/tutorials/auth.md"),
               ("auth", "reference"): Path("docs/reference/auth.md"),
               # Missing: auth/how-to, auth/explanation, api/tutorial, api/how-to, api/reference, api/explanation
           }
       )

       gaps = matrix.get_gaps()

       # Should identify 6 gaps (2 areas × 4 types - 2 filled = 6 missing)
       assert len(gaps) == 6
       assert ("auth", "how-to") in gaps
       assert ("api", "tutorial") in gaps
   ```

3. Add test for coverage percentage:
   ```python
   def test_coverage_matrix_percentage():
       """Test coverage percentage calculation."""
       matrix = CoverageMatrix(
           project_areas=["auth", "api"],
           cells={
               ("auth", "tutorial"): Path("docs/tutorials/auth.md"),
               ("auth", "reference"): Path("docs/reference/auth.md"),
               ("api", "reference"): Path("docs/reference/api.md"),
           }
       )

       # 3 filled out of 8 total cells (2 areas × 4 types)
       # But cells dict only has 3 entries, and get_gaps uses all possible combinations
       # Actually: 2 areas × 4 types = 8 possible cells
       # Filled: 3 cells
       # Coverage: 3/8 = 0.375
       coverage = matrix.get_coverage_percentage()
       assert coverage == 0.375
   ```

4. Add test for markdown table generation:
   ```python
   def test_coverage_matrix_markdown_table():
       """Test markdown table generation."""
       matrix = CoverageMatrix(
           project_areas=["auth"],
           cells={
               ("auth", "tutorial"): Path("docs/tutorials/auth.md"),
               ("auth", "reference"): Path("docs/reference/auth.md"),
           }
       )

       table = matrix.to_markdown_table()

       # Check table has headers
       assert "| Area |" in table
       assert "| tutorial |" in table or "tutorial" in table
       assert "✓" in table  # Filled cells marked
       assert "✗" in table  # Empty cells marked
       assert "Coverage:" in table
   ```

**Files**: `tests/specify_cli/test_gap_analysis.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**:
- Tests matrix construction and data access
- Tests gap identification logic
- Tests coverage calculation
- Tests markdown rendering

### Subtask T071 – Test Gap Prioritization

**Purpose**: Test gap prioritization assigns appropriate priorities based on Divio type and project area.

**Steps**:
1. Add test for priority assignment:
   ```python
   def test_prioritize_tutorial_gaps_high():
       """Test tutorial gaps prioritized as HIGH."""
       gaps = [("auth", "tutorial")]
       project_areas = ["auth", "api"]

       prioritized = prioritize_gaps(gaps, project_areas, {})

       assert len(prioritized) == 1
       assert prioritized[0].priority == GapPriority.HIGH
       assert "new users" in prioritized[0].reason.lower()

   def test_prioritize_reference_gaps_high():
       """Test reference gaps prioritized as HIGH for core areas."""
       gaps = [("auth", "reference")]  # auth is core (first area)
       project_areas = ["auth", "api", "cli"]

       prioritized = prioritize_gaps(gaps, project_areas, {})

       assert prioritized[0].priority == GapPriority.HIGH

   def test_prioritize_howto_gaps_medium():
       """Test how-to gaps prioritized as MEDIUM."""
       gaps = [("auth", "how-to")]
       project_areas = ["auth"]

       prioritized = prioritize_gaps(gaps, project_areas, {})

       assert prioritized[0].priority == GapPriority.MEDIUM

   def test_prioritize_explanation_gaps_low():
       """Test explanation gaps prioritized as LOW."""
       gaps = [("auth", "explanation")]
       project_areas = ["auth"]

       prioritized = prioritize_gaps(gaps, project_areas, {})

       assert prioritized[0].priority == GapPriority.LOW
   ```

2. Add test for sorting by priority:
   ```python
   def test_gaps_sorted_by_priority():
       """Test gaps sorted with HIGH first, then MEDIUM, then LOW."""
       gaps = [
           ("auth", "explanation"),  # LOW
           ("auth", "tutorial"),     # HIGH
           ("auth", "how-to"),       # MEDIUM
       ]
       project_areas = ["auth"]

       prioritized = prioritize_gaps(gaps, project_areas, {})

       # Should be sorted: HIGH, MEDIUM, LOW
       assert prioritized[0].priority == GapPriority.HIGH
       assert prioritized[1].priority == GapPriority.MEDIUM
       assert prioritized[2].priority == GapPriority.LOW
   ```

**Files**: `tests/specify_cli/test_gap_analysis.py` (modified)

**Parallel?**: Yes (independent test functions)

**Notes**:
- Tests priority assignment for each Divio type
- Tests core vs peripheral area handling
- Tests sorting by priority
- Validates reasons are provided

### Subtask T072 – Create test_m_0_12_0_documentation_mission.py

**Purpose**: Create test file for documentation mission migration (tests from T050-T052).

**Steps**:
1. Create `tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py`
2. Add imports:
   ```python
   """Tests for documentation mission installation migration."""

   import pytest
   from pathlib import Path

   from specify_cli.upgrade.migrations.m_0_12_0_documentation_mission import (
       InstallDocumentationMission
   )
   from specify_cli.mission import get_mission_by_name, list_available_missions
   ```

**Files**: `tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py` (new file)

**Parallel?**: Yes (can create test files in parallel)

**Notes**: Foundation for migration tests (T073-T076)

### Subtask T073 – Test Migration Detection

**Purpose**: Test migration correctly detects when documentation mission is missing.

**Steps**:
1. Add detection tests (from T048 notes):
   ```python
   def test_detect_missing_mission(tmp_path):
       """Test migration detects when documentation mission is missing."""
       kittify = tmp_path / ".kittify"
       kittify.mkdir()

       migration = InstallDocumentationMission()
       assert migration.detect(tmp_path) is True

   def test_detect_existing_mission(tmp_path):
       """Test migration detects when documentation mission already exists."""
       missions = tmp_path / ".kittify" / "missions" / "documentation"
       missions.mkdir(parents=True)
       (missions / "mission.yaml").write_text("name: Documentation Kitty\n")

       migration = InstallDocumentationMission()
       assert migration.detect(tmp_path) is False

   def test_detect_non_kittify_project(tmp_path):
       """Test migration returns False for non-spec-kitty projects."""
       # No .kittify directory
       migration = InstallDocumentationMission()
       assert migration.detect(tmp_path) is False
   ```

**Files**: `tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py` (modified)

**Parallel?**: Yes (independent test functions)

### Subtask T074 – Test Migration Copy

**Purpose**: Test migration correctly copies mission directory.

**Steps**:
1. Add tests for apply():
   ```python
   def test_apply_installs_mission(tmp_path):
       """Test migration successfully installs documentation mission."""
       kittify = tmp_path / ".kittify"
       kittify.mkdir()

       migration = InstallDocumentationMission()
       result = migration.apply(tmp_path)

       assert result.success
       assert "installed" in result.message.lower()

       # Verify mission directory exists
       doc_mission = kittify / "missions" / "documentation"
       assert doc_mission.exists()
       assert (doc_mission / "mission.yaml").exists()

   def test_apply_copies_all_templates(tmp_path):
       """Test migration copies all template files."""
       kittify = tmp_path / ".kittify"
       kittify.mkdir()

       migration = InstallDocumentationMission()
       migration.apply(tmp_path)

       doc_mission = kittify / "missions" / "documentation"

       # Check core templates
       assert (doc_mission / "templates" / "spec-template.md").exists()
       assert (doc_mission / "templates" / "plan-template.md").exists()

       # Check Divio templates
       assert (doc_mission / "templates" / "divio" / "tutorial-template.md").exists()
       assert (doc_mission / "templates" / "divio" / "howto-template.md").exists()
       assert (doc_mission / "templates" / "divio" / "reference-template.md").exists()
       assert (doc_mission / "templates" / "divio" / "explanation-template.md").exists()

       # Check command templates
       assert (doc_mission / "command-templates" / "specify.md").exists()
       assert (doc_mission / "command-templates" / "plan.md").exists()
       assert (doc_mission / "command-templates" / "implement.md").exists()
   ```

**Files**: `tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py` (modified)

**Parallel?**: Yes (independent test functions)

### Subtask T075 – Test Migration Idempotency

**Purpose**: Test migration can run multiple times safely (from T051).

**Steps**:
1. Add idempotency test (from T051 notes):
   ```python
   def test_migration_is_idempotent(tmp_path):
       """Test migration can run multiple times without errors."""
       kittify = tmp_path / ".kittify"
       missions = kittify / "missions"
       missions.mkdir(parents=True)

       migration = InstallDocumentationMission()

       # First run
       result1 = migration.apply(tmp_path)
       assert result1.success

       # Count files
       doc_mission = missions / "documentation"
       files_after_first = list(doc_mission.rglob("*"))
       file_count_1 = len([f for f in files_after_first if f.is_file()])

       # Second run
       result2 = migration.apply(tmp_path)
       assert result2.success

       # Verify no changes
       files_after_second = list(doc_mission.rglob("*"))
       file_count_2 = len([f for f in files_after_second if f.is_file()])
       assert file_count_1 == file_count_2

   def test_detect_false_after_apply(tmp_path):
       """Test detect() returns False after successful apply()."""
       kittify = tmp_path / ".kittify"
       kittify.mkdir()

       migration = InstallDocumentationMission()

       assert migration.detect(tmp_path) is True  # Before
       migration.apply(tmp_path)
       assert migration.detect(tmp_path) is False  # After
   ```

**Files**: `tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py` (modified)

**Parallel?**: Yes (independent test functions)

### Subtask T076 – Test Migration Doesn't Break Existing

**Purpose**: Test migration doesn't affect existing missions (from T050).

**Steps**:
1. Add tests from T050 notes:
   ```python
   def test_migration_preserves_software_dev(tmp_path):
       """Test migration doesn't touch software-dev mission."""
       # Create software-dev mission
       software_dev = tmp_path / ".kittify" / "missions" / "software-dev"
       software_dev.mkdir(parents=True)
       (software_dev / "mission.yaml").write_text("name: Software Dev Kitty\n")
       original_content = (software_dev / "mission.yaml").read_text()

       # Run migration
       migration = InstallDocumentationMission()
       migration.apply(tmp_path)

       # Verify unchanged
       assert (software_dev / "mission.yaml").read_text() == original_content

   def test_migration_preserves_research(tmp_path):
       """Test migration doesn't touch research mission."""
       # Similar to software-dev test
       research = tmp_path / ".kittify" / "missions" / "research"
       research.mkdir(parents=True)
       (research / "mission.yaml").write_text("name: Research Kitty\n")
       original_content = (research / "mission.yaml").read_text()

       migration = InstallDocumentationMission()
       migration.apply(tmp_path)

       assert (research / "mission.yaml").read_text() == original_content

   def test_migration_only_touches_documentation(tmp_path):
       """Test migration only creates documentation mission directory."""
       kittify = tmp_path / ".kittify"
       kittify.mkdir()
       (kittify / "config.json").write_text("{}")

       migration = InstallDocumentationMission()
       migration.apply(tmp_path)

       # Verify config.json unchanged
       assert (kittify / "config.json").read_text() == "{}"

       # Verify only missions/documentation created
       assert (kittify / "missions" / "documentation").exists()
   ```

**Files**: `tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py` (modified)

**Parallel?**: Yes (independent test functions)

## Test Execution

### Running Tests

**All tests**:
```bash
pytest tests/specify_cli/missions/test_documentation_mission.py -v
pytest tests/specify_cli/missions/test_documentation_templates.py -v
pytest tests/specify_cli/test_doc_generators.py -v
pytest tests/specify_cli/test_gap_analysis.py -v
pytest tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py -v
```

**Unit tests only** (fast):
```bash
pytest tests/specify_cli/ -v -m "not integration"
```

**Integration tests** (require tools):
```bash
pytest tests/specify_cli/ -v -m integration
```

**With coverage**:
```bash
pytest tests/specify_cli/ --cov=specify_cli.doc_generators --cov=specify_cli.gap_analysis --cov=specify_cli.doc_state --cov-report=html
```

### Coverage Goals

Target 80%+ coverage for:
- `src/specify_cli/doc_generators.py`
- `src/specify_cli/gap_analysis.py`
- `src/specify_cli/doc_state.py`
- `src/specify_cli/upgrade/migrations/m_0_12_0_documentation_mission.py`

## Test Organization

### Test Files and Coverage

| Test File | What It Tests | Subtasks | Test Count |
|-----------|---------------|----------|------------|
| `test_documentation_mission.py` | Mission config loading | T053-T056 | ~8 tests |
| `test_documentation_templates.py` | Template structure | T057-T060 | ~12 tests |
| `test_doc_generators.py` | Generator protocol | T061-T066 | ~20 tests |
| `test_gap_analysis.py` | Gap analysis logic | T067-T071 | ~18 tests |
| `test_m_0_12_0_documentation_mission.py` | Migration | T072-T076 | ~12 tests |

**Total**: ~70 tests

### Test Categories

**Unit Tests** (~60 tests):
- Mission loading (8 tests)
- Template validation (12 tests)
- Generator detection (12 tests)
- Generator configuration (6 tests)
- Gap analysis (15 tests)
- State management (7 tests - in WP07)
- Migration (10 tests)

**Integration Tests** (~5 tests):
- Sphinx generation end-to-end
- JSDoc generation end-to-end
- rustdoc generation end-to-end
- Full gap analysis on real docs
- Migration on real project

**Parametrized Tests**:
- Divio template frontmatter (4 templates)
- Generator detection (3 generators × 3 scenarios)
- Divio classification (5 types)
- Framework detection (6 frameworks)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Integration tests fail on CI | Medium - gates releases | Mark with @pytest.mark.integration, skip if tools unavailable |
| Flaky subprocess tests | High - unreliable CI | Use deterministic fixtures, mock subprocess for unit tests |
| Low coverage | Medium - bugs slip through | Aim for 80%+, use coverage report to identify gaps |
| Tests too slow | Medium - developer friction | Unit tests fast (<100ms), integration slow (<5s), separate markers |
| Test maintenance burden | Medium - tests become stale | Follow existing spec-kitty test patterns, DRY principles |

## Definition of Done Checklist

### Test Files Created
- [ ] `tests/specify_cli/missions/test_documentation_mission.py` created
- [ ] `tests/specify_cli/missions/test_documentation_templates.py` created
- [ ] `tests/specify_cli/test_doc_generators.py` created
- [ ] `tests/specify_cli/test_gap_analysis.py` created
- [ ] `tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py` created

### Mission Config Tests (test_documentation_mission.py)
- [ ] T054: Test mission loads successfully
- [ ] T054: Test mission appears in list
- [ ] T054: Test config passes validation
- [ ] T055: Test workflow has 6 phases (discover → publish)
- [ ] T055: Test each phase has description
- [ ] T056: Test required artifacts include gap-analysis.md
- [ ] T056: Test path conventions define docs/ workspace

### Template Tests (test_documentation_templates.py)
- [ ] T057: Test core templates exist (spec, plan, tasks)
- [ ] T058: Test Divio templates have frontmatter (parametrized, 4 templates)
- [ ] T058: Test frontmatter type field matches expected value
- [ ] T059: Test tutorial has required sections
- [ ] T059: Test how-to has required sections
- [ ] T059: Test reference has required sections
- [ ] T059: Test explanation has required sections
- [ ] T060: Test all 5 command templates exist
- [ ] T060: Test command templates reference workflow phases (parametrized)
- [ ] T060: Test command templates mention Divio types

### Generator Tests (test_doc_generators.py)
- [ ] T061: Test protocol compliance (all generators implement protocol)
- [ ] T062: Test JSDoc detects package.json projects
- [ ] T062: Test JSDoc detects .js files
- [ ] T062: Test JSDoc detects .ts files
- [ ] T062: Test JSDoc doesn't detect Python projects
- [ ] T063: Test Sphinx detects setup.py projects
- [ ] T063: Test Sphinx detects pyproject.toml projects
- [ ] T063: Test Sphinx detects .py files
- [ ] T063: Test Sphinx doesn't detect JS projects
- [ ] T064: Test rustdoc detects Cargo.toml projects
- [ ] T064: Test rustdoc detects .rs files
- [ ] T064: Test rustdoc doesn't detect Python projects
- [ ] T065: Test JSDoc raises GeneratorError when npx missing
- [ ] T065: Test Sphinx raises GeneratorError when sphinx-build missing
- [ ] T065: Test rustdoc raises GeneratorError when cargo missing
- [ ] T065: Test error messages include installation URLs
- [ ] T066: [@pytest.mark.integration] Test Sphinx end-to-end generation
- [ ] T066: [@pytest.mark.integration] Test JSDoc end-to-end generation
- [ ] T066: [@pytest.mark.integration] Test rustdoc end-to-end generation

### Gap Analysis Tests (test_gap_analysis.py)
- [ ] T068: Test detect Sphinx framework (conf.py)
- [ ] T068: Test detect MkDocs framework (mkdocs.yml)
- [ ] T068: Test detect Docusaurus framework (docusaurus.config.js)
- [ ] T068: Test detect Jekyll framework (_config.yml)
- [ ] T068: Test detect plain Markdown (no framework)
- [ ] T068: Test returns UNKNOWN for empty directory
- [ ] T069: Test classify from frontmatter (explicit type)
- [ ] T069: Test classify tutorial by content heuristics
- [ ] T069: Test classify how-to by content heuristics
- [ ] T069: Test classify reference by content heuristics
- [ ] T069: Test classify explanation by content heuristics
- [ ] T069: Test returns UNCLASSIFIED for ambiguous content
- [ ] T070: Test CoverageMatrix initialization
- [ ] T070: Test get_gaps() returns missing cells
- [ ] T070: Test get_coverage_percentage() calculates correctly
- [ ] T070: Test to_markdown_table() generates valid table
- [ ] T071: Test prioritize tutorial gaps as HIGH
- [ ] T071: Test prioritize reference gaps as HIGH
- [ ] T071: Test prioritize how-to gaps as MEDIUM
- [ ] T071: Test prioritize explanation gaps as LOW
- [ ] T071: Test gaps sorted by priority

### Migration Tests (test_m_0_12_0_documentation_mission.py)
- [ ] T073: Test detect missing mission
- [ ] T073: Test detect existing mission
- [ ] T073: Test detect non-kittify project
- [ ] T074: Test apply installs mission
- [ ] T074: Test apply copies all templates
- [ ] T074: Test apply copies all command templates
- [ ] T075: Test migration is idempotent (can run multiple times)
- [ ] T075: Test detect returns False after apply
- [ ] T076: Test migration preserves software-dev mission
- [ ] T076: Test migration preserves research mission
- [ ] T076: Test migration only touches documentation directory
- [ ] T052: Test migration is registered in registry
- [ ] T052: Test migration can be loaded and instantiated

### Test Execution
- [ ] All unit tests pass (100%)
- [ ] Integration tests pass (if tools installed) or skip gracefully
- [ ] Code coverage ≥80% for new modules
- [ ] Tests run on CI (if applicable)
- [ ] No flaky tests (deterministic results)
- [ ] Test execution time reasonable (unit <10s total, integration <30s total)

### Documentation
- [ ] Test files have docstrings explaining what they test
- [ ] Complex tests have inline comments
- [ ] Fixtures are documented
- [ ] Integration test requirements documented (which tools needed)

### Quality
- [ ] `tasks.md` in feature directory updated with WP09 status

## Review Guidance

**Key Acceptance Checkpoints**:

1. **Test Coverage**: All WP01-08 functionality is tested
2. **Test Quality**: Tests are clear, deterministic, fast
3. **Pass Rate**: 100% of tests pass
4. **Code Coverage**: ≥80% for doc_generators.py, gap_analysis.py, doc_state.py
5. **Integration Tests**: Properly marked, skip if tools unavailable
6. **Edge Cases**: Tests cover error cases, empty inputs, invalid data

**Validation Commands**:
```bash
# Run all tests
pytest tests/specify_cli/missions/test_documentation_mission.py \
       tests/specify_cli/missions/test_documentation_templates.py \
       tests/specify_cli/test_doc_generators.py \
       tests/specify_cli/test_gap_analysis.py \
       tests/specify_cli/upgrade/migrations/test_m_0_12_0_documentation_mission.py \
       -v

# Check coverage
pytest tests/specify_cli/ \
       --cov=specify_cli.doc_generators \
       --cov=specify_cli.gap_analysis \
       --cov=specify_cli.doc_state \
       --cov-report=term-missing

# Run only unit tests (fast)
pytest tests/specify_cli/ -v -m "not integration"

# Run only integration tests
pytest tests/specify_cli/ -v -m integration
```

**Review Focus Areas**:
- All critical functionality has tests
- Tests actually test the behavior (not just imports)
- Edge cases and error conditions covered
- Integration tests skip gracefully if tools missing
- Coverage gaps identified and justified or filled
- Tests follow existing spec-kitty patterns
- Test names are descriptive
- Assertions are meaningful (not just "assert True")

## Activity Log

- 2026-01-12T17:18:56Z – system – lane=planned – Prompt created.
- 2026-01-13T09:20:54Z – debug-test – lane=doing – Moved to doing
- 2026-01-13T09:22:17Z – rollback-test – lane=planned – Moved to planned
- 2026-01-13T09:31:17Z – slug-test – lane=doing – Moved to doing
- 2026-01-13T10:47:28Z – slug-test – lane=planned – Reset to planned (was test activity)
- 2026-01-13T10:56:13Z – claude – shell_pid=64122 – lane=doing – Started implementation via workflow command
- 2026-01-13T10:57:44Z – claude – shell_pid=64122 – lane=doing – Blocked: WP05-08 are in for_review/doing but not yet merged. doc_generators.py, gap_analysis.py, doc_state.py modules not available for testing. Need WP05-08 to complete and merge before WP09 can proceed.
- 2026-01-13T10:57:50Z – claude – shell_pid=64122 – lane=planned – Blocked: Dependencies WP05-08 not yet merged. Returning to planned until implementation WPs complete.
- 2026-01-13T11:25:14Z – claude – shell_pid=77266 – lane=doing – Started implementation via workflow command
- 2026-01-13T11:36:12Z – claude – shell_pid=77266 – lane=for_review – Tests complete: 74 comprehensive tests created (T053-T076). All test files written and committed. Tests ready but cannot run until WP07-WP08 code is merged (doc_state.py, migration). See TEST_STATUS.md for details. Tests follow pytest best practices with fixtures, parametrization, and proper mocking.

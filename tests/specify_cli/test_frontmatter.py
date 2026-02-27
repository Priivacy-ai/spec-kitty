"""Tests for frontmatter management module."""

from pathlib import Path
import pytest
from specify_cli.frontmatter import (
    FrontmatterManager,
    FrontmatterError,
    read_frontmatter,
    write_frontmatter,
    validate_frontmatter,
)


@pytest.fixture
def temp_wp_file(tmp_path):
    """Create a temporary work package file."""
    def _create_file(content: str, filename: str = "WP01.md") -> Path:
        file_path = tmp_path / filename
        file_path.write_text(content)
        return file_path
    return _create_file


class TestDependenciesParsing:
    """Test parsing of dependencies field."""

    def test_parse_wp_with_empty_dependencies(self, temp_wp_file):
        """Test parsing WP with empty dependencies list."""
        content = """---
work_package_id: "WP01"
title: "Test WP"
lane: "planned"
dependencies: []
---
# Content
"""
        wp_file = temp_wp_file(content)
        frontmatter, body = read_frontmatter(wp_file)

        assert "dependencies" in frontmatter
        assert frontmatter["dependencies"] == []
        assert frontmatter["work_package_id"] == "WP01"

    def test_parse_wp_with_single_dependency(self, temp_wp_file):
        """Test parsing WP with single dependency."""
        content = """---
work_package_id: "WP02"
title: "Test WP 2"
lane: "planned"
dependencies:
  - "WP01"
---
# Content
"""
        wp_file = temp_wp_file(content, "WP02.md")
        frontmatter, body = read_frontmatter(wp_file)

        assert frontmatter["dependencies"] == ["WP01"]

    def test_parse_wp_with_multiple_dependencies(self, temp_wp_file):
        """Test parsing WP with multiple dependencies."""
        content = """---
work_package_id: "WP03"
title: "Test WP 3"
lane: "planned"
dependencies:
  - "WP01"
  - "WP02"
---
# Content
"""
        wp_file = temp_wp_file(content, "WP03.md")
        frontmatter, body = read_frontmatter(wp_file)

        assert frontmatter["dependencies"] == ["WP01", "WP02"]

    def test_parse_wp_without_dependencies_field(self, temp_wp_file):
        """Test backward compatibility - WP without dependencies field."""
        content = """---
work_package_id: "WP01"
title: "Legacy WP"
lane: "planned"
---
# Content
"""
        wp_file = temp_wp_file(content)
        frontmatter, body = read_frontmatter(wp_file)

        # Should default to empty list
        assert "dependencies" in frontmatter
        assert frontmatter["dependencies"] == []


class TestDependenciesValidation:
    """Test validation of dependencies field."""

    def test_validate_valid_dependencies(self, temp_wp_file):
        """Test validation passes for valid dependencies."""
        content = """---
work_package_id: "WP02"
title: "Test WP"
lane: "planned"
dependencies:
  - "WP01"
---
# Content
"""
        wp_file = temp_wp_file(content, "WP02.md")
        errors = validate_frontmatter(wp_file)

        assert errors == []

    def test_validate_invalid_dependency_format(self, temp_wp_file):
        """Test validation catches invalid WP ID format."""
        content = """---
work_package_id: "WP02"
title: "Test WP"
lane: "planned"
dependencies:
  - "WP1"
---
# Content
"""
        wp_file = temp_wp_file(content, "WP02.md")
        errors = validate_frontmatter(wp_file)

        assert len(errors) > 0
        assert any("Invalid WP ID format" in err for err in errors)

    def test_validate_duplicate_dependencies(self, temp_wp_file):
        """Test validation catches duplicate dependencies."""
        content = """---
work_package_id: "WP03"
title: "Test WP"
lane: "planned"
dependencies:
  - "WP01"
  - "WP01"
---
# Content
"""
        wp_file = temp_wp_file(content, "WP03.md")
        errors = validate_frontmatter(wp_file)

        assert len(errors) > 0
        assert any("Duplicate dependency" in err for err in errors)

    def test_validate_dependencies_not_list(self, temp_wp_file):
        """Test validation catches non-list dependencies."""
        content = """---
work_package_id: "WP02"
title: "Test WP"
lane: "planned"
dependencies: "WP01"
---
# Content
"""
        wp_file = temp_wp_file(content, "WP02.md")
        errors = validate_frontmatter(wp_file)

        assert len(errors) > 0
        assert any("must be a list" in err for err in errors)

    def test_validate_dependencies_non_string_items(self, temp_wp_file):
        """Test validation catches non-string items in dependencies."""
        content = """---
work_package_id: "WP02"
title: "Test WP"
lane: "planned"
dependencies:
  - 1
---
# Content
"""
        wp_file = temp_wp_file(content, "WP02.md")
        errors = validate_frontmatter(wp_file)

        assert len(errors) > 0
        assert any("must be string" in err for err in errors)


class TestFieldOrdering:
    """Test that dependencies field appears in correct order."""

    def test_field_order_includes_dependencies(self):
        """Test WP_FIELD_ORDER includes dependencies in correct position."""
        manager = FrontmatterManager()

        assert "dependencies" in manager.WP_FIELD_ORDER

        # dependencies should be after lane and before subtasks
        lane_idx = manager.WP_FIELD_ORDER.index("lane")
        dep_idx = manager.WP_FIELD_ORDER.index("dependencies")
        subtasks_idx = manager.WP_FIELD_ORDER.index("subtasks")

        assert dep_idx > lane_idx, "dependencies should come after lane"
        assert dep_idx < subtasks_idx, "dependencies should come before subtasks"

    def test_write_maintains_field_order(self, temp_wp_file):
        """Test writing frontmatter maintains correct field order."""
        content = """---
work_package_id: "WP02"
title: "Test WP"
lane: "planned"
dependencies:
  - "WP01"
subtasks:
  - "T001"
---
# Content
"""
        wp_file = temp_wp_file(content, "WP02.md")

        # Read and rewrite
        frontmatter, body = read_frontmatter(wp_file)
        write_frontmatter(wp_file, frontmatter, body)

        # Read back and verify order
        new_content = wp_file.read_text()
        lines = new_content.split("\n")

        # Find line indices
        lane_line = next(i for i, line in enumerate(lines) if line.startswith("lane:"))
        dep_line = next(i for i, line in enumerate(lines) if line.startswith("dependencies:"))
        subtasks_line = next(i for i, line in enumerate(lines) if line.startswith("subtasks:"))

        # dependencies should come after lane and before subtasks
        assert dep_line > lane_line, "dependencies should come after lane"
        assert dep_line < subtasks_line, "dependencies should come before subtasks"

    def test_field_order_includes_review_feedback(self):
        """Test WP_FIELD_ORDER includes review_feedback in correct position."""
        manager = FrontmatterManager()

        assert "review_feedback" in manager.WP_FIELD_ORDER

        reviewed_by_idx = manager.WP_FIELD_ORDER.index("reviewed_by")
        review_feedback_idx = manager.WP_FIELD_ORDER.index("review_feedback")
        history_idx = manager.WP_FIELD_ORDER.index("history")

        assert review_feedback_idx > reviewed_by_idx, "review_feedback should come after reviewed_by"
        assert review_feedback_idx < history_idx, "review_feedback should come before history"


class TestScopeRestriction:
    """Test that dependencies field is only added to WP files."""

    def test_non_wp_files_dont_get_dependencies(self, tmp_path):
        """Test that non-WP files (spec, plan, etc.) don't get dependencies injected."""
        spec_content = """---
title: "Feature Specification"
version: "1.0"
---
# Spec content
"""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        # Read non-WP file
        frontmatter, body = read_frontmatter(spec_file)

        # Should NOT have dependencies field
        assert "dependencies" not in frontmatter

        # Write it back
        write_frontmatter(spec_file, frontmatter, body)

        # Read again
        new_frontmatter, _ = read_frontmatter(spec_file)

        # Still should NOT have dependencies
        assert "dependencies" not in new_frontmatter

    def test_wp_files_get_dependencies_default(self, tmp_path):
        """Test that WP files without dependencies get the field defaulted."""
        wp_content = """---
work_package_id: "WP01"
title: "Test WP"
lane: "planned"
---
# Content
"""
        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(wp_content)

        # Read WP file
        frontmatter, _ = read_frontmatter(wp_file)

        # Should have dependencies field defaulted
        assert "dependencies" in frontmatter
        assert frontmatter["dependencies"] == []


class TestBackwardCompatibility:
    """Test backward compatibility with pre-0.11.0 WP files."""

    def test_old_wp_without_dependencies_parses(self, temp_wp_file):
        """Test old WP files without dependencies field parse correctly."""
        old_content = """---
work_package_id: "WP01"
title: "Legacy WP"
lane: "planned"
subtasks:
  - "T001"
phase: "Phase 1"
assignee: ""
agent: ""
---
# Content
"""
        wp_file = temp_wp_file(old_content)

        # Should parse without errors
        frontmatter, body = read_frontmatter(wp_file)

        # Should default dependencies to []
        assert frontmatter["dependencies"] == []

        # Other fields should be preserved
        assert frontmatter["work_package_id"] == "WP01"
        assert frontmatter["title"] == "Legacy WP"
        assert frontmatter["subtasks"] == ["T001"]

    def test_validation_passes_for_old_wp(self, temp_wp_file):
        """Test validation passes for old WP files."""
        old_content = """---
work_package_id: "WP01"
title: "Legacy WP"
lane: "planned"
---
# Content
"""
        wp_file = temp_wp_file(old_content)

        errors = validate_frontmatter(wp_file)
        assert errors == []

    def test_writing_preserves_backward_compat(self, temp_wp_file):
        """Test writing old WP preserves all fields."""
        old_content = """---
work_package_id: "WP01"
title: "Legacy WP"
lane: "planned"
subtasks:
  - "T001"
---
# Content
"""
        wp_file = temp_wp_file(old_content)

        # Read and modify
        frontmatter, body = read_frontmatter(wp_file)
        frontmatter["title"] = "Updated Legacy WP"

        # Write back
        write_frontmatter(wp_file, frontmatter, body)

        # Read again
        new_frontmatter, new_body = read_frontmatter(wp_file)

        # Should have dependencies added
        assert new_frontmatter["dependencies"] == []
        # Other fields preserved
        assert new_frontmatter["title"] == "Updated Legacy WP"
        assert new_frontmatter["subtasks"] == ["T001"]

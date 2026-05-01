"""Tests for frontmatter management module."""

from pathlib import Path
import pytest
from specify_cli.frontmatter import (
    FrontmatterManager,
    read_frontmatter,
    write_frontmatter,
    validate_frontmatter,
)

pytestmark = pytest.mark.fast


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
        assert "requirement_refs" in manager.WP_FIELD_ORDER

        # dependencies should come before requirement_refs and subtasks
        dep_idx = manager.WP_FIELD_ORDER.index("dependencies")
        req_idx = manager.WP_FIELD_ORDER.index("requirement_refs")
        subtasks_idx = manager.WP_FIELD_ORDER.index("subtasks")

        assert dep_idx < req_idx, "dependencies should come before requirement_refs"
        assert req_idx < subtasks_idx, "requirement_refs should come before subtasks"

    def test_write_maintains_field_order(self, temp_wp_file):
        """Test writing frontmatter maintains correct field order."""
        content = """---
work_package_id: "WP02"
title: "Test WP"
dependencies:
  - "WP01"
requirement_refs:
  - "FR-001"
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
        dep_line = next(i for i, line in enumerate(lines) if line.startswith("dependencies:"))
        req_line = next(i for i, line in enumerate(lines) if line.startswith("requirement_refs:"))
        subtasks_line = next(i for i, line in enumerate(lines) if line.startswith("subtasks:"))

        # dependencies should come before requirement_refs and subtasks
        assert dep_line < req_line, "dependencies should come before requirement_refs"
        assert req_line < subtasks_line, "requirement_refs should come before subtasks"

    def test_field_order_excludes_mutable_lane_fields(self):
        """Test WP_FIELD_ORDER does not include mutable lane fields (moved to event log)."""
        manager = FrontmatterManager()

        # Lane state is now tracked in status.events.jsonl, not frontmatter
        assert "lane" not in manager.WP_FIELD_ORDER, "lane should not be in WP_FIELD_ORDER (use event log)"
        assert "review_feedback" not in manager.WP_FIELD_ORDER, "review_feedback should not be in WP_FIELD_ORDER"
        assert "reviewed_by" not in manager.WP_FIELD_ORDER, "reviewed_by should not be in WP_FIELD_ORDER"


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

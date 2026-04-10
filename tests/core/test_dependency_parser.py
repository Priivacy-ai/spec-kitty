"""Regression tests for the shared dependency parser (T001-T002).

Covers all three dependency declaration formats and edge cases required by
WP01 acceptance criteria.
"""

from __future__ import annotations

import pytest

from specify_cli.core.dependency_parser import parse_dependencies_from_tasks_md


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tasks_md(*wp_sections: tuple[str, str]) -> str:
    """Build a minimal tasks.md with the given (wp_id, body) pairs."""
    parts = []
    for wp_id, body in wp_sections:
        parts.append(f"## {wp_id}\n\n{body}\n")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Format 1: "Depends on WP##"
# ---------------------------------------------------------------------------


class TestInlineDependsOnFormat:
    def test_single_dep(self) -> None:
        content = _make_tasks_md(
            ("WP02", "Depends on WP01.\n"),
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP02"] == ["WP01"]

    def test_multiple_deps_comma_separated(self) -> None:
        content = _make_tasks_md(
            ("WP03", "Depends on WP01, WP02.\n"),
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP03"] == ["WP01", "WP02"]

    def test_case_insensitive(self) -> None:
        content = _make_tasks_md(
            ("WP02", "DEPENDS ON WP01.\n"),
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP02"] == ["WP01"]

    def test_depend_without_s(self) -> None:
        content = _make_tasks_md(
            ("WP02", "Depend on WP01.\n"),
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP02"] == ["WP01"]


# ---------------------------------------------------------------------------
# Format 2: "**Dependencies**: WP##" header-line colon
# ---------------------------------------------------------------------------


class TestInlineDependenciesColonFormat:
    def test_bold_header_single_dep(self) -> None:
        content = _make_tasks_md(
            ("WP02", "**Dependencies**: WP01\n"),
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP02"] == ["WP01"]

    def test_plain_header_multiple_deps(self) -> None:
        content = _make_tasks_md(
            ("WP03", "Dependencies: WP01, WP02\n"),
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP03"] == ["WP01", "WP02"]

    def test_case_insensitive(self) -> None:
        content = _make_tasks_md(
            ("WP02", "DEPENDENCIES: WP01\n"),
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP02"] == ["WP01"]


# ---------------------------------------------------------------------------
# Format 3: bullet-list under "### Dependencies" heading
# ---------------------------------------------------------------------------


class TestBulletListFormat:
    def test_two_deps_with_notes(self) -> None:
        body = (
            "### Dependencies\n"
            "- WP01 (cite Divio standard)\n"
            "- WP02 (new path known)\n"
        )
        content = _make_tasks_md(("WP03", body))
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP03"] == ["WP01", "WP02"]

    def test_single_dep_no_note(self) -> None:
        body = "### Dependencies\n- WP01\n"
        content = _make_tasks_md(("WP02", body))
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP02"] == ["WP01"]

    def test_asterisk_bullet(self) -> None:
        body = "### Dependencies\n* WP01\n* WP02\n"
        content = _make_tasks_md(("WP03", body))
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP03"] == ["WP01", "WP02"]

    def test_lower_level_heading(self) -> None:
        body = "## Dependencies\n- WP01\n"
        content = _make_tasks_md(("WP02", body))
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP02"] == ["WP01"]

    def test_bullet_list_stops_at_next_heading(self) -> None:
        body = (
            "### Dependencies\n"
            "- WP01\n"
            "\n"
            "### Other Section\n"
            "- WP99\n"
        )
        content = _make_tasks_md(("WP02", body))
        result = parse_dependencies_from_tasks_md(content)
        # WP99 is under "Other Section", not Dependencies
        assert result["WP02"] == ["WP01"]


# ---------------------------------------------------------------------------
# Mixed formats in the same file
# ---------------------------------------------------------------------------


class TestMixedFormatsInSameFile:
    def test_each_wp_uses_different_format(self) -> None:
        content = (
            "## WP01\n\nNo dependencies.\n\n"
            "## WP02\n\nDepends on WP01.\n\n"
            "## WP03\n\n**Dependencies**: WP01, WP02\n\n"
            "## WP04\n\n"
            "### Dependencies\n"
            "- WP01\n"
            "- WP03\n\n"
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP01"] == []
        assert result["WP02"] == ["WP01"]
        assert result["WP03"] == ["WP01", "WP02"]
        assert result["WP04"] == ["WP01", "WP03"]


# ---------------------------------------------------------------------------
# No dependencies
# ---------------------------------------------------------------------------


class TestNoDependenciesReturnsEmpty:
    def test_wp_with_no_dep_declaration(self) -> None:
        content = _make_tasks_md(
            ("WP01", "This WP has no dependencies, just some text.\n"),
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP01"] == []

    def test_empty_tasks_md(self) -> None:
        result = parse_dependencies_from_tasks_md("")
        assert result == {}

    def test_no_wp_sections(self) -> None:
        result = parse_dependencies_from_tasks_md("# General Tasks\n\nSome text.\n")
        assert result == {}


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_same_wp_mentioned_twice_inline(self) -> None:
        body = "Depends on WP01.\nDepends on WP01.\n"
        content = _make_tasks_md(("WP02", body))
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP02"] == ["WP01"]

    def test_same_wp_across_formats(self) -> None:
        body = "Depends on WP01.\n### Dependencies\n- WP01\n"
        content = _make_tasks_md(("WP02", body))
        result = parse_dependencies_from_tasks_md(content)
        # WP01 should appear only once
        assert result["WP02"] == ["WP01"]

    def test_order_preserved_after_dedup(self) -> None:
        body = "Depends on WP02, WP01.\n"
        content = _make_tasks_md(("WP03", body))
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP03"] == ["WP02", "WP01"]


# ---------------------------------------------------------------------------
# Section header format variants
# ---------------------------------------------------------------------------


class TestSectionHeaderVariants:
    def test_work_package_header_style(self) -> None:
        content = "## Work Package WP01\n\nNo deps.\n\n## Work Package WP02\n\nDepends on WP01.\n"
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP01"] == []
        assert result["WP02"] == ["WP01"]

    def test_numeric_work_package_headers_normalize_to_wp_ids(self) -> None:
        content = (
            "## Work Package 1 — Foundation\n\nNo deps.\n\n"
            "## Work Package 2: Follow Up\n\nDepends on WP01.\n"
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP01"] == []
        assert result["WP02"] == ["WP01"]

    def test_hash_hash_hash_header_style(self) -> None:
        content = "### WP01\n\nNo deps.\n\n### WP02\n\nDepends on WP01.\n"
        result = parse_dependencies_from_tasks_md(content)
        assert result["WP02"] == ["WP01"]


# ---------------------------------------------------------------------------
# FR-304 regression: trailing ## sections must not bleed into final WP
# ---------------------------------------------------------------------------


class TestTrailingProseDoesNotBleedIntoFinalWP:
    def test_trailing_non_wp_heading_stops_final_wp_section(self) -> None:
        """FR-304: trailing ## heading does not bleed into final WP's deps."""
        content = (
            "## Plan\n\n"
            "Some intro.\n\n"
            "## WP01\n\n"
            "**Dependencies**: WP00\n\n"
            "Body of WP01.\n\n"
            "## WP02\n\n"
            "**Dependencies**: []\n\n"
            "Body of WP02.\n\n"
            "## Notes\n\n"
            "This component depends on WP01 being signed off. Depends on WP01.\n"
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result.get("WP01", []) == ["WP00"]
        # WP02 must NOT have WP01 from the ## Notes section
        assert result.get("WP02", []) == []
        assert "WP01" not in result.get("WP02", [])

    def test_trailing_appendix_heading_stops_final_wp_section(self) -> None:
        """FR-304 variant: ## Appendix at end must not bleed into final WP."""
        content = (
            "## WP01\n\n"
            "Body of WP01.\n\n"
            "## Appendix\n\n"
            "This appendix depends on WP01 for context. Depends on WP01.\n"
        )
        result = parse_dependencies_from_tasks_md(content)
        assert result.get("WP01", []) == []

    def test_subheadings_inside_wp_section_preserved(self) -> None:
        """FR-301 edge case: ### headings inside a WP section are NOT a stop boundary."""
        content = (
            "## WP01\n\n"
            "### Implementation notes\n\n"
            "Some notes.\n\n"
            "Depends on WP02\n\n"
            "## WP02\n\n"
            "Body.\n"
        )
        result = parse_dependencies_from_tasks_md(content)
        # ### sub-heading inside WP01 must not stop the section early
        assert "WP02" in result.get("WP01", [])

    def test_dependencies_h2_inside_final_wp_not_a_stop_boundary(self) -> None:
        """## Dependencies heading inside final WP is Pattern 3, not a stop boundary."""
        content = (
            "## WP01\n\n"
            "Some body.\n\n"
            "## Dependencies\n"
            "- WP00\n"
        )
        result = parse_dependencies_from_tasks_md(content)
        # ## Dependencies is a valid dep header; WP00 should be parsed
        assert result.get("WP01", []) == ["WP00"]

    def test_explicit_empty_dependencies_not_overwritten(self) -> None:
        """FR-302/FR-303: WP with no dependency text in section yields empty list."""
        content = (
            "## WP01\n\n"
            "This WP has no dependency declarations.\n\n"
            "## Notes\n\n"
            "This section depends on WP01 being done. Depends on WP01.\n"
        )
        result = parse_dependencies_from_tasks_md(content)
        # The parser found nothing in WP01's bounded section — result is []
        assert result.get("WP01", []) == []

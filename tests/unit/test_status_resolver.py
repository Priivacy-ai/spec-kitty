"""Unit tests for status_resolver module.

Tests the auto-resolution of status file conflicts including:
- Conflict marker parsing
- Lane resolution (more-done wins)
- Checkbox resolution (prefer checked)
- History array merging (chronological)
"""

from __future__ import annotations


from specify_cli.merge.status_resolver import (
    LANE_PRIORITY,
    ConflictRegion,
    extract_lane_value,
    is_status_file,
    parse_conflict_markers,
    replace_lane_value,
    resolve_checkbox_conflict,
    resolve_history_conflict,
    resolve_lane_conflict,
)


class TestConflictMarkerParsing:
    """Tests for parse_conflict_markers function."""

    def test_parse_single_conflict(self):
        content = """Some content before
<<<<<<< HEAD
our content
=======
their content
>>>>>>> branch
Some content after
"""
        regions = parse_conflict_markers(content)
        assert len(regions) == 1
        assert regions[0].ours == "our content\n"
        assert regions[0].theirs == "their content\n"

    def test_parse_multiple_conflicts(self):
        content = """<<<<<<< HEAD
first ours
=======
first theirs
>>>>>>> branch
middle content
<<<<<<< HEAD
second ours
=======
second theirs
>>>>>>> branch
"""
        regions = parse_conflict_markers(content)
        assert len(regions) == 2
        assert regions[0].ours == "first ours\n"
        assert regions[1].ours == "second ours\n"

    def test_parse_no_conflicts(self):
        content = "No conflicts here\nJust normal content"
        regions = parse_conflict_markers(content)
        assert len(regions) == 0

    def test_parse_multiline_conflict(self):
        content = """<<<<<<< HEAD
line 1
line 2
line 3
=======
different line 1
different line 2
>>>>>>> branch
"""
        regions = parse_conflict_markers(content)
        assert len(regions) == 1
        assert "line 1\nline 2\nline 3\n" == regions[0].ours
        assert "different line 1\ndifferent line 2\n" == regions[0].theirs


class TestIsStatusFile:
    """Tests for is_status_file function."""

    def test_matches_tasks_md(self):
        assert is_status_file("kitty-specs/feature/tasks.md")
        assert is_status_file("kitty-specs/feature/subfolder/tasks.md")

    def test_matches_task_file(self):
        assert is_status_file("kitty-specs/feature/tasks/WP01.md")
        assert is_status_file("kitty-specs/feature/subfolder/tasks/WP02.md")

    def test_rejects_non_status_files(self):
        assert not is_status_file("kitty-specs/feature/spec.md")
        assert not is_status_file("kitty-specs/feature/plan.md")
        assert not is_status_file("src/module.py")
        assert not is_status_file("README.md")


class TestLaneResolution:
    """Tests for lane value extraction and resolution."""

    def test_extract_lane_value(self):
        content = """---
lane: doing
---
Content here
"""
        assert extract_lane_value(content) == "doing"

    def test_extract_lane_value_with_quotes(self):
        content = 'lane: "for_review"\n'
        assert extract_lane_value(content) == "for_review"

    def test_extract_lane_value_missing(self):
        content = "No lane field here\n"
        assert extract_lane_value(content) is None

    def test_replace_lane_value(self):
        content = """---
lane: doing
---
"""
        result = replace_lane_value(content, "done")
        assert "lane: done" in result
        assert "lane: doing" not in result

    def test_lane_priority_order(self):
        # done > for_review > doing > planned
        assert LANE_PRIORITY["done"] > LANE_PRIORITY["for_review"]
        assert LANE_PRIORITY["for_review"] > LANE_PRIORITY["doing"]
        assert LANE_PRIORITY["doing"] > LANE_PRIORITY["planned"]

    def test_resolve_lane_conflict_theirs_more_done(self):
        ours = "lane: doing\n"
        theirs = "lane: for_review\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is not None
        assert "for_review" in result

    def test_resolve_lane_conflict_ours_more_done(self):
        ours = "lane: done\n"
        theirs = "lane: doing\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is not None
        assert "done" in result

    def test_resolve_lane_conflict_equal_prefers_ours(self):
        ours = "lane: doing\n"
        theirs = "lane: doing\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is not None
        assert "doing" in result

    def test_resolve_lane_conflict_missing_lane(self):
        ours = "no lane here\n"
        theirs = "lane: done\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is None


class TestCheckboxResolution:
    """Tests for checkbox conflict resolution."""

    def test_prefer_checked(self):
        ours = "- [ ] Task one\n"
        theirs = "- [x] Task one\n"
        result = resolve_checkbox_conflict(ours, theirs)
        assert "[x]" in result

    def test_keep_ours_if_already_checked(self):
        ours = "- [x] Task one\n"
        theirs = "- [ ] Task one\n"
        result = resolve_checkbox_conflict(ours, theirs)
        assert "[x]" in result

    def test_multiple_checkboxes(self):
        ours = """- [ ] Task one
- [x] Task two
- [ ] Task three"""
        theirs = """- [x] Task one
- [ ] Task two
- [x] Task three"""
        result = resolve_checkbox_conflict(ours, theirs)
        # Task one: theirs has [x], so [x]
        # Task two: ours has [x], so [x]
        # Task three: theirs has [x], so [x]
        assert result.count("[x]") == 3

    def test_extra_lines_in_theirs(self):
        ours = "- [ ] Task one\n"
        theirs = """- [x] Task one
- [x] Task two"""
        result = resolve_checkbox_conflict(ours, theirs)
        # Should preserve our lines, theirs extra line not added unless ours empty
        assert "Task one" in result


class TestHistoryResolution:
    """Tests for history array conflict resolution."""

    def test_merge_history_entries(self):
        ours = """history:
  - timestamp: "2026-01-01T10:00:00"
    action: created
    lane: planned
    agent: claude
"""
        theirs = """history:
  - timestamp: "2026-01-02T11:00:00"
    action: moved
    lane: doing
    agent: codex
"""
        result = resolve_history_conflict(ours, theirs)
        assert result is not None
        assert "2026-01-01" in result
        assert "2026-01-02" in result

    def test_deduplicates_identical_entries(self):
        ours = """history:
  - timestamp: "2026-01-01T10:00:00"
    action: created
    lane: planned
    agent: claude
"""
        theirs = """history:
  - timestamp: "2026-01-01T10:00:00"
    action: created
    lane: planned
    agent: claude
"""
        result = resolve_history_conflict(ours, theirs)
        assert result is not None
        # Should only have one entry, not duplicated
        assert result.count("2026-01-01T10:00:00") == 1

    def test_sorts_chronologically(self):
        ours = """history:
  - timestamp: "2026-01-03T10:00:00"
    action: moved
    lane: done
    agent: claude
"""
        theirs = """history:
  - timestamp: "2026-01-01T10:00:00"
    action: created
    lane: planned
    agent: codex
"""
        result = resolve_history_conflict(ours, theirs)
        assert result is not None
        # First entry should be the earlier timestamp
        idx_01 = result.find("2026-01-01")
        idx_03 = result.find("2026-01-03")
        assert idx_01 < idx_03, "Earlier timestamp should come first"

    def test_empty_history(self):
        ours = "history:\n"
        theirs = "history:\n"
        result = resolve_history_conflict(ours, theirs)
        # Empty histories should return None (nothing to merge)
        assert result is None

    def test_invalid_yaml(self):
        ours = "history:\n  - invalid: yaml: structure:\n"
        theirs = "history:\n  - timestamp: valid\n"
        result = resolve_history_conflict(ours, theirs)
        # Invalid YAML in ours should cause graceful failure
        assert result is None or "valid" in result


class TestConflictRegionDataclass:
    """Tests for ConflictRegion dataclass."""

    def test_conflict_region_attributes(self):
        region = ConflictRegion(
            start_line=5,
            end_line=10,
            ours="our content",
            theirs="their content",
            original="<<<<<<< HEAD\nour content\n=======\ntheir content\n>>>>>>> branch\n",
        )
        assert region.start_line == 5
        assert region.end_line == 10
        assert region.ours == "our content"
        assert region.theirs == "their content"
        assert "<<<<<<< HEAD" in region.original

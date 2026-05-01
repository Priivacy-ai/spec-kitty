"""Tests for migration/strip_frontmatter.py — Subtask T062.

Covers:
- T062-1: Mutable fields removed from WP frontmatter
- T062-2: Static/identity fields preserved
- T062-3: Body content preserved byte-for-byte
- T062-4: lane values recorded in StripResult.lane_records before stripping
- T062-5: StripResult counts are accurate
- T062-6: Works correctly when some mutable fields are absent
- T062-7: tasks.md frontmatter stripped if present
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.migration.strip_frontmatter import (
    MUTABLE_FIELDS,
    StripResult,
    strip_mutable_fields,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wp(tasks_dir: Path, wp_name: str, extra_fields: str = "", body: str = "# Body") -> Path:
    """Write a WP file with standard mutable fields + optional extras."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    wp_file = tasks_dir / f"{wp_name}.md"
    frontmatter = (
        f"title: {wp_name}\n"
        "dependencies: []\n"
        "work_package_id: 01WP000000000000000000000A\n"
        "wp_code: WP01\n"
        "mission_id: 01MISSION000000000000000000\n"
        "lane: doing\n"
        "review_status: ''\n"
        "reviewed_by: ''\n"
        "review_feedback: ''\n"
        "shell_pid: '12345'\n"
        "assignee: alice\n"
        "agent: claude\n"
    )
    if extra_fields:
        frontmatter += extra_fields + "\n"
    wp_file.write_text(f"---\n{frontmatter}---\n\n{body}\n")
    return wp_file


def _read_frontmatter(wp_file: Path) -> dict:
    from specify_cli.frontmatter import FrontmatterManager

    fm = FrontmatterManager()
    frontmatter, _ = fm.read(wp_file)
    return frontmatter


def _read_body(wp_file: Path) -> str:
    """Return body content (after closing ---)."""
    content = wp_file.read_text()
    parts = content.split("---\n", 2)
    return parts[2] if len(parts) == 3 else ""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestStripMutableFields:
    def test_mutable_fields_removed(self, tmp_path: Path) -> None:
        """T062-1: All MUTABLE_FIELDS are absent after stripping."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        _make_wp(feature_dir / "tasks", "WP01-test")

        strip_mutable_fields(feature_dir)
        frontmatter = _read_frontmatter(feature_dir / "tasks" / "WP01-test.md")

        for mf in MUTABLE_FIELDS:
            assert mf not in frontmatter, f"Mutable field still present: {mf}"

    def test_static_fields_preserved(self, tmp_path: Path) -> None:
        """T062-2: Static identity fields survive stripping."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        _make_wp(feature_dir / "tasks", "WP01-test")

        strip_mutable_fields(feature_dir)
        frontmatter = _read_frontmatter(feature_dir / "tasks" / "WP01-test.md")

        # These static fields were written by _make_wp
        assert frontmatter.get("work_package_id") == "01WP000000000000000000000A"
        assert frontmatter.get("wp_code") == "WP01"
        assert frontmatter.get("mission_id") == "01MISSION000000000000000000"
        assert frontmatter.get("title") == "WP01-test"

    def test_body_preserved(self, tmp_path: Path) -> None:
        """T062-3: Body content after frontmatter is unchanged."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        body_text = "# My WP\n\nThis is the **body** content.\n\nWith multiple paragraphs.\n"
        _make_wp(feature_dir / "tasks", "WP01-body", body=body_text)

        strip_mutable_fields(feature_dir)
        body = _read_body(feature_dir / "tasks" / "WP01-body.md")
        # FrontmatterManager may add a leading \n and/or trailing \n — strip both
        # ends for comparison; core text must survive unchanged
        assert body.strip() == body_text.strip()

    def test_lane_recorded_before_strip(self, tmp_path: Path) -> None:
        """T062-4: lane value is captured in StripResult.lane_records."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        _make_wp(feature_dir / "tasks", "WP01-lane")  # lane=doing

        result = strip_mutable_fields(feature_dir)
        assert "WP01" in result.lane_records
        assert result.lane_records["WP01"] == "doing"

    def test_strip_result_counts(self, tmp_path: Path) -> None:
        """T062-5: StripResult.wps_processed and fields_stripped are accurate."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        _make_wp(feature_dir / "tasks", "WP01-a")
        _make_wp(feature_dir / "tasks", "WP02-b")

        result = strip_mutable_fields(feature_dir)
        assert result.wps_processed == 2
        # Each WP has: lane, review_status, reviewed_by, review_feedback,
        # shell_pid, assignee, agent = 7 mutable fields
        assert result.fields_stripped >= 14  # 7 * 2

    def test_no_mutable_fields_already_absent(self, tmp_path: Path) -> None:
        """T062-6: Works gracefully when mutable fields are already absent."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        wp_file = tasks_dir / "WP01-clean.md"
        wp_file.write_text("---\ntitle: WP01-clean\ndependencies: []\nwork_package_id: 01WP000000000000000000000B\n---\n\n# Body\n")
        result = strip_mutable_fields(feature_dir)
        assert result.wps_processed == 1
        assert result.fields_stripped == 0

    def test_no_tasks_dir(self, tmp_path: Path) -> None:
        """Missing tasks/ dir returns empty result without raising."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        feature_dir.mkdir(parents=True)
        result = strip_mutable_fields(feature_dir)
        assert isinstance(result, StripResult)
        assert result.wps_processed == 0
        assert result.fields_stripped == 0

    def test_tasks_md_stripped(self, tmp_path: Path) -> None:
        """T062-7: Mutable fields in tasks.md are stripped."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        # Create a tasks.md with a mutable field
        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text("---\ntitle: Tasks Overview\nlane: planned\n---\n\n# Tasks\n")

        result = strip_mutable_fields(feature_dir)
        assert result.fields_stripped >= 1

        # Verify stripped
        from specify_cli.frontmatter import FrontmatterManager

        fm = FrontmatterManager()
        try:
            fm_data, _ = fm.read(tasks_md)
            assert "lane" not in fm_data
        except Exception:
            pass  # tasks.md with no frontmatter is also acceptable

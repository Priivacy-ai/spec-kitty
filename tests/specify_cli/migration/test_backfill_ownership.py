"""Tests for migration/backfill_ownership.py — Subtask T061.

Covers:
- T061-1: code_change inferred for WPs that mention src/
- T061-2: planning_artifact inferred for WPs that mention kitty-specs/
- T061-3: existing ownership fields are not overwritten
- T061-4: all three fields (execution_mode, owned_files, authoritative_surface) are written
- T061-5: gracefully handles missing tasks/ directory
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.migration.backfill_ownership import backfill_ownership


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wp(tasks_dir: Path, wp_name: str, body: str) -> Path:
    """Write a WP markdown file with the given body."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    wp_file = tasks_dir / f"{wp_name}.md"
    wp_file.write_text(f"---\ntitle: {wp_name} Title\ndependencies: []\n---\n\n{body}\n")
    return wp_file


def _read_frontmatter(wp_file: Path) -> dict:
    from specify_cli.frontmatter import FrontmatterManager

    fm = FrontmatterManager()
    frontmatter, _ = fm.read(wp_file)
    return frontmatter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBackfillOwnership:
    def test_code_change_inferred(self, tmp_path: Path) -> None:
        """T061-1: WP body mentioning src/ gets execution_mode=code_change."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        wp_file = _make_wp(
            feature_dir / "tasks",
            "WP01-code",
            "Implement src/specify_cli/context/models.py and tests/specify_cli/context/test_models.py",
        )
        backfill_ownership(feature_dir, "001-alpha")
        frontmatter = _read_frontmatter(wp_file)
        assert frontmatter["execution_mode"] == "code_change"
        assert "owned_files" in frontmatter
        assert len(frontmatter["owned_files"]) > 0
        assert "authoritative_surface" in frontmatter

    def test_planning_artifact_inferred(self, tmp_path: Path) -> None:
        """T061-2: WP body mentioning kitty-specs/ gets execution_mode=planning_artifact."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        wp_file = _make_wp(
            feature_dir / "tasks",
            "WP01-planning",
            "Create kitty-specs/001-alpha/spec.md and kitty-specs/001-alpha/plan.md",
        )
        backfill_ownership(feature_dir, "001-alpha")
        frontmatter = _read_frontmatter(wp_file)
        assert frontmatter["execution_mode"] == "planning_artifact"

    def test_existing_ownership_not_overwritten(self, tmp_path: Path) -> None:
        """T061-3: Pre-existing ownership fields are never overwritten."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        wp_file = tasks_dir / "WP01-existing.md"
        wp_file.write_text(
            "---\n"
            "title: WP01\n"
            "dependencies: []\n"
            "execution_mode: planning_artifact\n"
            "owned_files:\n"
            "- kitty-specs/001-alpha/**\n"
            "authoritative_surface: kitty-specs/001-alpha/\n"
            "---\n\n"
            "Implement src/specify_cli/context/models.py\n"
        )

        backfill_ownership(feature_dir, "001-alpha")
        frontmatter = _read_frontmatter(wp_file)

        # Should NOT have been changed to code_change even though body mentions src/
        assert frontmatter["execution_mode"] == "planning_artifact"
        assert frontmatter["owned_files"] == ["kitty-specs/001-alpha/**"]

    def test_all_three_fields_written(self, tmp_path: Path) -> None:
        """T061-4: execution_mode, owned_files, authoritative_surface all written."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        wp_file = _make_wp(
            feature_dir / "tasks",
            "WP02-full",
            "Work on src/specify_cli/migration/backfill_identity.py",
        )
        backfill_ownership(feature_dir, "001-alpha")
        frontmatter = _read_frontmatter(wp_file)
        assert "execution_mode" in frontmatter
        assert "owned_files" in frontmatter
        assert "authoritative_surface" in frontmatter

    def test_no_tasks_dir_handled_gracefully(self, tmp_path: Path) -> None:
        """T061-5: Missing tasks/ dir does not raise."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        feature_dir.mkdir(parents=True)
        # Should return without exception
        backfill_ownership(feature_dir, "001-alpha")

    def test_partial_ownership_filled_in(self, tmp_path: Path) -> None:
        """Fields present are kept; only absent fields are filled in."""
        feature_dir = tmp_path / "kitty-specs" / "001-alpha"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        wp_file = tasks_dir / "WP03-partial.md"
        wp_file.write_text("---\ntitle: WP03\ndependencies: []\nexecution_mode: code_change\n---\n\nWork on src/specify_cli/foo.py\n")

        backfill_ownership(feature_dir, "001-alpha")
        frontmatter = _read_frontmatter(wp_file)
        # execution_mode preserved
        assert frontmatter["execution_mode"] == "code_change"
        # owned_files and authoritative_surface filled in
        assert "owned_files" in frontmatter
        assert "authoritative_surface" in frontmatter

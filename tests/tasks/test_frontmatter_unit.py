"""Unit tests for FrontmatterManager.read() edge-cases — malformed input.

Covers error paths: missing frontmatter, unclosed frontmatter, and None/empty
YAML body.  All tests are pure in-memory (tmp_path only, no real WP files).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.frontmatter import FrontmatterError, FrontmatterManager

pytestmark = pytest.mark.fast


@pytest.fixture
def fm() -> FrontmatterManager:
    """Return a fresh FrontmatterManager instance."""
    return FrontmatterManager()


class TestReadMalformedInput:
    """FrontmatterManager.read() raises FrontmatterError on bad input."""

    def test_no_frontmatter_raises(self, tmp_path: Path, fm: FrontmatterManager) -> None:
        """A file that does not start with '---' raises FrontmatterError."""
        # Arrange
        f = tmp_path / "WP01.md"
        f.write_text("# No frontmatter here\n", encoding="utf-8")

        # Assumption check
        assert not f.read_text().startswith("---")

        # Act / Assert
        with pytest.raises(FrontmatterError, match="no frontmatter"):
            fm.read(f)

    def test_unclosed_frontmatter_raises(self, tmp_path: Path, fm: FrontmatterManager) -> None:
        """A file with an opening '---' but no closing '---' raises FrontmatterError."""
        # Arrange
        f = tmp_path / "WP02.md"
        f.write_text("---\ntitle: orphan\n# No closing delimiter\n", encoding="utf-8")

        # Assumption check
        assert f.read_text().startswith("---")

        # Act / Assert
        with pytest.raises(FrontmatterError, match="no closing"):
            fm.read(f)

    def test_file_not_found_raises(self, tmp_path: Path, fm: FrontmatterManager) -> None:
        """Reading a nonexistent file raises FrontmatterError."""
        # Arrange
        f = tmp_path / "nonexistent.md"

        # Assumption check
        assert not f.exists()

        # Act / Assert
        with pytest.raises(FrontmatterError, match="not found"):
            fm.read(f)

    def test_empty_frontmatter_block_returns_empty_dict(self, tmp_path: Path, fm: FrontmatterManager) -> None:
        """An empty YAML block between '---' delimiters returns an empty dict.

        Uses a non-WP filename to avoid the pre-0.11.0 dependencies backfill path.
        """
        # Arrange
        f = tmp_path / "spec.md"
        f.write_text("---\n---\n# Body\n", encoding="utf-8")

        # Assumption check
        assert f.read_text().startswith("---\n---")

        # Act
        frontmatter, body = fm.read(f)

        # Assert
        assert frontmatter == {}
        assert "Body" in body


class TestReadValidInput:
    """FrontmatterManager.read() parses well-formed frontmatter correctly."""

    def test_reads_simple_fields(self, tmp_path: Path, fm: FrontmatterManager) -> None:
        """Standard WP frontmatter fields round-trip correctly."""
        # Arrange
        content = (
            "---\nwork_package_id: WP01\ntitle: Setup\nlane: planned\ndependencies: []\n---\n# Setup\n\nBody text.\n"
        )
        f = tmp_path / "WP01.md"
        f.write_text(content, encoding="utf-8")

        # Assumption check
        assert f.exists()

        # Act
        frontmatter, body = fm.read(f)

        # Assert
        assert frontmatter["work_package_id"] == "WP01"
        assert frontmatter["lane"] == "planned"
        assert frontmatter["dependencies"] == []
        assert "Body text." in body

    def test_wp_file_gets_dependencies_backfilled(self, tmp_path: Path, fm: FrontmatterManager) -> None:
        """A WP file missing 'dependencies' gets it backfilled as [] (0.11.0 compat)."""
        # Arrange
        content = "---\nwork_package_id: WP01\ntitle: No deps field\n---\n# Body\n"
        f = tmp_path / "WP01.md"
        f.write_text(content, encoding="utf-8")

        # Assumption check
        assert "dependencies" not in content

        # Act
        frontmatter, _ = fm.read(f)

        # Assert
        assert "dependencies" in frontmatter
        assert frontmatter["dependencies"] == []

    def test_non_wp_file_no_dependencies_backfill(self, tmp_path: Path, fm: FrontmatterManager) -> None:
        """A non-WP file (e.g. spec.md) does NOT get dependencies backfilled."""
        # Arrange
        content = "---\ntitle: A spec file\n---\n# Spec\n"
        f = tmp_path / "spec.md"
        f.write_text(content, encoding="utf-8")

        # Assumption check
        assert not f.name.startswith("WP")

        # Act
        frontmatter, _ = fm.read(f)

        # Assert
        assert "dependencies" not in frontmatter

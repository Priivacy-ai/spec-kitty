"""T019 (WP tasks) / T020 — Tests for MarkdownRulesWriter.

Covers append_mode=True (CLAUDE.md-style) and append_mode=False (standalone file),
idempotency, removal, and atomicity invariants.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.session_presence.content import SECTION_CLOSE, SECTION_OPEN, SessionPresenceContent
from specify_cli.session_presence.writers.markdown_rules import MarkdownRulesWriter

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_wp07_atomic_writer_preserves_foreign_temp_sentinel(tmp_path: Path) -> None:
    sentinel = tmp_path / "AGENTS.md.tmp"
    sentinel.write_bytes(b"foreign in-flight content")
    writer = MarkdownRulesWriter("codex", "AGENTS.md", True)
    writer.write(tmp_path, SessionPresenceContent("3.2.0", "example", "healthy", None))
    assert sentinel.read_bytes() == b"foreign in-flight content"


def test_wp07_mixed_markdown_preserves_exact_prefix_suffix(tmp_path: Path) -> None:
    writer = MarkdownRulesWriter("codex", "AGENTS.md", True)
    old = SessionPresenceContent("0.1.0", "example", "healthy", None)
    new = SessionPresenceContent("3.2.0", "example", "healthy", None)
    prefix, suffix = b"# foreign\r\n\r\n\r\n", b"\r\n\r\n# footer with no newline"
    target = tmp_path / "AGENTS.md"
    target.write_bytes(prefix + old.render().strip().replace("\n", "\r\n").encode() + suffix)
    writer.write(tmp_path, new)
    assert target.read_bytes() == prefix + new.render().strip().replace("\n", "\r\n").encode() + suffix


def test_wp07_same_version_health_difference_has_no_churn(tmp_path: Path) -> None:
    from tests.upgrade.preview_support.snapshot import assert_unchanged, snapshot

    writer = MarkdownRulesWriter("codex", "AGENTS.md", True)
    writer.write(tmp_path, SessionPresenceContent("3.2.0", "example", "upgrade-available", "4.0.0"))
    before = snapshot({"project": tmp_path})
    writer.write(tmp_path, SessionPresenceContent("3.2.0", "example", "healthy", None))
    assert_unchanged(before, snapshot({"project": tmp_path}))


def test_wp07_oracle_rejects_unowned_overwrite_and_same_byte_churn(tmp_path: Path) -> None:
    import os
    from tests.upgrade.preview_support.snapshot import assert_unchanged, snapshot

    writer = MarkdownRulesWriter("codex", "AGENTS.md", True)
    target = tmp_path / "AGENTS.md"
    target.write_bytes(b"# foreign\n")
    writer.write(tmp_path, SessionPresenceContent("3.2.0", "example", "healthy", None))
    original = target.read_bytes()
    before = snapshot({"project": tmp_path})
    target.write_bytes(original.replace(b"# foreign", b"# clobbered"))
    with pytest.raises(AssertionError, match="Filesystem changed"):
        assert_unchanged(before, snapshot({"project": tmp_path}))
    target.write_bytes(original)
    before = snapshot({"project": tmp_path})
    os.utime(target, ns=(1_000_000_000, 1_000_000_000))
    with pytest.raises(AssertionError, match="Filesystem changed"):
        assert_unchanged(before, snapshot({"project": tmp_path}))


def test_wp07_existing_markdown_second_write_has_no_churn(tmp_path: Path) -> None:
    import os
    from tests.upgrade.preview_support.snapshot import assert_unchanged, snapshot

    writer = MarkdownRulesWriter("codex", "AGENTS.md", True)
    content = SessionPresenceContent("3.2.0", "example", "healthy", None)
    writer.write(tmp_path, content)
    target = tmp_path / "AGENTS.md"
    target.chmod(0o640)
    os.utime(target, ns=(1_000_000_000, 1_000_000_000))
    before = snapshot({"project": tmp_path})
    writer.write(tmp_path, content)
    assert_unchanged(before, snapshot({"project": tmp_path}))


def _make_content(
    version: str = "3.2.0",
    slug: str = "test-project",
    health: str = "healthy",
    available: str | None = None,
) -> SessionPresenceContent:
    return SessionPresenceContent(version, slug, health, available)


class TestAppendModeTrue:
    """Tests for MarkdownRulesWriter with append_mode=True (e.g. CLAUDE.md)."""

    def _writer(self, rules_path: str = "CLAUDE.md") -> MarkdownRulesWriter:
        return MarkdownRulesWriter(harness_key="test", rules_path=rules_path, append_mode=True)

    def test_first_write_creates_file(self, tmp_path: Path) -> None:
        writer = self._writer()
        writer.write(tmp_path, _make_content())
        target = tmp_path / "CLAUDE.md"
        assert target.exists()
        assert SECTION_OPEN in target.read_text(encoding="utf-8")

    def test_first_write_on_existing_file_appends(self, tmp_path: Path) -> None:
        target = tmp_path / "CLAUDE.md"
        target.write_text("# Existing content\n", encoding="utf-8")
        writer = self._writer()
        writer.write(tmp_path, _make_content())
        text = target.read_text(encoding="utf-8")
        assert "# Existing content" in text
        assert SECTION_OPEN in text

    def test_rewrite_replaces_section_no_duplicates(self, tmp_path: Path) -> None:
        writer = self._writer()
        content = _make_content()
        writer.write(tmp_path, content)
        writer.write(tmp_path, content)
        text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert text.count(SECTION_OPEN) == 1

    def test_rewrite_preserves_surrounding_content(self, tmp_path: Path) -> None:
        target = tmp_path / "CLAUDE.md"
        target.write_text("# Header\n\n# Footer\n", encoding="utf-8")
        writer = self._writer()
        writer.write(tmp_path, _make_content())
        writer.write(tmp_path, _make_content())
        text = target.read_text(encoding="utf-8")
        assert "# Header" in text

    def test_remove_strips_section_preserves_content(self, tmp_path: Path) -> None:
        target = tmp_path / "CLAUDE.md"
        target.write_text("# Before\n\n# After\n", encoding="utf-8")
        writer = self._writer()
        writer.write(tmp_path, _make_content())
        writer.remove(tmp_path)
        text = target.read_text(encoding="utf-8")
        assert SECTION_OPEN not in text
        assert SECTION_CLOSE not in text
        assert "# Before" in text

    def test_remove_noop_when_no_section(self, tmp_path: Path) -> None:
        target = tmp_path / "CLAUDE.md"
        target.write_text("# Nothing here\n", encoding="utf-8")
        writer = self._writer()
        writer.remove(tmp_path)  # Should not raise
        assert target.read_text(encoding="utf-8") == "# Nothing here\n"

    def test_remove_noop_when_file_absent(self, tmp_path: Path) -> None:
        writer = self._writer("nonexistent.md")
        writer.remove(tmp_path)  # Must not raise

    def test_has_presence_true_when_section_present(self, tmp_path: Path) -> None:
        writer = self._writer()
        writer.write(tmp_path, _make_content())
        assert writer.has_presence(tmp_path) is True

    def test_has_presence_false_when_section_absent(self, tmp_path: Path) -> None:
        target = tmp_path / "CLAUDE.md"
        target.write_text("# No section\n", encoding="utf-8")
        writer = self._writer()
        assert writer.has_presence(tmp_path) is False

    def test_has_presence_false_when_file_absent(self, tmp_path: Path) -> None:
        writer = self._writer()
        assert writer.has_presence(tmp_path) is False


class TestAppendModeFalse:
    """Tests for MarkdownRulesWriter with append_mode=False (standalone file)."""

    def _writer(self, rules_path: str = ".cursor/rules/spec-kitty.mdc") -> MarkdownRulesWriter:
        return MarkdownRulesWriter(harness_key="cursor", rules_path=rules_path, append_mode=False)

    def test_first_write_creates_file(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".cursor" / "rules"
        rules_dir.mkdir(parents=True)
        writer = self._writer()
        writer.write(tmp_path, _make_content())
        target = tmp_path / ".cursor" / "rules" / "spec-kitty.mdc"
        assert target.exists()
        text = target.read_text(encoding="utf-8")
        assert SECTION_OPEN in text
        assert SECTION_CLOSE in text

    def test_rewrite_replaces_entire_file(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".cursor" / "rules"
        rules_dir.mkdir(parents=True)
        writer = self._writer()
        writer.write(tmp_path, _make_content())
        writer.write(tmp_path, _make_content(version="3.3.0"))
        target = tmp_path / ".cursor" / "rules" / "spec-kitty.mdc"
        text = target.read_text(encoding="utf-8")
        assert text.count(SECTION_OPEN) == 1
        assert "3.3.0" in text

    def test_remove_deletes_file(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".cursor" / "rules"
        rules_dir.mkdir(parents=True)
        writer = self._writer()
        writer.write(tmp_path, _make_content())
        writer.remove(tmp_path)
        target = tmp_path / ".cursor" / "rules" / "spec-kitty.mdc"
        assert not target.exists()

    def test_can_write_false_when_parent_dir_absent(self, tmp_path: Path) -> None:
        writer = self._writer()
        # Parent .cursor/rules/ does not exist
        assert writer.can_write(tmp_path) is False

    def test_can_write_true_when_parent_dir_present(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / ".cursor" / "rules"
        rules_dir.mkdir(parents=True)
        writer = self._writer()
        assert writer.can_write(tmp_path) is True


class TestAtomicity:
    def test_custom_prelude_in_old_managed_block_is_preserved(self, tmp_path: Path) -> None:
        target = tmp_path / "CLAUDE.md"
        original = _make_content(version="0.1.0").render().replace("Two usage patterns:", "My custom instruction.\n\nTwo usage patterns:")
        target.write_text(original, encoding="utf-8")
        before = target.stat()
        writer = MarkdownRulesWriter(harness_key="test", rules_path="CLAUDE.md", append_mode=True)
        writer.write(tmp_path, _make_content())
        assert target.read_text(encoding="utf-8") == original
        assert target.stat().st_mtime_ns == before.st_mtime_ns

    def test_original_file_unchanged_on_os_replace_failure(self, tmp_path: Path) -> None:
        """Atomicity: if os.replace raises, original file must be unchanged."""
        target = tmp_path / "CLAUDE.md"
        original_content = "# Original content\n"
        target.write_text(original_content, encoding="utf-8")

        writer = MarkdownRulesWriter(harness_key="test", rules_path="CLAUDE.md", append_mode=True)

        with patch("os.replace", side_effect=OSError("disk full")), pytest.raises(OSError):
            writer.write(tmp_path, _make_content())

        # Original file should be unchanged
        assert target.read_text(encoding="utf-8") == original_content

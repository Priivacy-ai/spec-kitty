"""T027 — Tests for SkillsPreambleWriter.

Covers:
- Structural behaviour (same as AgentsMdWriter; writes to AGENTS.md)
- Inheritance checks (SkillsPreambleWriter IS-A MarkdownRulesWriter)
- Registry returns correct writer types for Pattern D keys
- Pattern C keys return AgentsMdWriter (not SkillsPreambleWriter)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.session_presence.content import SECTION_CLOSE, SECTION_OPEN, SessionPresenceContent
from specify_cli.session_presence.writers.agents_md import AgentsMdWriter
from specify_cli.session_presence.writers.markdown_rules import MarkdownRulesWriter
from specify_cli.session_presence.writers.registry import get_writer
from specify_cli.session_presence.writers.skills_preamble import SkillsPreambleWriter

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_content(
    version: str = "3.2.0",
    slug: str = "test-project",
    health: str = "healthy",
    available: str | None = None,
) -> SessionPresenceContent:
    return SessionPresenceContent(version, slug, health, available)


def _skills_writer(harness_key: str = "pi") -> SkillsPreambleWriter:
    return SkillsPreambleWriter(harness_key)


# ---------------------------------------------------------------------------
# Inheritance
# ---------------------------------------------------------------------------

class TestSkillsPreambleWriterInheritance:
    def test_is_instance_of_markdown_rules_writer(self) -> None:
        assert isinstance(SkillsPreambleWriter("pi"), MarkdownRulesWriter)

    def test_is_instance_of_agents_md_writer(self) -> None:
        assert isinstance(SkillsPreambleWriter("pi"), AgentsMdWriter)

    def test_defaults_to_agents_md_path(self) -> None:
        writer = SkillsPreambleWriter("vibe")
        assert writer.rules_path == "AGENTS.md"
        assert writer.append_mode is True


# ---------------------------------------------------------------------------
# can_write
# ---------------------------------------------------------------------------

class TestSkillsPreambleWriterCanWrite:
    def test_can_write_always_true(self, tmp_path: Path) -> None:
        assert _skills_writer().can_write(tmp_path) is True

    def test_can_write_true_even_when_dir_is_empty(self, tmp_path: Path) -> None:
        assert _skills_writer("letta").can_write(tmp_path) is True


# ---------------------------------------------------------------------------
# has_presence
# ---------------------------------------------------------------------------

class TestSkillsPreambleWriterHasPresence:
    def test_false_when_agents_md_absent(self, tmp_path: Path) -> None:
        assert _skills_writer().has_presence(tmp_path) is False

    def test_false_when_no_section_in_agents_md(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# No section\n", encoding="utf-8")
        assert _skills_writer().has_presence(tmp_path) is False

    def test_true_after_write(self, tmp_path: Path) -> None:
        writer = _skills_writer()
        writer.write(tmp_path, _make_content())
        assert writer.has_presence(tmp_path) is True


# ---------------------------------------------------------------------------
# write
# ---------------------------------------------------------------------------

class TestSkillsPreambleWriterWrite:
    def test_first_write_creates_agents_md(self, tmp_path: Path) -> None:
        writer = _skills_writer()
        writer.write(tmp_path, _make_content())
        target = tmp_path / "AGENTS.md"
        assert target.exists()
        text = target.read_text(encoding="utf-8")
        assert SECTION_OPEN in text
        assert SECTION_CLOSE in text

    def test_second_write_replaces_section_no_duplicate(self, tmp_path: Path) -> None:
        writer = _skills_writer()
        writer.write(tmp_path, _make_content())
        writer.write(tmp_path, _make_content(version="3.3.0"))
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert text.count(SECTION_OPEN) == 1
        assert "3.3.0" in text

    def test_preserves_existing_agents_md_content(self, tmp_path: Path) -> None:
        target = tmp_path / "AGENTS.md"
        target.write_text("# Existing content\n", encoding="utf-8")
        writer = _skills_writer()
        writer.write(tmp_path, _make_content())
        text = target.read_text(encoding="utf-8")
        assert "# Existing content" in text
        assert SECTION_OPEN in text


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

class TestSkillsPreambleWriterRemove:
    def test_remove_strips_section_preserves_other_content(self, tmp_path: Path) -> None:
        target = tmp_path / "AGENTS.md"
        target.write_text("# Header\n", encoding="utf-8")
        writer = _skills_writer()
        writer.write(tmp_path, _make_content())
        writer.remove(tmp_path)
        text = target.read_text(encoding="utf-8")
        assert SECTION_OPEN not in text
        assert "# Header" in text

    def test_remove_noop_when_section_absent(self, tmp_path: Path) -> None:
        target = tmp_path / "AGENTS.md"
        original = "# No section\n"
        target.write_text(original, encoding="utf-8")
        _skills_writer().remove(tmp_path)  # Must not raise
        assert target.read_text(encoding="utf-8") == original

    def test_remove_noop_when_file_absent(self, tmp_path: Path) -> None:
        _skills_writer().remove(tmp_path)  # Must not raise


# ---------------------------------------------------------------------------
# Registry checks for Pattern D keys
# ---------------------------------------------------------------------------

class TestSkillsPreambleWriterRegistry:
    def test_get_writer_pi_returns_skills_preamble_writer(self) -> None:
        result = get_writer("pi")
        assert isinstance(result, SkillsPreambleWriter)

    def test_get_writer_vibe_returns_skills_preamble_writer(self) -> None:
        result = get_writer("vibe")
        assert isinstance(result, SkillsPreambleWriter)

    def test_get_writer_letta_returns_skills_preamble_writer(self) -> None:
        result = get_writer("letta")
        assert isinstance(result, SkillsPreambleWriter)

    def test_get_writer_codex_returns_agents_md_not_skills_preamble(self) -> None:
        """codex is Pattern C, not Pattern D — should be AgentsMdWriter, not SkillsPreambleWriter."""
        result = get_writer("codex")
        assert isinstance(result, AgentsMdWriter)
        assert not isinstance(result, SkillsPreambleWriter)

    def test_get_writer_opencode_returns_agents_md_not_skills_preamble(self) -> None:
        result = get_writer("opencode")
        assert isinstance(result, AgentsMdWriter)
        assert not isinstance(result, SkillsPreambleWriter)

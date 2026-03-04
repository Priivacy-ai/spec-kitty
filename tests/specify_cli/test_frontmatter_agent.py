"""Tests for extract_agent_identity() and ActorIdentity round-trip in frontmatter.

Covers T006 (read path), T007 (write path), T008 (WorkPackage.agent), T009 (unknown tools).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.frontmatter import (
    FrontmatterManager,
    extract_agent_identity,
    read_frontmatter,
    write_frontmatter,
)
from specify_cli.identity import ActorIdentity
from specify_cli.tasks_support import WorkPackage, split_frontmatter

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_frontmatter(**kwargs: str | list | None) -> str:
    """Build a minimal frontmatter string from keyword arguments."""
    lines = []
    for k, v in kwargs.items():
        if v is None:
            lines.append(f"{k}: ''")
        elif isinstance(v, list):
            lines.append(f"{k}: {v!r}")
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines) + "\n"


def _wp_from_frontmatter(frontmatter_text: str) -> WorkPackage:
    """Construct a minimal WorkPackage from raw frontmatter text."""
    full = f"---\n{frontmatter_text}---\nbody\n"
    front, body, padding = split_frontmatter(full)
    return WorkPackage(
        feature="test",
        path=Path("/fake/WP01.md"),
        current_lane="planned",
        relative_subpath=Path("WP01.md"),
        frontmatter=front,
        body=body,
        padding=padding,
    )


# ---------------------------------------------------------------------------
# T006 – extract_agent_identity read path
# ---------------------------------------------------------------------------


class TestExtractAgentIdentityRead:
    def test_scalar_legacy_string(self):
        fm = _make_frontmatter(agent='"claude"')
        result = extract_agent_identity(fm)
        assert result is not None
        assert result.tool == "claude"
        assert result.model == "unknown"
        assert result.profile == "unknown"
        assert result.role == "unknown"

    def test_scalar_unquoted_string(self):
        fm = _make_frontmatter(agent="claude")
        result = extract_agent_identity(fm)
        assert result is not None
        assert result.tool == "claude"

    def test_structured_mapping(self):
        fm = "agent:\n  tool: claude\n  model: opus\n  profile: impl\n  role: impl\n"
        result = extract_agent_identity(fm)
        assert result == ActorIdentity(tool="claude", model="opus", profile="impl", role="impl")

    def test_mapping_partial_fields(self):
        fm = "agent:\n  tool: gemini\n  model: pro\n"
        result = extract_agent_identity(fm)
        assert result is not None
        assert result.tool == "gemini"
        assert result.model == "pro"
        assert result.profile == "unknown"
        assert result.role == "unknown"

    def test_empty_agent_returns_none(self):
        fm = _make_frontmatter(agent="''")
        result = extract_agent_identity(fm)
        assert result is None

    def test_missing_agent_returns_none(self):
        fm = _make_frontmatter(lane="planned")
        result = extract_agent_identity(fm)
        assert result is None

    def test_unknown_tool_name_preserved(self):
        fm = "agent:\n  tool: my-custom-agent\n  model: v1\n  profile: p\n  role: r\n"
        result = extract_agent_identity(fm)
        assert result is not None
        assert result.tool == "my-custom-agent"
        assert result.model == "v1"

    def test_compact_colon_format(self):
        fm = _make_frontmatter(agent="claude:opus:impl:impl")
        result = extract_agent_identity(fm)
        assert result == ActorIdentity(tool="claude", model="opus", profile="impl", role="impl")


# ---------------------------------------------------------------------------
# T007 – frontmatter write path always emits mapping
# ---------------------------------------------------------------------------


class TestFrontmatterWriteAgent:
    def test_actor_identity_serialised_as_mapping(self, tmp_path: Path):
        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: planned\nagent: ''\n---\nbody\n",
            encoding="utf-8",
        )
        identity = ActorIdentity(tool="claude", model="opus-4", profile="implementer", role="implementer")
        manager = FrontmatterManager()
        manager.update_field(wp_file, "agent", identity)

        content = wp_file.read_text()
        assert "agent:" in content
        assert "tool: claude" in content
        assert "model: opus-4" in content
        assert "profile: implementer" in content
        assert "role: implementer" in content
        # Must NOT write a single-line scalar for agent
        assert "agent: claude" not in content

    def test_write_read_round_trip_preserves_all_fields(self, tmp_path: Path):
        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: planned\nagent: ''\n---\nbody\n",
            encoding="utf-8",
        )
        original = ActorIdentity(tool="codex", model="gpt4o", profile="reviewer", role="reviewer")
        manager = FrontmatterManager()
        manager.update_field(wp_file, "agent", original)

        # Read back via extract_agent_identity
        frontmatter, _ = read_frontmatter(wp_file)
        agent_val = frontmatter.get("agent")
        assert isinstance(agent_val, dict)
        result = ActorIdentity.from_dict(agent_val)
        assert result == original

    def test_unknown_tool_round_trip(self, tmp_path: Path):
        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: planned\nagent: ''\n---\nbody\n",
            encoding="utf-8",
        )
        original = ActorIdentity(tool="my-custom-agent", model="v1", profile="p", role="r")
        manager = FrontmatterManager()
        manager.update_field(wp_file, "agent", original)

        frontmatter, _ = read_frontmatter(wp_file)
        result = ActorIdentity.from_dict(frontmatter["agent"])
        assert result == original
        assert result.tool == "my-custom-agent"

    def test_all_unknown_fields_still_writes_mapping(self, tmp_path: Path):
        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: planned\nagent: ''\n---\nbody\n",
            encoding="utf-8",
        )
        identity = ActorIdentity(tool="cursor", model="unknown", profile="unknown", role="unknown")
        manager = FrontmatterManager()
        manager.update_field(wp_file, "agent", identity)

        content = wp_file.read_text()
        # Should still write the full mapping, not collapse to scalar
        assert "tool: cursor" in content
        assert "model: unknown" in content


# ---------------------------------------------------------------------------
# T008 – WorkPackage.agent returns ActorIdentity | None
# ---------------------------------------------------------------------------


class TestWorkPackageAgentProperty:
    def test_scalar_agent_returns_actor_identity(self):
        wp = _wp_from_frontmatter('work_package_id: WP01\nagent: "claude"\n')
        result = wp.agent
        assert isinstance(result, ActorIdentity)
        assert result.tool == "claude"

    def test_structured_agent_returns_actor_identity(self):
        fm = "work_package_id: WP01\nagent:\n  tool: codex\n  model: gpt4o\n  profile: reviewer\n  role: reviewer\n"
        wp = _wp_from_frontmatter(fm)
        result = wp.agent
        assert isinstance(result, ActorIdentity)
        assert result.tool == "codex"
        assert result.model == "gpt4o"

    def test_missing_agent_returns_none(self):
        wp = _wp_from_frontmatter("work_package_id: WP01\nlane: planned\n")
        assert wp.agent is None

    def test_empty_agent_returns_none(self):
        wp = _wp_from_frontmatter("work_package_id: WP01\nagent: ''\n")
        assert wp.agent is None

    def test_agent_str_returns_tool_name(self):
        wp = _wp_from_frontmatter('work_package_id: WP01\nagent: "gemini"\n')
        # __str__ compatibility for legacy callers
        assert str(wp.agent) == "gemini"


# ---------------------------------------------------------------------------
# T009 – Unknown tool name round-trip
# ---------------------------------------------------------------------------


class TestUnknownToolRoundTrip:
    def test_read_write_read_unknown_tool(self, tmp_path: Path):
        wp_file = tmp_path / "WP01.md"
        custom_frontmatter = (
            "---\n"
            "work_package_id: WP01\n"
            "title: Test\n"
            "lane: planned\n"
            "agent:\n"
            "  tool: my-custom-agent\n"
            "  model: v1\n"
            "  profile: tester\n"
            "  role: tester\n"
            "---\nbody\n"
        )
        wp_file.write_text(custom_frontmatter, encoding="utf-8")

        # Read
        frontmatter, body = read_frontmatter(wp_file)
        agent = ActorIdentity.from_dict(frontmatter["agent"])
        assert agent.tool == "my-custom-agent"
        assert agent.model == "v1"

        # Write back
        write_frontmatter(wp_file, frontmatter, body)
        content = wp_file.read_text()
        assert "tool: my-custom-agent" in content
        assert "model: v1" in content

        # Read again — verify faithful preservation
        frontmatter2, _ = read_frontmatter(wp_file)
        agent2 = ActorIdentity.from_dict(frontmatter2["agent"])
        assert agent2 == agent

    def test_no_validation_rejects_unknown_tools(self):
        fm = "agent:\n  tool: some-unknown-llm\n  model: alpha\n"
        result = extract_agent_identity(fm)
        assert result is not None
        assert result.tool == "some-unknown-llm"

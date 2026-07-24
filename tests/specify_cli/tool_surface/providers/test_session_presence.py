"""Unit tests for ``tool_surface.providers.session_presence``."""

from __future__ import annotations

from pathlib import Path

from specify_cli.tool_surface.enums import ToolSurfaceKind
from specify_cli.tool_surface.providers.command_skills import (
    command_skill_definition,
)
from specify_cli.tool_surface.providers.protocol import ReportingSurfaceProvider
from specify_cli.tool_surface.providers.session_presence import (
    SessionPresenceProvider,
    context_file_definition,
    hook_definition,
    rule_definition,
)
from specify_cli.tool_surface.status import (
    STATE_MISSING,
    STATE_NOT_APPLICABLE,
    STATE_PRESENT,
)

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_provider_satisfies_reporting_protocol() -> None:
    provider = SessionPresenceProvider()
    assert isinstance(provider, ReportingSurfaceProvider)
    assert provider.provider_key == "session_presence"


def test_can_handle_context_file() -> None:
    provider = SessionPresenceProvider()
    assert provider.can_handle(context_file_definition()) is True


def test_can_handle_hook() -> None:
    provider = SessionPresenceProvider()
    assert provider.can_handle(hook_definition()) is True


def test_can_handle_rule() -> None:
    provider = SessionPresenceProvider()
    assert provider.can_handle(rule_definition()) is True


def test_cannot_handle_command_skill() -> None:
    provider = SessionPresenceProvider()
    assert provider.can_handle(command_skill_definition()) is False


def test_definitions_use_distinct_kinds() -> None:
    assert context_file_definition().kind == ToolSurfaceKind.CONTEXT_FILE
    assert hook_definition().kind == ToolSurfaceKind.HOOK
    assert rule_definition().kind == ToolSurfaceKind.RULE
    # session_presence is a provider name, never a ToolSurfaceKind value.
    assert "session_presence" not in {k.value for k in ToolSurfaceKind}


def test_session_presence_is_provider_key_not_a_kind() -> None:
    for definition in (
        context_file_definition(),
        hook_definition(),
        rule_definition(),
    ):
        assert definition.provider_key == "session_presence"
        assert str(definition.kind) != "session_presence"


def test_expand_claude_context_file(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    provider = SessionPresenceProvider()
    instances = provider.expand(
        context_file_definition(), "claude", tmp_path
    )
    assert len(instances) == 1
    inst = instances[0]
    assert inst.definition.kind == ToolSurfaceKind.CONTEXT_FILE
    assert inst.path == tmp_path / ".claude" / "CLAUDE.md"
    assert inst.owner == "claude"


def test_expand_claude_hooks_two_entries(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    provider = SessionPresenceProvider()
    instances = provider.expand(hook_definition(), "claude", tmp_path)
    # SessionStart and Stop -> two hook instances.
    assert len(instances) == 2
    assert all(i.definition.kind == ToolSurfaceKind.HOOK for i in instances)
    assert all(i.path.name == "settings.json" for i in instances)


def test_expand_filters_to_requested_kind(tmp_path: Path) -> None:
    """A context_file definition must not leak hook instances."""
    (tmp_path / ".claude").mkdir()
    provider = SessionPresenceProvider()
    ctx = provider.expand(context_file_definition(), "claude", tmp_path)
    assert all(i.definition.kind == ToolSurfaceKind.CONTEXT_FILE for i in ctx)


def test_expand_cursor_yields_rule(tmp_path: Path) -> None:
    (tmp_path / ".cursor").mkdir()
    provider = SessionPresenceProvider()
    instances = provider.expand(rule_definition(), "cursor", tmp_path)
    assert len(instances) == 1
    assert instances[0].definition.kind == ToolSurfaceKind.RULE
    assert instances[0].path.name.endswith(".mdc")


def test_expand_codex_context_file_is_agents_md(tmp_path: Path) -> None:
    provider = SessionPresenceProvider()
    instances = provider.expand(context_file_definition(), "codex", tmp_path)
    assert len(instances) == 1
    assert instances[0].path == tmp_path / "AGENTS.md"
    assert instances[0].definition.kind == ToolSurfaceKind.CONTEXT_FILE


def test_expand_per_tool_paths_differ(tmp_path: Path) -> None:
    """Each tool has distinct session presence paths."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".cursor").mkdir()
    provider = SessionPresenceProvider()
    claude = provider.expand(context_file_definition(), "claude", tmp_path)[0]
    codex = provider.expand(context_file_definition(), "codex", tmp_path)[0]
    cursor = provider.expand(rule_definition(), "cursor", tmp_path)[0]
    paths = {claude.path, codex.path, cursor.path}
    assert len(paths) == 3


def test_expand_null_writer_yields_research_gap(tmp_path: Path) -> None:
    provider = SessionPresenceProvider()
    instances = provider.expand(context_file_definition(), "qwen", tmp_path)
    assert len(instances) == 1
    status = provider.probe(instances[0])
    assert status.state == STATE_NOT_APPLICABLE
    assert status.findings[0].code == "research-gap-surface"
    assert status.findings[0].severity == "info"


def test_probe_detects_missing_context_file(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    provider = SessionPresenceProvider()
    instance = provider.expand(
        context_file_definition(), "claude", tmp_path
    )[0]
    status = provider.probe(instance)
    assert status.state == STATE_MISSING
    assert status.findings[0].code == "context-file-missing"
    assert status.findings[0].repair_command is not None


def test_probe_detects_missing_hook(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    provider = SessionPresenceProvider()
    instance = provider.expand(hook_definition(), "claude", tmp_path)[0]
    status = provider.probe(instance)
    assert status.state == STATE_MISSING
    assert status.findings[0].code == "session-presence-incomplete"


def test_probe_present_after_repair(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    provider = SessionPresenceProvider()
    instance = provider.expand(
        context_file_definition(), "claude", tmp_path
    )[0]
    missing = provider.probe(instance)
    assert missing.state == STATE_MISSING
    result = provider.repair(tmp_path, [missing])
    assert result.repaired
    assert not result.failed
    refreshed = provider.probe(instance)
    assert refreshed.state == STATE_PRESENT
    assert (tmp_path / ".claude" / "CLAUDE.md").exists()


def test_repair_hook_registers_entries(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    provider = SessionPresenceProvider()
    instances = provider.expand(hook_definition(), "claude", tmp_path)
    statuses = [provider.probe(i) for i in instances]
    result = provider.repair(tmp_path, statuses)
    assert result.repaired
    assert (tmp_path / ".claude" / "settings.json").exists()
    for instance in instances:
        assert provider.probe(instance).state == STATE_PRESENT


def test_repair_dry_run_writes_nothing(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    provider = SessionPresenceProvider()
    instance = provider.expand(
        context_file_definition(), "claude", tmp_path
    )[0]
    status = provider.probe(instance)
    result = provider.repair(tmp_path, [status], dry_run=True)
    assert result.dry_run is True
    assert result.repaired
    assert not (tmp_path / ".claude" / "CLAUDE.md").exists()


def test_repair_no_actionable_skips_research_gap(tmp_path: Path) -> None:
    provider = SessionPresenceProvider()
    instance = provider.expand(
        context_file_definition(), "qwen", tmp_path
    )[0]
    status = provider.probe(instance)
    result = provider.repair(tmp_path, [status])
    assert result.repaired == ()
    assert status.findings[0].code == "research-gap-surface"
    assert result.skipped


def test_remove_research_gap_returns_false(tmp_path: Path) -> None:
    provider = SessionPresenceProvider()
    instance = provider.expand(
        context_file_definition(), "qwen", tmp_path
    )[0]
    assert provider.remove(instance) is False


def test_remove_context_file_deletes_section(tmp_path: Path) -> None:
    (tmp_path / ".cursor").mkdir()
    provider = SessionPresenceProvider()
    instance = provider.expand(rule_definition(), "cursor", tmp_path)[0]
    provider.repair(tmp_path, [provider.probe(instance)])
    assert provider.probe(instance).state == STATE_PRESENT
    assert provider.remove(instance) is True
    assert provider.probe(instance).state == STATE_MISSING

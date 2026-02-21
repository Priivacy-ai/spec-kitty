"""Tests for the telemetry emit template migration (m_2_0_1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_2_0_1_telemetry_emit_templates import (
    TelemetryEmitTemplatesMigration,
    TELEMETRY_MARKER,
    TEMPLATES_TO_UPDATE,
)


@pytest.fixture
def migration():
    return TelemetryEmitTemplatesMigration()


# Agent dirs to test (representative subset per CLAUDE.md)
AGENT_DIRS_TO_TEST = [
    (".claude", "commands"),
    (".codex", "prompts"),
    (".opencode", "command"),
]


def _create_agent_template(tmp_path: Path, agent_dir: str, subdir: str, template_name: str, content: str):
    """Helper to create a slash command template file."""
    agent_path = tmp_path / agent_dir / subdir
    agent_path.mkdir(parents=True, exist_ok=True)
    (agent_path / f"spec-kitty.{template_name}").write_text(content, encoding="utf-8")


def _create_config(tmp_path: Path, agents: list[str]):
    """Create a .kittify/config.yaml with specified agents."""
    config_dir = tmp_path / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    lines = ["agents:", "  available:"]
    for agent in agents:
        lines.append(f"    - {agent}")
    (config_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


OLD_TEMPLATE_CONTENT = """\
---
description: Test template
---

# Test Template

Some content here.
"""


@pytest.mark.parametrize("agent_dir,subdir", AGENT_DIRS_TO_TEST)
def test_detect_needed_when_missing_telemetry(tmp_path, migration, agent_dir, subdir):
    """Migration detects templates missing the telemetry section."""
    _create_agent_template(tmp_path, agent_dir, subdir, "specify.md", OLD_TEMPLATE_CONTENT)
    assert migration.detect(tmp_path) is True


@pytest.mark.parametrize("agent_dir,subdir", AGENT_DIRS_TO_TEST)
def test_detect_not_needed_when_telemetry_present(tmp_path, migration, agent_dir, subdir):
    """Migration not needed when telemetry marker already present."""
    content = OLD_TEMPLATE_CONTENT + f"\n{TELEMETRY_MARKER}\n"
    _create_agent_template(tmp_path, agent_dir, subdir, "specify.md", content)
    # Also need all other templates to have the marker
    for template in TEMPLATES_TO_UPDATE:
        _create_agent_template(tmp_path, agent_dir, subdir, template, content)
    assert migration.detect(tmp_path) is False


def test_detect_false_when_no_agent_dirs(tmp_path, migration):
    """Migration not needed when no agent directories exist."""
    assert migration.detect(tmp_path) is False


def test_can_apply_succeeds(tmp_path, migration):
    """can_apply returns True when source templates are accessible."""
    can, reason = migration.can_apply(tmp_path)
    assert can is True
    assert reason == ""


def test_apply_updates_templates(tmp_path, migration):
    """Migration copies canonical templates to agent directories."""
    agent_dir, subdir = ".claude", "commands"
    for template_name in TEMPLATES_TO_UPDATE:
        _create_agent_template(tmp_path, agent_dir, subdir, template_name, OLD_TEMPLATE_CONTENT)

    result = migration.apply(tmp_path)

    assert result.success is True
    assert len(result.errors) == 0

    # Verify all templates now contain the telemetry marker
    agent_path = tmp_path / agent_dir / subdir
    for template_name in TEMPLATES_TO_UPDATE:
        content = (agent_path / f"spec-kitty.{template_name}").read_text(encoding="utf-8")
        assert TELEMETRY_MARKER in content, f"Template {template_name} missing telemetry marker"


def test_apply_skips_missing_agent_dirs(tmp_path, migration):
    """Migration skips agent directories that don't exist (respects deletions)."""
    # Don't create any agent directories
    result = migration.apply(tmp_path)

    assert result.success is True
    assert len(result.errors) == 0


def test_apply_skips_already_updated(tmp_path, migration):
    """Migration is idempotent — skips templates that already have telemetry."""
    agent_dir, subdir = ".claude", "commands"
    content_with_telemetry = OLD_TEMPLATE_CONTENT + f"\n{TELEMETRY_MARKER}\n"
    for template_name in TEMPLATES_TO_UPDATE:
        _create_agent_template(tmp_path, agent_dir, subdir, template_name, content_with_telemetry)

    result = migration.apply(tmp_path)

    assert result.success is True
    # Should report no updates needed
    assert any("No agent templates needed" in c or "already have" in c for c in result.changes_made)


def test_apply_respects_agent_config(tmp_path, migration):
    """Migration only processes agents listed in config.yaml."""
    # Configure only opencode
    _create_config(tmp_path, ["opencode"])

    # Create both opencode and claude directories
    for template_name in TEMPLATES_TO_UPDATE:
        _create_agent_template(tmp_path, ".opencode", "command", template_name, OLD_TEMPLATE_CONTENT)
        _create_agent_template(tmp_path, ".claude", "commands", template_name, OLD_TEMPLATE_CONTENT)

    result = migration.apply(tmp_path)

    assert result.success is True

    # opencode should be updated
    for template_name in TEMPLATES_TO_UPDATE:
        content = (tmp_path / ".opencode" / "command" / f"spec-kitty.{template_name}").read_text(encoding="utf-8")
        assert TELEMETRY_MARKER in content

    # claude should NOT be updated (not in config)
    for template_name in TEMPLATES_TO_UPDATE:
        content = (tmp_path / ".claude" / "commands" / f"spec-kitty.{template_name}").read_text(encoding="utf-8")
        assert TELEMETRY_MARKER not in content


def test_apply_legacy_no_config_falls_back_to_all(tmp_path, migration):
    """Without config.yaml, migration processes all agent directories (legacy)."""
    # No config.yaml — should process all agents
    for template_name in TEMPLATES_TO_UPDATE:
        _create_agent_template(tmp_path, ".claude", "commands", template_name, OLD_TEMPLATE_CONTENT)
        _create_agent_template(tmp_path, ".codex", "prompts", template_name, OLD_TEMPLATE_CONTENT)

    result = migration.apply(tmp_path)

    assert result.success is True

    # Both should be updated
    for template_name in TEMPLATES_TO_UPDATE:
        assert TELEMETRY_MARKER in (tmp_path / ".claude" / "commands" / f"spec-kitty.{template_name}").read_text(
            encoding="utf-8"
        )
        assert TELEMETRY_MARKER in (tmp_path / ".codex" / "prompts" / f"spec-kitty.{template_name}").read_text(
            encoding="utf-8"
        )


def test_apply_dry_run_no_changes(tmp_path, migration):
    """Dry run reports what would change but doesn't modify files."""
    agent_dir, subdir = ".claude", "commands"
    for template_name in TEMPLATES_TO_UPDATE:
        _create_agent_template(tmp_path, agent_dir, subdir, template_name, OLD_TEMPLATE_CONTENT)

    result = migration.apply(tmp_path, dry_run=True)

    assert result.success is True
    assert any("Would update" in c for c in result.changes_made)

    # Files should NOT have been modified
    agent_path = tmp_path / agent_dir / subdir
    for template_name in TEMPLATES_TO_UPDATE:
        content = (agent_path / f"spec-kitty.{template_name}").read_text(encoding="utf-8")
        assert TELEMETRY_MARKER not in content


def test_apply_idempotent(tmp_path, migration):
    """Running migration twice produces same result."""
    agent_dir, subdir = ".claude", "commands"
    for template_name in TEMPLATES_TO_UPDATE:
        _create_agent_template(tmp_path, agent_dir, subdir, template_name, OLD_TEMPLATE_CONTENT)

    # First run
    result1 = migration.apply(tmp_path)
    assert result1.success is True

    # Capture content after first run
    agent_path = tmp_path / agent_dir / subdir
    contents_after_first = {}
    for template_name in TEMPLATES_TO_UPDATE:
        contents_after_first[template_name] = (agent_path / f"spec-kitty.{template_name}").read_text(encoding="utf-8")

    # Second run
    result2 = migration.apply(tmp_path)
    assert result2.success is True

    # Content should be identical
    for template_name in TEMPLATES_TO_UPDATE:
        content = (agent_path / f"spec-kitty.{template_name}").read_text(encoding="utf-8")
        assert content == contents_after_first[template_name]


@pytest.mark.parametrize(
    "template_name,expected_role",
    [
        ("specify.md", "specifier"),
        ("plan.md", "planner"),
        ("tasks.md", "planner"),
        ("review.md", "reviewer"),
        ("merge.md", "merger"),
    ],
)
def test_templates_contain_correct_role(tmp_path, migration, template_name, expected_role):
    """Each template instructs the agent to use the correct --role value."""
    _create_agent_template(tmp_path, ".claude", "commands", template_name, OLD_TEMPLATE_CONTENT)

    migration.apply(tmp_path)

    content = (tmp_path / ".claude" / "commands" / f"spec-kitty.{template_name}").read_text(encoding="utf-8")
    assert f"--role {expected_role}" in content

"""ATDD acceptance tests for the profile-context deployment migration (WP08).

US-4 scenarios:
- Migration deploys spec-kitty.profile-context.md to all configured agents
- Migration skips unconfigured agents
- Migration is idempotent (safe to run twice)
- Migration skips missing agent directory (respects user deletion)
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_config(project_path: Path, agents: list[str]) -> None:
    """Write .kittify/config.yaml with the given agent list."""
    kittify = project_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(
        f"agents:\n  available:\n"
        + "".join(f"    - {a}\n" for a in agents)
    )


def _make_agent_dir(project_path: Path, agent_root: str, subdir: str) -> Path:
    """Create an agent command directory and return its Path."""
    p = project_path / agent_root / subdir
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture()
def migration():
    from specify_cli.upgrade.migrations.m_2_2_0_profile_context_deployment import (
        ProfileContextDeploymentMigration,
    )

    return ProfileContextDeploymentMigration()


# ---------------------------------------------------------------------------
# T033 scenario 1 – deploys to all configured agents
# ---------------------------------------------------------------------------


def test_migration_deploys_to_configured_agents(tmp_path: Path, migration) -> None:
    """Migration creates spec-kitty.profile-context.md in each configured agent dir."""
    _write_config(tmp_path, ["claude", "opencode"])
    _make_agent_dir(tmp_path, ".claude", "commands")
    _make_agent_dir(tmp_path, ".opencode", "command")

    result = migration.apply(tmp_path)

    assert result.success
    assert (tmp_path / ".claude" / "commands" / "spec-kitty.profile-context.md").exists()
    assert (tmp_path / ".opencode" / "command" / "spec-kitty.profile-context.md").exists()


# ---------------------------------------------------------------------------
# T033 scenario 2 – skips unconfigured agents
# ---------------------------------------------------------------------------


def test_migration_skips_unconfigured_agents(tmp_path: Path, migration) -> None:
    """Migration does NOT write to agent dirs that are not in config.yaml."""
    _write_config(tmp_path, ["opencode"])
    _make_agent_dir(tmp_path, ".claude", "commands")   # exists but NOT configured
    _make_agent_dir(tmp_path, ".opencode", "command")  # configured

    result = migration.apply(tmp_path)

    assert result.success
    assert not (tmp_path / ".claude" / "commands" / "spec-kitty.profile-context.md").exists()
    assert (tmp_path / ".opencode" / "command" / "spec-kitty.profile-context.md").exists()


# ---------------------------------------------------------------------------
# T033 scenario 3 – idempotent
# ---------------------------------------------------------------------------


def test_migration_idempotent(tmp_path: Path, migration) -> None:
    """Running the migration twice produces no errors and no duplicate files."""
    _write_config(tmp_path, ["claude"])
    _make_agent_dir(tmp_path, ".claude", "commands")

    result1 = migration.apply(tmp_path)
    result2 = migration.apply(tmp_path)

    assert result1.success
    assert result2.success

    dest = tmp_path / ".claude" / "commands" / "spec-kitty.profile-context.md"
    assert dest.exists()
    # No duplicate — only one file
    siblings = list(dest.parent.glob("spec-kitty.profile-context*"))
    assert len(siblings) == 1


# ---------------------------------------------------------------------------
# T033 scenario 4 – skips missing directory
# ---------------------------------------------------------------------------


def test_migration_skips_missing_directory(tmp_path: Path, migration) -> None:
    """Migration silently skips an agent that is configured but whose dir was deleted."""
    _write_config(tmp_path, ["claude"])
    # Do NOT create .claude/commands/ — simulate manual deletion

    result = migration.apply(tmp_path)

    assert result.success
    assert not (tmp_path / ".claude" / "commands" / "spec-kitty.profile-context.md").exists()

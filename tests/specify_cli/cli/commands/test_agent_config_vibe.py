"""Integration tests for agent config add/remove vibe (T027).

Tests:
- agent config add vibe: config updated, skill-only registration.
- agent config remove vibe (vibe-only): manifest empty, files gone.
- agent config remove vibe (codex+vibe): manifest has codex-only entries.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.config import app
from specify_cli.core.agent_config import save_agent_config, load_agent_config, AgentConfig
from specify_cli.skills import command_installer, manifest_store

pytestmark = pytest.mark.integration

runner = CliRunner()

# ---------------------------------------------------------------------------
# Root of the real spec-kitty repo (used to resolve command templates).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent


def _write_config(tmp_path: Path, agents: list[str]) -> None:
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    config = AgentConfig(available=agents)
    save_agent_config(tmp_path, config)


def _missions_available() -> bool:
    """Return True when the real command templates exist (local dev environment)."""
    return (_REPO_ROOT / "src" / "specify_cli" / "missions").is_dir()


def _setup_missions_symlink(tmp_path: Path) -> None:
    """Symlink src/specify_cli/missions into tmp_path so templates resolve."""
    missions_src = _REPO_ROOT / "src" / "specify_cli" / "missions"
    missions_dst = tmp_path / "src" / "specify_cli"
    missions_dst.mkdir(parents=True, exist_ok=True)
    missions_link = missions_dst / "missions"
    if not missions_link.exists():
        missions_link.symlink_to(missions_src)


# ---------------------------------------------------------------------------
# T027-A: agent config add vibe
# ---------------------------------------------------------------------------


def test_add_vibe_updates_config(tmp_path: Path) -> None:
    """agent config add vibe must add vibe to agents.available in config.yaml."""
    _write_config(tmp_path, [])

    with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=tmp_path):
        result = runner.invoke(app, ["add", "vibe"])

    assert result.exit_code == 0, result.output

    config = load_agent_config(tmp_path)
    assert "vibe" in config.available


def test_add_vibe_prints_registered(tmp_path: Path) -> None:
    """agent config add vibe must print a registration confirmation."""
    _write_config(tmp_path, [])

    with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=tmp_path):
        result = runner.invoke(app, ["add", "vibe"])

    assert result.exit_code == 0
    output = result.output
    # Should mention vibe registered or added
    assert "vibe" in output.lower() or "Registered" in output


def test_add_vibe_idempotent(tmp_path: Path) -> None:
    """Adding vibe twice must leave config with exactly one vibe entry."""
    _write_config(tmp_path, [])

    with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=tmp_path):
        runner.invoke(app, ["add", "vibe"])
        result2 = runner.invoke(app, ["add", "vibe"])

    assert result2.exit_code == 0
    config = load_agent_config(tmp_path)
    assert config.available.count("vibe") == 1


# ---------------------------------------------------------------------------
# T027-B: agent config remove vibe (vibe-only)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _missions_available(), reason="command templates not available")
def test_remove_vibe_only(tmp_path: Path) -> None:
    """remove vibe from vibe-only project: manifest empty, skill dirs gone."""
    _write_config(tmp_path, ["vibe"])
    _setup_missions_symlink(tmp_path)

    # Install vibe skills
    report = command_installer.install(tmp_path, "vibe")
    assert len(report.added) == 11

    # Verify files exist before removal
    manifest = manifest_store.load(tmp_path)
    assert len(manifest.entries) == 11
    for entry in manifest.entries:
        assert (tmp_path / entry.path).exists()

    with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=tmp_path):
        result = runner.invoke(app, ["remove", "vibe"])

    assert result.exit_code == 0, result.output

    # Manifest must be empty
    manifest_after = manifest_store.load(tmp_path)
    assert len(manifest_after.entries) == 0, (
        f"Expected empty manifest after remove vibe; got {len(manifest_after.entries)} entries"
    )

    # Skill dirs must be gone
    skills_root = tmp_path / ".agents" / "skills"
    if skills_root.exists():
        remaining = list(skills_root.glob("spec-kitty.*/SKILL.md"))
        assert len(remaining) == 0, f"Unexpected SKILL.md files remain: {remaining}"

    # Config must not contain vibe
    config = load_agent_config(tmp_path)
    assert "vibe" not in config.available


# ---------------------------------------------------------------------------
# T027-C: agent config remove vibe with codex also configured
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _missions_available(), reason="command templates not available")
def test_remove_vibe_leaves_codex_entries(tmp_path: Path) -> None:
    """remove vibe when codex+vibe configured: codex manifest entries remain."""
    _write_config(tmp_path, ["codex", "vibe"])
    _setup_missions_symlink(tmp_path)

    # Install codex first, then vibe (shared root — same files, two agents)
    command_installer.install(tmp_path, "codex")
    command_installer.install(tmp_path, "vibe")

    # After both installs, all entries should have agents == ("codex", "vibe")
    manifest_before = manifest_store.load(tmp_path)
    assert len(manifest_before.entries) == 11
    for entry in manifest_before.entries:
        assert "codex" in entry.agents
        assert "vibe" in entry.agents

    # Snapshot bytes before remove
    snapshots: dict[str, bytes] = {}
    for entry in manifest_before.entries:
        abs_path = tmp_path / entry.path
        snapshots[entry.path] = abs_path.read_bytes()

    with patch("specify_cli.cli.commands.agent.config.find_repo_root", return_value=tmp_path):
        result = runner.invoke(app, ["remove", "vibe"])

    assert result.exit_code == 0, result.output

    # Manifest must still have 11 entries — codex still owns them
    manifest_after = manifest_store.load(tmp_path)
    assert len(manifest_after.entries) == 11, (
        f"Expected 11 entries (codex still present); got {len(manifest_after.entries)}"
    )

    # All entries must be codex-only now
    for entry in manifest_after.entries:
        assert entry.agents == ("codex",), (
            f"Entry {entry.path} has agents={entry.agents}, expected ('codex',)"
        )

    # Files must be byte-identical (no rewrite)
    for entry in manifest_after.entries:
        abs_path = tmp_path / entry.path
        assert abs_path.exists(), f"File missing: {entry.path}"
        assert abs_path.read_bytes() == snapshots[entry.path], (
            f"File content changed after removing vibe: {entry.path}"
        )

    # Config must not contain vibe but must still contain codex
    config = load_agent_config(tmp_path)
    assert "vibe" not in config.available
    assert "codex" in config.available

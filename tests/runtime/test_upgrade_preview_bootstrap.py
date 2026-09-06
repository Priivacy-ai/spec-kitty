"""Global owner regressions; public startup wiring is separately owned by WP10."""

from pathlib import Path

import pytest

from specify_cli.runtime import agent_commands, agent_skills, bootstrap
from specify_cli.skills.registry import SkillRegistry
from tests.upgrade.preview_support.snapshot import assert_unchanged, snapshot

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@pytest.fixture
def owner_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".kittify"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(home / ".config/opencode"))
    return home


@pytest.fixture
def skill_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source = tmp_path / "skills"
    skill = source / "spec-kitty"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: spec-kitty\ndescription: Govern work\n---\n# Work\n")
    monkeypatch.setattr(agent_skills, "_discover_registry", lambda: SkillRegistry(source))
    return source


def test_existing_runtime_repairs_current_marker_missing_content(
    owner_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "package/missions"
    (source / "software-dev").mkdir(parents=True)
    (source / "software-dev/mission.yaml").write_text("mission: software-dev\n")
    monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(source))
    cache = owner_home / ".kittify/cache"
    cache.mkdir(parents=True)
    (cache / "version.lock").write_text(bootstrap._get_cli_version())
    bootstrap.ensure_runtime()
    assert (owner_home / ".kittify/missions/software-dev/mission.yaml").is_file()


def test_existing_skills_repair_current_marker_missing_content(
    owner_home: Path, skill_source: Path,
) -> None:
    agent_skills.ensure_global_agent_skills()
    missing = owner_home / ".agents/skills/spec-kitty/SKILL.md"
    missing.unlink()
    agent_skills.ensure_global_agent_skills()
    assert missing.is_file(), "Current stamp must not conceal missing required content"


def test_existing_commands_preserve_unknown_prefixed_link(owner_home: Path) -> None:
    output = agent_commands.get_global_command_dir("claude")
    output.mkdir(parents=True)
    target = owner_home / "custom.md"
    target.write_text("custom command\n")
    target.chmod(0o444)
    link = output / "spec-kitty.custom.md"
    link.symlink_to(target)
    before = snapshot({"target": target, "link": link})
    agent_commands.ensure_global_agent_commands(agent_keys=["claude"])
    assert_unchanged(before, snapshot({"target": target, "link": link}))


def test_existing_skills_preserve_unknown_prefixed_tree(
    owner_home: Path, skill_source: Path,
) -> None:
    custom = owner_home / ".agents/skills/spec-kitty-custom"
    custom.mkdir(parents=True)
    (custom / "SKILL.md").write_text("# User skill\n")
    (custom / ".ignored").write_bytes(b"sentinel")
    before = snapshot({"custom": custom})
    agent_skills.ensure_global_agent_skills()
    assert_unchanged(before, snapshot({"custom": custom}))


def test_existing_scoped_command_repair_has_no_churn(owner_home: Path) -> None:
    agent_commands.ensure_global_agent_commands(agent_keys=["claude"])
    before = snapshot({"home": owner_home})
    agent_commands.ensure_global_agent_commands(agent_keys=["claude"])
    assert_unchanged(before, snapshot({"home": owner_home}))

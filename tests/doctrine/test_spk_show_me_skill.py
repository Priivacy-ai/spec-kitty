"""Contract pins for the compact visual-communication skill."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.skills.installer import install_skills_for_agent
from specify_cli.skills.registry import SkillRegistry
from specify_cli.status.models import Lane


pytestmark = [pytest.mark.doctrine, pytest.mark.fast]
REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPO_ROOT / "src" / "doctrine" / "skills"
SKILL = SKILLS_ROOT / "spk-doctrine-show-me" / "SKILL.md"


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_skill_attributes_humanlayer_source_and_carries_mit_notice(
    skill_text: str,
) -> None:
    notice = SKILL.parent / "references" / "humanlayer-origin-and-license.md"

    assert "Dexter Horthy" in skill_text
    assert "HumanLayer" in skill_text
    assert "https://github.com/humanlayer/skills" in skill_text
    assert notice.is_file()
    notice_text = notice.read_text(encoding="utf-8")
    assert "MIT License" in notice_text
    assert "Copyright (c) 2026 HumanLayer" in notice_text
    assert "The above copyright notice and this permission notice" in notice_text


def test_skill_builds_on_canonical_diagram_doctrine(skill_text: str) -> None:
    sources = (SKILL.parent / "references" / "spec-kitty-diagram-sources.md").read_text(
        encoding="utf-8"
    )
    assert "spec-kitty charter" in skill_text
    assert "context --include" in skill_text
    assert "toolguide:mermaid-diagramming" in sources
    assert "toolguide:plantuml-diagramming" in sources
    assert "directive:USE_C4_MODEL_TECHNIQUES" in sources
    assert "tactic:architecture-diagram-review-checklist" in sources
    assert "--action <action> --mission-type <type> --json" in sources
    assert "inclusion alone does not" in sources
    assert "packs/built-in/toolguides/MERMAID_DIAGRAMMING.md" in sources
    assert "packs/built-in/toolguides/PLANTUML_DIAGRAMMING.md" in sources


def test_skill_pins_status_tui_rendering_contract(skill_text: str) -> None:
    lifecycle = " → ".join(
        lane.value
        for lane in (
            Lane.PLANNED,
            Lane.CLAIMED,
            Lane.IN_PROGRESS,
            Lane.FOR_REVIEW,
            Lane.IN_REVIEW,
            Lane.APPROVED,
            Lane.DONE,
        )
    )
    renderer = (
        REPO_ROOT / "src/specify_cli/cli/commands/agent/tasks_status_cmd.py"
    ).read_text(encoding="utf-8")

    assert "spec-kitty agent tasks status --json" in skill_text
    assert lifecycle in skill_text
    for heading in (
        "📋 Planned",
        "🔄 Doing",
        "👀 For Review",
        "👍 Approved",
        "✅ Done",
    ):
        assert f'table.add_column("{heading}"' in renderer
        assert heading.split(maxsplit=1)[1] in skill_text
    assert "Lane.CLAIMED" in renderer and "Lane.IN_REVIEW" in renderer
    assert "work_packages[].lane" in skill_text
    assert "JSON has no `next_action`" in skill_text
    assert "Done progress" in skill_text
    assert "Weighted readiness" in skill_text


def test_installed_skill_carries_portable_sources_and_themes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    project = tmp_path / "project"
    project.mkdir()
    skill = SkillRegistry.from_local_repo(REPO_ROOT).get_skill("spk-doctrine-show-me")
    assert skill is not None

    install_skills_for_agent(project, "codex", [skill])

    installed = project / ".agents" / "skills" / "spk-doctrine-show-me"
    assert (installed / "references" / "spec-kitty-diagram-sources.md").is_file()
    assert (installed / "assets" / "MERMAID_DIAGRAMMING.md").is_file()
    assert (installed / "assets" / "PLANTUML_DIAGRAMMING.md").is_file()
    assert (installed / "assets" / "mermaid-theme-common-template.md").is_file()
    assert (
        installed / "assets" / "mermaid-theme-bluegray-conversation-template.md"
    ).is_file()


@pytest.mark.parametrize(
    "filename",
    [
        "mermaid-theme-common-template.md",
        "mermaid-theme-bluegray-conversation-template.md",
    ],
)
def test_bundled_theme_matches_canonical_template(filename: str) -> None:
    bundled = SKILL.parent / "assets" / filename
    canonical = REPO_ROOT / "src" / "doctrine" / "templates" / "diagrams" / "themes" / filename
    assert bundled.read_bytes() == canonical.read_bytes()


@pytest.mark.parametrize(
    "filename",
    ["MERMAID_DIAGRAMMING.md", "PLANTUML_DIAGRAMMING.md"],
)
def test_bundled_guide_matches_canonical_toolguide(filename: str) -> None:
    bundled = SKILL.parent / "assets" / filename
    canonical = REPO_ROOT / "packs" / "built-in" / "toolguides" / filename
    assert bundled.read_bytes() == canonical.read_bytes()


@pytest.mark.parametrize(
    "relative_path",
    [
        "src/doctrine/skills/spec-kitty/SKILL.md",
        "src/doctrine/skills/spk-mission-specify/SKILL.md",
        "src/doctrine/skills/spk-mission-plan/SKILL.md",
        "src/doctrine/skills/spk-admin-dashboard/SKILL.md",
        "packs/built-in/missions/mission-steps/software-dev/specify/prompt.md",
        "packs/built-in/missions/mission-steps/software-dev/plan/prompt.md",
        "packs/built-in/missions/mission-steps/plan/specify/prompt.md",
        "packs/built-in/missions/mission-steps/plan/plan/prompt.md",
    ],
)
def test_primary_surfaces_recommend_the_skill(relative_path: str) -> None:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    assert "spk-doctrine-show-me" in text


@pytest.mark.parametrize(
    "relative_path",
    [
        "tests/specify_cli/regression/_twelve_agent_baseline/claude/specify.md",
        "tests/specify_cli/regression/_twelve_agent_baseline/gemini/specify.toml",
    ],
)
def test_rendered_specify_command_preserves_exact_skill_name(relative_path: str) -> None:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    assert "`spk-doctrine-show-me`" in text

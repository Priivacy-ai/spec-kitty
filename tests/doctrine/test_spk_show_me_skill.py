"""Contract pins for the compact visual-communication skill."""

from __future__ import annotations

from pathlib import Path

import pytest


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
    assert "MIT License" in notice.read_text(encoding="utf-8")


def test_skill_builds_on_canonical_diagram_doctrine(skill_text: str) -> None:
    assert "MERMAID_DIAGRAMMING.md" in skill_text
    assert "PLANTUML_DIAGRAMMING.md" in skill_text
    assert "USE_C4_MODEL_TECHNIQUES" in skill_text
    assert "architecture-diagram-review-checklist" in skill_text
    assert "src/doctrine/templates/diagrams/" in skill_text


def test_skill_pins_status_tui_rendering_contract(skill_text: str) -> None:
    assert "spec-kitty agent tasks status --json" in skill_text
    assert "Planned → Doing → For Review → Approved → Done" in skill_text
    assert "Done progress" in skill_text
    assert "Weighted readiness" in skill_text
    assert "in_review" in skill_text


@pytest.mark.parametrize(
    "relative_path",
    [
        "src/doctrine/skills/spec-kitty/SKILL.md",
        "src/doctrine/skills/spk-mission-specify/SKILL.md",
        "src/doctrine/skills/spk-mission-plan/SKILL.md",
        "packs/built-in/missions/mission-steps/software-dev/specify/prompt.md",
        "packs/built-in/missions/mission-steps/software-dev/plan/prompt.md",
    ],
)
def test_primary_surfaces_recommend_the_skill(relative_path: str) -> None:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    assert "spk-doctrine-show-me" in text

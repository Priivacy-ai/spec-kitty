from __future__ import annotations

import re
from pathlib import Path

import pytest


pytestmark = [pytest.mark.doctrine, pytest.mark.fast]
REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPO_ROOT / "src" / "doctrine" / "skills"
SPK_SKILLS = {
    "spk-admin-agent-config",
    "spk-admin-dashboard",
    "spk-admin-git-workflow",
    "spk-admin-setup-doctor",
    "spk-admin-upgrade",
    "spk-doctrine-bulk-edit",
    "spk-doctrine-charter",
    "spk-doctrine-glossary",
    "spk-doctrine-profile-load",
    "spk-doctrine-semantic-compression",
    "spk-doctrine-spdd-reasons",
    "spk-gate-accept",
    "spk-gate-merge",
    "spk-gate-mission-review",
    "spk-gate-retrospective",
    "spk-integrate-orchestrator-api",
    "spk-meta-skill-authoring",
    "spk-meta-skill-map",
    "spk-mission-documentation",
    "spk-mission-plan",
    "spk-mission-research",
    "spk-mission-specify",
    "spk-mission-tasks",
    "spk-mission-types",
    "spk-run-blocked-recovery",
    "spk-run-implement-review",
    "spk-run-next",
    "spk-run-program-orchestrate",
    "spk-run-review-wp",
    "spk-start-agent-surface",
    "spk-start-command-map",
    "spk-start-first-feature",
    "spk-start-here",
    "spk-team-auth",
    "spk-team-connectors",
    "spk-team-sync",
    "spk-team-tracker",
}
LEGACY_ALIAS_SKILLS = {
    "ad-hoc-profile-load",
    "spec-kitty-bulk-edit-classification",
    "spec-kitty-charter-doctrine",
    "spec-kitty-git-workflow",
    "spec-kitty-glossary-context",
    "spec-kitty-implement-review",
    "spec-kitty-mission-review",
    "spec-kitty-mission-system",
    "spec-kitty-orchestrator-api-operator",
    "spec-kitty-program-orchestrate",
    "spec-kitty-runtime-next",
    "spec-kitty-runtime-review",
    "spec-kitty-setup-doctor",
    "spec-kitty-spdd-reasons",
}


def _frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(?P<body>.*?)\n---\n", text, re.DOTALL)
    assert match, "SKILL.md must start with a YAML frontmatter block"
    fields: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def test_320_spk_skill_pack_is_complete() -> None:
    actual = {
        path.name
        for path in SKILLS_ROOT.iterdir()
        if path.is_dir() and path.name.startswith("spk-")
    }

    assert actual == SPK_SKILLS


def test_spk_skill_frontmatter_matches_directory_name() -> None:
    for skill_name in sorted(SPK_SKILLS):
        skill_md = SKILLS_ROOT / skill_name / "SKILL.md"
        assert skill_md.is_file(), f"missing {skill_name}/SKILL.md"

        fields = _frontmatter(skill_md.read_text(encoding="utf-8"))

        assert fields.get("name") == skill_name
        assert fields.get("description"), f"{skill_name} needs a description"
        assert len(fields["description"]) <= 200


def test_spk_skill_bodies_stay_concise() -> None:
    for skill_name in sorted(SPK_SKILLS):
        skill_md = SKILLS_ROOT / skill_name / "SKILL.md"
        body = skill_md.read_text(encoding="utf-8").split("---\n", 2)[2]

        assert len(body.splitlines()) <= 80, f"{skill_name} body is too long"


def test_spk_skill_map_mentions_every_public_skill() -> None:
    skill_map = (
        SKILLS_ROOT
        / "spk-meta-skill-map"
        / "references"
        / "spk-skill-map.md"
    ).read_text(encoding="utf-8")

    for skill_name in sorted(SPK_SKILLS):
        assert f"`{skill_name}`" in skill_map


def test_legacy_alias_skills_remain_installed() -> None:
    actual = {
        path.name
        for path in SKILLS_ROOT.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }

    assert actual >= LEGACY_ALIAS_SKILLS

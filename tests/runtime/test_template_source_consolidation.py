"""Regression tests for #1731 template source consolidation."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.runtime.resolver import ResolutionTier, resolve_command, resolve_template

pytestmark = [pytest.mark.fast]

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_TEMPLATE_NAMES = {
    "plan-template.md",
    "spec-template.md",
    "tasks-template.md",
    "task-prompt-template.md",
}


def test_software_dev_runtime_template_tree_removed() -> None:
    duplicate_tree = REPO_ROOT / "src" / "specify_cli" / "missions" / "software-dev" / "templates"

    assert not duplicate_tree.exists()


def test_generic_content_template_copies_removed() -> None:
    stale_roots = [
        REPO_ROOT / "src" / "specify_cli" / "templates",
        REPO_ROOT / "src" / "doctrine" / "templates",
    ]

    stale_copies = [
        root / name
        for root in stale_roots
        for name in CONTENT_TEMPLATE_NAMES
        if (root / name).exists()
    ]

    assert stale_copies == []


@pytest.mark.parametrize("name", sorted(CONTENT_TEMPLATE_NAMES))
def test_content_template_source_is_doctrine_mission_tree(name: str) -> None:
    canonical = REPO_ROOT / "src" / "doctrine" / "missions" / "software-dev" / "templates" / name

    assert canonical.is_file()


def test_runtime_package_default_resolves_doctrine_template(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "empty-global-home"))

    project = tmp_path / "project"
    (project / ".kittify").mkdir(parents=True)

    result = resolve_template("plan-template.md", project, mission="software-dev")

    assert result.tier == ResolutionTier.PACKAGE_DEFAULT
    assert result.path == (
        REPO_ROOT
        / "src"
        / "doctrine"
        / "missions"
        / "software-dev"
        / "templates"
        / "plan-template.md"
    )


def test_stale_specify_cli_missions_env_root_resolves_doctrine_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A deleted legacy template tree must not mask doctrine package defaults."""
    monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(REPO_ROOT / "src" / "specify_cli" / "missions"))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "empty-global-home"))

    project = tmp_path / "project"
    (project / ".kittify").mkdir(parents=True)

    content = resolve_template("plan-template.md", project, mission="software-dev")
    command = resolve_command("implement.md", project, mission="software-dev")

    assert content.tier == ResolutionTier.PACKAGE_DEFAULT
    assert content.path == (
        REPO_ROOT
        / "src"
        / "doctrine"
        / "missions"
        / "software-dev"
        / "templates"
        / "plan-template.md"
    )
    assert command.tier == ResolutionTier.PACKAGE_DEFAULT
    assert command.path == (
        REPO_ROOT
        / "src"
        / "doctrine"
        / "missions"
        / "mission-steps"
        / "software-dev"
        / "implement"
        / "prompt.md"
    )

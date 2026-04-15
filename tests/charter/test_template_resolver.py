"""Tests for charter-level template resolution."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import charter.template_resolver as template_resolver_module
from charter.template_resolver import CharterTemplateResolver
from doctrine.missions.repository import TemplateResult
from doctrine.resolver import ResolutionResult, ResolutionTier

pytestmark = pytest.mark.fast


def test_resolve_command_template_with_project_context_uses_runtime_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "plan.md"
    path.write_text("override command", encoding="utf-8")
    monkeypatch.setattr(
        template_resolver_module,
        "resolve_command",
        lambda *args, **kwargs: ResolutionResult(path=path, tier=ResolutionTier.OVERRIDE, mission="software-dev"),
    )

    resolver = CharterTemplateResolver(repo=SimpleNamespace())
    result = resolver.resolve_command_template("software-dev", "plan", project_dir=tmp_path)

    assert result.content == "override command"
    assert result.origin == "override/software-dev/command-templates/plan.md"
    assert result.tier.name == ResolutionTier.OVERRIDE.name


def test_resolve_content_template_with_project_context_uses_runtime_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "spec-template.md"
    path.write_text("legacy content", encoding="utf-8")
    monkeypatch.setattr(
        template_resolver_module,
        "resolve_template",
        lambda *args, **kwargs: ResolutionResult(path=path, tier=ResolutionTier.LEGACY, mission="software-dev"),
    )

    resolver = CharterTemplateResolver(repo=SimpleNamespace())
    result = resolver.resolve_content_template("software-dev", "spec-template.md", project_dir=tmp_path)

    assert result.content == "legacy content"
    assert result.origin == "legacy/software-dev/templates/spec-template.md"
    assert result.tier.name == ResolutionTier.LEGACY.name


def test_resolve_templates_without_project_context_use_doctrine_repo() -> None:
    repo = SimpleNamespace(
        get_command_template=lambda mission, name: TemplateResult("command body", "doctrine/software-dev/command-templates/plan.md"),
        get_content_template=lambda mission, name: TemplateResult("template body", "doctrine/software-dev/templates/spec-template.md"),
    )

    resolver = CharterTemplateResolver(repo=repo)

    command = resolver.resolve_command_template("software-dev", "plan")
    content = resolver.resolve_content_template("software-dev", "spec-template.md")

    assert command.content == "command body"
    assert command.origin == "doctrine/software-dev/command-templates/plan.md"
    assert command.tier.name == ResolutionTier.PACKAGE_DEFAULT.name
    assert content.content == "template body"
    assert content.origin == "doctrine/software-dev/templates/spec-template.md"
    assert content.tier.name == ResolutionTier.PACKAGE_DEFAULT.name


def test_resolve_templates_raise_when_doctrine_repo_has_no_match() -> None:
    repo = SimpleNamespace(
        get_command_template=lambda mission, name: None,
        get_content_template=lambda mission, name: None,
    )
    resolver = CharterTemplateResolver(repo=repo)

    with pytest.raises(FileNotFoundError):
        resolver.resolve_command_template("software-dev", "plan")

    with pytest.raises(FileNotFoundError):
        resolver.resolve_content_template("software-dev", "spec-template.md")


def test_tier_to_origin_falls_back_to_unknown_prefix() -> None:
    origin = CharterTemplateResolver._tier_to_origin(object(), "software-dev", "templates", "spec-template.md")
    assert origin == "unknown/software-dev/templates/spec-template.md"

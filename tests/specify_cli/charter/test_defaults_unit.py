"""Unit tests for specify_cli charter defaults and markdown fallbacks."""

from __future__ import annotations

import importlib
import warnings
from types import SimpleNamespace

import pytest

from specify_cli.charter.compiler import CharterReference, _render_charter_markdown
from specify_cli.charter.interview import (
    CharterInterview,
    _load_packaged_defaults,
    default_interview,
)
from specify_cli.charter.resolver import DEFAULT_TOOL_REGISTRY

pytestmark = pytest.mark.fast


def _import_legacy_interview_module():
    """Import the legacy interview module after any test-driven module resets."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return importlib.import_module("specify_cli.charter.interview")


class _StubResource:
    def __init__(self, content: str) -> None:
        self._content = content

    def joinpath(self, name: str) -> "_StubResource":
        assert name == "defaults.yaml"
        return self

    def read_text(self, encoding: str = "utf-8") -> str:
        assert encoding == "utf-8"
        return self._content


def test_load_packaged_defaults_returns_empty_when_resource_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "specify_cli.charter.interview.importlib.resources.files",
        lambda package: (_ for _ in ()).throw(FileNotFoundError("missing defaults")),
    )

    defaults = _load_packaged_defaults()

    assert defaults == {
        "answers": {},
        "selected_paradigms": [],
        "selected_directives": [],
        "available_tools": [],
    }


def test_load_packaged_defaults_returns_empty_on_invalid_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "specify_cli.charter.interview.importlib.resources.files",
        lambda package: _StubResource("answers: ["),
    )

    defaults = _load_packaged_defaults()

    assert defaults["answers"] == {}
    assert defaults["available_tools"] == []


def test_load_packaged_defaults_returns_empty_when_yaml_is_not_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "specify_cli.charter.interview.importlib.resources.files",
        lambda package: _StubResource("- not-a-mapping\n"),
    )

    defaults = _load_packaged_defaults()

    assert defaults["answers"] == {}
    assert defaults["selected_paradigms"] == []
    assert defaults["selected_directives"] == []


def test_default_interview_loads_packaged_defaults_and_falls_back_to_tool_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    interview_mod = _import_legacy_interview_module()
    monkeypatch.setattr(
        "specify_cli.charter.interview.load_doctrine_catalog",
        lambda: SimpleNamespace(paradigms=frozenset(), directives=frozenset()),
    )
    monkeypatch.setattr(
        "specify_cli.charter.interview._load_packaged_defaults",
        lambda: {
            "answers": {
                "project_intent": "Keep upgrades deterministic.",
                "languages_frameworks": "Python and pytest.",
                "testing_requirements": "Run focused tests.",
                "quality_gates": "CI green.",
                "review_policy": "One reviewer.",
                "performance_targets": "N/A",
                "deployment_constraints": "Local only",
            },
            "selected_paradigms": [],
            "selected_directives": [],
        },
    )

    interview = interview_mod.default_interview(mission="software-dev", profile="minimal")

    assert interview.answers["project_intent"] == "Keep upgrades deterministic."
    assert interview.selected_paradigms == []
    assert interview.selected_directives == []
    assert interview.available_tools == sorted(DEFAULT_TOOL_REGISTRY)


def test_render_charter_markdown_uses_testing_fallback_when_missing() -> None:
    markdown = _render_charter_markdown(
        mission="software-dev",
        template_set="software-dev-default",
        interview=CharterInterview(
            mission="software-dev",
            profile="minimal",
            answers={
                "project_intent": "Make the CLI reliable.",
                "languages_frameworks": "Python",
                "quality_gates": "CI green.",
                "review_policy": "One reviewer.",
                "performance_targets": "N/A",
                "deployment_constraints": "None.",
            },
            selected_paradigms=[],
            selected_directives=[],
            available_tools=["git"],
        ),
        selected_paradigms=[],
        selected_directives=[],
        available_tools=["git"],
        references=[
            CharterReference(
                id="USER:PROJECT_PROFILE",
                kind="user_profile",
                title="User Project Profile",
                summary="Captured answers.",
                source_path=".kittify/charter/interview/answers.yaml",
                local_path="library/user-project-profile.md",
                content="profile",
            )
        ],
    )

    assert "Use the project's declared testing approach" in markdown

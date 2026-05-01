"""Validation checks for enriched directive content."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
import pytest

from tests.doctrine.conftest import DOCTRINE_SOURCE_ROOT

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

_DOCTRINE_ROOT = DOCTRINE_SOURCE_ROOT
_DIRECTIVES_DIRS = [_DOCTRINE_ROOT / "directives" / d for d in ("shipped", "_proposed")]


def _multi_glob(dirs: list[Path], pattern: str) -> list[Path]:
    results: list[Path] = []
    for d in dirs:
        if d.exists():
            results.extend(d.glob(pattern))
    return sorted(set(results))


def _load_yaml(path: Path) -> dict[str, Any]:
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.load(fh) or {}


def _looks_like_placeholder_intent(intent: str, title: str) -> bool:
    normalized_intent = " ".join(intent.split()).strip().lower()
    normalized_title = " ".join(title.split()).strip().lower()
    return normalized_intent == f"ensure compliance with {normalized_title}."


def test_shipped_directives_have_non_placeholder_intent_and_scope() -> None:
    directive_files = _multi_glob(_DIRECTIVES_DIRS, "*.directive.yaml")
    assert directive_files, "No directive files found"

    missing_scope: list[str] = []
    placeholder_intent: list[str] = []

    for path in directive_files:
        data = _load_yaml(path)
        title = str(data.get("title", "")).strip()
        intent = str(data.get("intent", "")).strip()
        scope = str(data.get("scope", "")).strip()

        if not scope:
            missing_scope.append(path.name)

        if _looks_like_placeholder_intent(intent, title):
            placeholder_intent.append(path.name)

    assert not missing_scope, "Directives missing scope:\n" + "\n".join(missing_scope)
    assert not placeholder_intent, "Directives with placeholder one-sentence intent:\n" + "\n".join(placeholder_intent)

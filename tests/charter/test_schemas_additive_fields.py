"""Tests for additive schema fields (WP01 of mission wp-prompt-governance-payload-01KRR8HS).

Verifies that:
1. ``Directive.references`` is an additive ``list[str]`` defaulting to ``[]``.
2. ``DoctrineSelectionConfig.authority_paths`` is an additive ``list[str]``
   defaulting to ``[]``.
3. YAML round-trips without the new fields parse cleanly (NFR-005 backward
   compatibility).
4. YAML round-trips with the new fields preserve the list contents.
5. Existing on-disk directives fixtures still load without ``ValidationError``.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, cast

import pytest
from ruamel.yaml import YAML

from charter.schemas import (
    Directive,
    DirectivesConfig,
    DoctrineSelectionConfig,
)

pytestmark = pytest.mark.fast


def _load_yaml_str(text: str) -> dict[str, Any]:
    """Parse a YAML string into a plain dict."""
    yaml = YAML(typ="safe")
    return cast(dict[str, Any], yaml.load(io.StringIO(text)))


# ---------------------------------------------------------------------------
# Directive.references
# ---------------------------------------------------------------------------


class TestDirectiveReferencesField:
    def test_default_is_empty_list(self) -> None:
        """A Directive constructed without ``references`` defaults to ``[]``."""
        directive = Directive(id="DIR-001", title="t", description="d")
        assert directive.references == []

    def test_default_is_not_shared_between_instances(self) -> None:
        """Two Directives must not share the same list object (Pydantic uses
        ``default_factory``)."""
        a = Directive(id="DIR-001", title="t", description="d")
        b = Directive(id="DIR-002", title="t", description="d")
        a.references.append("DIRECTIVE_999")
        assert b.references == []

    def test_round_trip_without_references(self) -> None:
        """Existing YAML lacking ``references:`` deserializes with ``[]`` and
        re-serializes (with ``exclude_defaults=True``) without emitting the
        new key — i.e. bytes-on-disk shape is preserved for missions that
        never touched the new field (NFR-005)."""
        yaml_text = (
            "id: DIR-001\n"
            "title: Example\n"
            "description: A directive\n"
            "severity: warn\n"
        )
        data = _load_yaml_str(yaml_text)
        directive = Directive(**data)

        assert directive.references == []

        dumped = directive.model_dump(exclude_defaults=True)
        assert "references" not in dumped

    def test_round_trip_with_references(self) -> None:
        """YAML carrying ``references: [DIRECTIVE_032]`` loads with the list
        intact."""
        yaml_text = (
            "id: DIR-001\n"
            "title: Example\n"
            "description: A directive\n"
            "severity: warn\n"
            "references:\n"
            "  - DIRECTIVE_032\n"
            "  - some-tactic-slug\n"
        )
        data = _load_yaml_str(yaml_text)
        directive = Directive(**data)

        assert directive.references == ["DIRECTIVE_032", "some-tactic-slug"]

        dumped = directive.model_dump(exclude_defaults=True)
        assert dumped["references"] == ["DIRECTIVE_032", "some-tactic-slug"]

    def test_references_accepts_empty_list_explicitly(self) -> None:
        directive = Directive(
            id="DIR-001", title="t", description="d", references=[]
        )
        assert directive.references == []


# ---------------------------------------------------------------------------
# DoctrineSelectionConfig.authority_paths
# ---------------------------------------------------------------------------


class TestDoctrineSelectionAuthorityPathsField:
    def test_default_is_empty_list(self) -> None:
        config = DoctrineSelectionConfig()
        assert config.authority_paths == []

    def test_default_is_not_shared_between_instances(self) -> None:
        a = DoctrineSelectionConfig()
        b = DoctrineSelectionConfig()
        a.authority_paths.append("docs/context/")
        assert b.authority_paths == []

    def test_round_trip_without_authority_paths(self) -> None:
        """Existing YAML lacking ``authority_paths:`` loads with ``[]`` and
        does not emit the new key when dumped with ``exclude_defaults=True``."""
        yaml_text = (
            "selected_paradigms: []\n"
            "selected_directives: []\n"
            "selected_tactics: []\n"
            "available_tools: []\n"
            "template_set: null\n"
        )
        data = _load_yaml_str(yaml_text)
        config = DoctrineSelectionConfig(**data)

        assert config.authority_paths == []

        dumped = config.model_dump(exclude_defaults=True)
        assert "authority_paths" not in dumped

    def test_round_trip_with_authority_paths(self) -> None:
        yaml_text = (
            "selected_paradigms: []\n"
            "selected_directives: []\n"
            "selected_tactics: []\n"
            "available_tools: []\n"
            "template_set: null\n"
            "authority_paths:\n"
            "  - docs/context/\n"
            "  - docs/adr/3.x/\n"
        )
        data = _load_yaml_str(yaml_text)
        config = DoctrineSelectionConfig(**data)

        assert config.authority_paths == [
            "docs/context/",
            "docs/adr/3.x/",
        ]

        dumped = config.model_dump(exclude_defaults=True)
        assert dumped["authority_paths"] == [
            "docs/context/",
            "docs/adr/3.x/",
        ]


# ---------------------------------------------------------------------------
# Backward compatibility: existing directives.yaml fixtures load cleanly
# ---------------------------------------------------------------------------


def _discover_directives_yaml_paths() -> list[Path]:
    """Find every ``directives.yaml`` under the repository tree."""
    # Walk up from this test file to locate the worktree / repo root.
    here = Path(__file__).resolve()
    # repo root = parent of ``tests``
    for ancestor in here.parents:
        if (ancestor / "tests").is_dir() and (ancestor / "src").is_dir():
            repo_root = ancestor
            break
    else:  # pragma: no cover — defensive
        return []

    candidates: list[Path] = []
    for path in repo_root.rglob("directives.yaml"):
        # Skip generated agent-copy directories and node_modules-style noise.
        parts = set(path.parts)
        if ".worktrees" in parts and repo_root.name not in path.relative_to(
            repo_root
        ).parts[:1]:
            # only include paths inside our own worktree
            pass
        candidates.append(path)
    return candidates


class TestExistingDirectivesFixturesStillLoad:
    def test_existing_directives_yaml_fixture_still_loads(self) -> None:
        """Sanity check: every existing ``directives.yaml`` under the repo
        deserializes into a valid ``DirectivesConfig`` after the additive
        schema change. NFR-005 backward compatibility."""
        paths = _discover_directives_yaml_paths()

        # The test is meaningful only if at least one fixture exists.
        if not paths:
            pytest.skip("No directives.yaml fixtures found in the repo tree")

        yaml = YAML(typ="safe")
        loaded_any = False
        for path in paths:
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = yaml.load(fh)
            except Exception:  # pragma: no cover — unreadable file
                continue

            if data is None:
                continue
            if not isinstance(data, dict):
                continue

            # Accept both the bare-list and the wrapped shape.
            if "directives" in data:
                DirectivesConfig(**data)
            else:
                # Some fixtures may be a single Directive doc; tolerate that.
                if {"id", "title"}.issubset(data.keys()):
                    Directive(**data)
                else:
                    continue
            loaded_any = True

        assert loaded_any, (
            "Found directives.yaml files but none matched expected shapes — "
            "this is a discovery bug, not a schema bug"
        )

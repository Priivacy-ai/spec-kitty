"""Tests for CharterBundleManifest v1.0.0.

Pins the v1.0.0 manifest contract. Regressions here indicate scope creep
or a change in the tracked/derived invariants.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from charter.bundle import (
    CANONICAL_MANIFEST,
    CharterBundleManifest,
    SCHEMA_VERSION,
)


def test_schema_version_is_1_0_0() -> None:
    assert SCHEMA_VERSION == "1.0.0"
    assert CANONICAL_MANIFEST.schema_version == "1.0.0"


def test_canonical_manifest_has_exactly_three_derived_files() -> None:
    assert len(CANONICAL_MANIFEST.derived_files) == 3
    names = {p.name for p in CANONICAL_MANIFEST.derived_files}
    assert names == {"governance.yaml", "directives.yaml", "metadata.yaml"}


def test_canonical_manifest_excludes_references_and_context_state() -> None:
    names = {p.name for p in CANONICAL_MANIFEST.derived_files}
    assert "references.yaml" not in names  # C-012
    assert "context-state.json" not in names  # C-012


def test_every_derived_file_has_a_derivation_source() -> None:
    for d in CANONICAL_MANIFEST.derived_files:
        assert d in CANONICAL_MANIFEST.derivation_sources


def test_every_derivation_source_is_tracked() -> None:
    for src in CANONICAL_MANIFEST.derivation_sources.values():
        assert src in CANONICAL_MANIFEST.tracked_files


def test_validator_rejects_overlap() -> None:
    with pytest.raises(ValidationError):
        CharterBundleManifest(
            schema_version="1.0.0",
            tracked_files=[Path("a")],
            derived_files=[Path("a")],
            derivation_sources={},
            gitignore_required_entries=[],
        )


def test_validator_rejects_orphan_derivation_source() -> None:
    with pytest.raises(ValidationError):
        CharterBundleManifest(
            schema_version="1.0.0",
            tracked_files=[Path("src.md")],
            derived_files=[Path("out.yaml")],
            derivation_sources={Path("out.yaml"): Path("missing.md")},
            gitignore_required_entries=[],
        )


def test_schema_version_regex_enforced() -> None:
    with pytest.raises(ValidationError):
        CharterBundleManifest(
            schema_version="not-semver",
            tracked_files=[Path("a.md")],
            derived_files=[],
            derivation_sources={},
            gitignore_required_entries=[],
        )


def test_gitignore_required_entries_is_must_include_not_exclusive() -> None:
    """Documentary: the set is MUST-INCLUDE, not 'only these'.

    Additional .gitignore entries (e.g., for out-of-scope files) are allowed.
    """
    entries = set(CANONICAL_MANIFEST.gitignore_required_entries)
    assert ".kittify/charter/governance.yaml" in entries
    assert ".kittify/charter/directives.yaml" in entries
    assert ".kittify/charter/metadata.yaml" in entries

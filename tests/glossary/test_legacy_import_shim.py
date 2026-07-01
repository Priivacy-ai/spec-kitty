"""Compatibility coverage for the extracted glossary package."""

from __future__ import annotations

import importlib
import sys

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_legacy_glossary_package_import_warns_and_points_to_canonical() -> None:
    sys.modules.pop("specify_cli.glossary", None)

    with pytest.warns(DeprecationWarning, match="import from glossary"):
        legacy = importlib.import_module("specify_cli.glossary")

    assert legacy.__canonical_import__ == "glossary"
    assert legacy.__removal_release__ == "3.3.0"


def test_legacy_glossary_submodule_import_aliases_canonical_module() -> None:
    sys.modules.pop("specify_cli.glossary", None)
    sys.modules.pop("specify_cli.glossary.models", None)

    canonical = importlib.import_module("glossary.models")
    with pytest.warns(DeprecationWarning):
        legacy = importlib.import_module("specify_cli.glossary.models")

    assert legacy is canonical

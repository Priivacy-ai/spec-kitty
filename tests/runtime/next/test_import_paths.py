"""Runtime package extraction import invariants."""

from __future__ import annotations

import importlib
import sys

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_runtime_next_is_canonical_decision_home() -> None:
    decision = importlib.import_module("runtime.next.decision")

    assert decision.Decision.__module__ == "runtime.next.decision"


def test_legacy_next_package_import_warns_and_aliases_submodules() -> None:
    for name in list(sys.modules):
        if name == "specify_cli.next" or name.startswith("specify_cli.next."):
            sys.modules.pop(name)

    canonical = importlib.import_module("runtime.next.runtime_bridge")
    with pytest.warns(DeprecationWarning, match="runtime.next"):
        legacy = importlib.import_module("specify_cli.next.runtime_bridge")

    assert legacy is canonical

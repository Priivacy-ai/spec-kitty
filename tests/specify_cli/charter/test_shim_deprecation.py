"""Tests for the DeprecationWarning emitted by the specify_cli.charter shim.

Contract: C-2 — Shim Deprecation Warning Contract.
"""

from __future__ import annotations

import importlib
import sys
import warnings

import pytest

# Opt out of the _neutralize_worktree_detection autouse fixture in tests/conftest.py
# (which imports the full specify_cli CLI chain and fails in partial worktree environments).
# Our tests only use importlib + warnings; they do not need CLI worktree neutralization.
pytestmark = pytest.mark.real_worktree_detection

LEGACY_IMPORT_SHAPES = [
    "specify_cli.charter",
    "specify_cli.charter.compiler",
    "specify_cli.charter.interview",
    "specify_cli.charter.resolver",
]


def _reset_modules() -> None:
    for m in list(sys.modules):
        if m.startswith("specify_cli.charter") or m == "charter" or m.startswith("charter."):
            sys.modules.pop(m, None)


@pytest.mark.parametrize("module_path", LEGACY_IMPORT_SHAPES)
def test_legacy_import_emits_deprecation_warning(module_path: str) -> None:
    _reset_modules()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        importlib.import_module(module_path)
    depr = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(depr) >= 1, (
        f"Importing {module_path} produced zero DeprecationWarnings; "
        f"expected at least one from the specify_cli.charter package __init__."
    )
    # The package-level warning is the one we mandate. Other libraries may emit
    # their own unrelated DeprecationWarnings during import; we only require that
    # ours fires, not that it is the only one.
    ours = [w for w in depr if "specify_cli.charter" in str(w.message)]
    assert ours, f"No DeprecationWarning mentioning 'specify_cli.charter' was emitted."
    assert len(ours) == 1, (
        f"Expected exactly one specify_cli.charter DeprecationWarning across "
        f"all import shapes; got {len(ours)}. Submodule shims must not re-warn."
    )
    msg = str(ours[0].message)
    assert "charter" in msg
    assert "specify_cli.charter" in msg
    assert "3.3.0" in msg  # removal release


def test_package_carries_deprecation_metadata() -> None:
    _reset_modules()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        pkg = importlib.import_module("specify_cli.charter")
    assert getattr(pkg, "__deprecated__", False) is True
    assert pkg.__canonical_import__ == "charter"
    assert pkg.__removal_release__ == "3.3.0"
    assert "specify_cli.charter" in pkg.__deprecation_message__
    assert pkg.__removal_release__ in pkg.__deprecation_message__

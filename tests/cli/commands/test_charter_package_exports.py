from __future__ import annotations

import pytest

import specify_cli.cli.commands.charter as charter_module

pytestmark = [pytest.mark.fast]

def test_charter_all_exports_are_defined() -> None:
    for name in charter_module.__all__:
        assert hasattr(charter_module, name), f"{name} listed in __all__ but not defined"

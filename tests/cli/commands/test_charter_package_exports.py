from __future__ import annotations

import json
import subprocess
import sys

import pytest

import specify_cli.cli.commands.charter as charter_module

pytestmark = [pytest.mark.unit, pytest.mark.integration]


def test_charter_all_exports_are_defined() -> None:
    for name in charter_module.__all__:
        assert hasattr(charter_module, name), f"{name} listed in __all__ but not defined"


def test_charter_package_cold_import_keeps_status_orchestration_out() -> None:
    """Regression for #1461: charter package import must not trigger status cycles."""
    script = """
from specify_cli.cli.commands.charter import app
import specify_cli.cli.commands.charter as charter_module
import sys

print(json.dumps({
    "app_imported": app is charter_module.app,
    "find_repo_root_exported": callable(charter_module.find_repo_root),
    "status_loaded": "specify_cli.status" in sys.modules,
    "status_emit_loaded": "specify_cli.status.emit" in sys.modules,
    "workspace_loaded": "specify_cli.workspace" in sys.modules,
    "agent_utils_status_loaded": "specify_cli.agent_utils.status" in sys.modules,
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", "import json\n" + script],
        check=True,
        text=True,
        capture_output=True,
    )

    result = json.loads(completed.stdout)
    assert result == {
        "app_imported": True,
        "find_repo_root_exported": True,
        "status_loaded": False,
        "status_emit_loaded": False,
        "workspace_loaded": False,
        "agent_utils_status_loaded": False,
    }

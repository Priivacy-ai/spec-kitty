import importlib
import pytest
pytestmark = pytest.mark.fast



def test_dashboard_public_api_imports():
    module = importlib.import_module("specify_cli.dashboard")
    for attr in (
        "ensure_dashboard_running",
        "stop_dashboard",
        "start_dashboard",
        "find_free_port",
        "scan_all_missions",
        "scan_mission_kanban",
        "run_diagnostics",
    ):
        assert hasattr(module, attr), f"dashboard module should expose {attr}"

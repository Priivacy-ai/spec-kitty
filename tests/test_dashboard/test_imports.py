import importlib


def test_dashboard_public_api_imports():
    module = importlib.import_module("specify_cli.dashboard")
    for attr in (
        "ensure_dashboard_running",
        "stop_dashboard",
        "start_dashboard",
        "find_free_port",
        "scan_all_features",
        "scan_feature_kanban",
        "run_diagnostics",
    ):
        assert hasattr(module, attr), f"dashboard module should expose {attr}"

"""Architectural guards for plugin-validation workflow ownership."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "plugin-validate.yml"

_PLUGIN_BUILD_INPUT_PATHS = {
    "pyproject.toml",
    "uv.lock",
    "src/specify_cli/tool_surface/bundles/**",
    "src/specify_cli/tool_surface/profiles/**",
    "src/specify_cli/skills/**",
    "src/specify_cli/cli/**",
    "src/doctrine/agent_profiles/**",
    "src/doctrine/hooks/**",
    "src/doctrine/.mcp.json",
    ".github/workflows/plugin-validate.yml",
}


def _workflow() -> dict[str, Any]:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _on_section(workflow: dict[str, Any]) -> dict[str, Any]:
    # PyYAML treats the YAML 1.1 key "on" as boolean True.
    return workflow.get("on") or workflow[True]


@pytest.mark.parametrize("event_name", ["push", "pull_request"])
def test_plugin_validate_triggers_cover_plugin_build_inputs(
    event_name: str,
) -> None:
    workflow = _workflow()
    paths = set(_on_section(workflow)[event_name]["paths"])

    missing = _PLUGIN_BUILD_INPUT_PATHS - paths
    assert not missing, (
        f"Plugin Validate {event_name} trigger misses plugin build inputs: "
        f"{sorted(missing)}"
    )

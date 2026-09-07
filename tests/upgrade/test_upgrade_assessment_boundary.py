"""Non-vacuous architecture floor for concrete upgrade assessments."""

from __future__ import annotations

import ast
import inspect

import pytest

from specify_cli.tool_surface.service import build_providers
from specify_cli.upgrade import assessment

pytestmark = pytest.mark.fast

EXPECTED_OWNERS = {
    "agent_profiles",
    "command_skills",
    "managed_skills",
    "native_config",
    "plugin_bundle",
    "session_presence",
    "slash_commands",
}
FORBIDDEN_ASSESSMENT_CALLS = {"write_text", "write_bytes", "mkdir", "unlink", "replace", "ensure_runtime"}


def test_concrete_owner_floor_cannot_shrink() -> None:
    owners = {provider.provider_key for provider in build_providers()}
    assert owners >= EXPECTED_OWNERS


def test_upgrade_assessment_has_separate_prepare_preflight_apply_boundaries() -> None:
    assert callable(assessment.prepare_upgrade_repairs)
    assert callable(assessment.preflight_upgrade_repairs)
    assert callable(assessment.apply_upgrade_repairs)
    tree = ast.parse(inspect.getsource(assessment.prepare_upgrade_repairs))
    calls = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert not (calls & FORBIDDEN_ASSESSMENT_CALLS)
    assert "apply_upgrade_repairs" not in calls


def test_operations_leaf_does_not_import_cli_or_providers() -> None:
    import specify_cli.tool_surface.operations as operations

    tree = ast.parse(inspect.getsource(operations))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} | {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert not any(name.startswith("specify_cli.cli") or ".providers" in name for name in imported)

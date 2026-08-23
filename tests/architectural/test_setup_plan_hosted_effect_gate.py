"""AST gate for setup-plan's single hosted-effects executor."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

ROOT = Path(__file__).resolve().parents[2]
SETUP_PLAN = ROOT / "src/specify_cli/cli/commands/agent/mission_setup_plan.py"
EXECUTOR = "_execute_setup_plan_hosted_effects"
DOSSIER_ADAPTER = "_trigger_dossier_sync"
DECISION_VALIDATOR = "is_canonical_hosted_sync_decision"

# Closed census of setup-plan-callable hosted producers. Additions must route
# through EXECUTOR (or its one narrow dossier adapter), never grow this set.
HOSTED_CALLS = frozenset(
    {
        "fanout_lifecycle_event_hosted",
        "trigger_feature_dossier_sync_if_enabled",
        "emit_artifact_phase",
        "OfflineQueue",
        "OfflineBodyUploadQueue",
        "queue_event",
        "queue_body_upload",
        "get_client",
        "get_async_client",
    }
)


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _hosted_effect_bypasses(source: str) -> list[tuple[str, str]]:
    """Return ``(owner, call)`` pairs outside the sanctioned authority."""
    tree = ast.parse(source)
    bypasses: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        allowed = node.name == EXECUTOR or (
            node.name == DOSSIER_ADAPTER
            and any(
                _call_name(call) == "trigger_feature_dossier_sync_if_enabled"
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
            )
        )
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            name = _call_name(call)
            if name in HOSTED_CALLS and not allowed:
                bypasses.append((node.name, name))
    return bypasses


def test_setup_plan_hosted_effects_have_one_authority() -> None:
    assert _hosted_effect_bypasses(SETUP_PLAN.read_text(encoding="utf-8")) == []

    tree = ast.parse(SETUP_PLAN.read_text(encoding="utf-8"))
    executor = next(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == EXECUTOR
    )
    assert any(
        isinstance(node, ast.Call) and _call_name(node) == DECISION_VALIDATOR
        for node in ast.walk(executor)
    )


def test_setup_plan_hosted_effect_gate_rejects_synthetic_bypass() -> None:
    source = SETUP_PLAN.read_text(encoding="utf-8")
    mutated = source + "\n\ndef bypass():\n    OfflineQueue().queue_event({})\n"
    bypasses = _hosted_effect_bypasses(mutated)
    assert ("bypass", "OfflineQueue") in bypasses
    assert ("bypass", "queue_event") in bypasses

"""Regression test for #571: typer OptionInfo leakage in programmatic calls.

When top_level_implement() is called as a Python function (not via CLI), any
optional parameter that retains its typer.models.OptionInfo default is truthy
and triggers unexpected branches (e.g., crash-recovery mode on every call).

This module verifies:
  1. The known-risky parameters (json_output, recover) have OptionInfo defaults,
     so future changes that accidentally remove our guard would be caught.
  2. Every call site in workflow.py passes those parameters as explicit Python
     literals, not relying on the OptionInfo defaults.
"""

from __future__ import annotations

import ast
import inspect

import pytest

pytestmark = pytest.mark.fast


def test_implement_has_optioninfo_defaults_for_risky_params() -> None:
    """The implement() CLI function uses typer.Option() as default for json_output and recover.

    This documents the known typer leakage risk (issue #571).  If this test ever
    fails it means the signature changed — re-audit workflow.py call sites.
    """
    from typer.models import OptionInfo

    from specify_cli.cli.commands.implement import implement

    sig = inspect.signature(implement)
    params = sig.parameters

    assert isinstance(params["json_output"].default, OptionInfo), "json_output default must be a typer OptionInfo (used to detect regression guard)"
    assert isinstance(params["recover"].default, OptionInfo), "recover default must be a typer OptionInfo (used to detect regression guard)"

    # Safe params — their default is the Python sentinel None, not OptionInfo
    assert params["mission"].default is None
    assert params["feature"].default is None
    assert params["base"].default is None


def test_workflow_calls_implement_with_explicit_python_bool_literals() -> None:
    """Every top_level_implement() call in workflow.py must pass json_output and recover
    as explicit Python bool literals (False), never relying on the OptionInfo default.

    Regression guard for #571.
    """
    from specify_cli.cli.commands.agent import workflow as workflow_module

    source = inspect.getsource(workflow_module)
    tree = ast.parse(source)

    implement_calls: list[ast.Call] = [
        node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "top_level_implement"
    ]

    assert implement_calls, "Expected at least one call to top_level_implement in workflow.py"

    for call in implement_calls:
        kwarg_map = {kw.arg: kw.value for kw in call.keywords}

        assert "json_output" in kwarg_map, "top_level_implement() must pass json_output= explicitly to prevent OptionInfo leakage"
        assert "recover" in kwarg_map, "top_level_implement() must pass recover= explicitly to prevent OptionInfo leakage"

        json_output_val = kwarg_map["json_output"]
        assert isinstance(json_output_val, ast.Constant) and json_output_val.value is False, "json_output must be the Python literal False at the call site"

        recover_val = kwarg_map["recover"]
        assert isinstance(recover_val, ast.Constant) and recover_val.value is False, "recover must be the Python literal False at the call site"

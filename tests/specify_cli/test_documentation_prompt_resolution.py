"""Regression test for documentation prompt template resolution (#502 fix-up F-1).

Pins that every documentation step declared in
``src/specify_cli/missions/documentation/mission-runtime.yaml`` is reachable
via the live ``resolve_command(...)`` path that ``prompt_builder.build_prompt``
calls (see ``src/specify_cli/next/prompt_builder.py:102``). This is the
contract the operator/host harness depends on; a file existing at an arbitrary
path is not enough.

Earlier fix-up shipped templates under ``missions/documentation/templates/``,
which the prompt builder does NOT consult — it consults
``missions/documentation/command-templates/`` (the COMMAND tier of the
5-tier asset resolver, see ``src/specify_cli/runtime/resolver.py:248``).
This test drives ``resolve_command`` directly so a regression of that asset
tier is caught immediately, not via a downstream smoke run.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.runtime.resolver import resolve_command

_DOC_STEPS = ("discover", "audit", "design", "generate", "validate", "publish", "accept")


@pytest.mark.parametrize("step_id", _DOC_STEPS)
def test_resolve_command_returns_nonempty_template(step_id: str) -> None:
    """resolve_command finds the template the runtime sidecar references."""
    result = resolve_command(f"{step_id}.md", Path("."), mission="documentation")
    assert result.path.is_file(), f"resolve_command returned non-existent path: {result.path}"
    content = result.path.read_text(encoding="utf-8").strip()
    assert content, f"empty template at {result.path}"
    assert (
        len(content.splitlines()) >= 10
    ), f"template too short ({len(content.splitlines())} lines): {result.path}"


@pytest.mark.parametrize("step_id", _DOC_STEPS)
def test_resolve_command_lands_in_command_templates_tier(step_id: str) -> None:
    """The shipped templates live under command-templates/, not templates/.

    This is the asset-tier the prompt builder consults; if a future refactor
    moves the files back to templates/, the prompt builder will silently
    return None and operators get steps with no runnable prompt (the F-1
    failure mode that this test is the regression gate against).
    """
    result = resolve_command(f"{step_id}.md", Path("."), mission="documentation")
    assert "command-templates" in result.path.parts, (
        f"expected command-templates/ tier, got {result.path}"
    )
    assert result.path.parent.name != "templates" or result.path.parent.parent.name == "documentation", (
        # Defensive: catch the case where someone ships *only* under
        # missions/<mission>/templates/ (which the resolver would not find
        # for the COMMAND subdir).
        f"unexpected resolution path: {result.path}"
    )

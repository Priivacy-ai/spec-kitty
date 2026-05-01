"""Regression test for research prompt template resolution.

Companion to ``test_documentation_prompt_resolution.py``. The research
mission's runtime sidecar (``src/specify_cli/missions/research/mission-runtime.yaml``)
declares ``prompt_template: <verb>.md`` for each step. The live prompt builder
calls ``resolve_command`` (``src/specify_cli/next/prompt_builder.py:102``)
which resolves the COMMAND tier (``missions/<mission>/command-templates/``,
per the 5-tier asset resolver at ``src/specify_cli/runtime/resolver.py:248``).

Before this regression-gate landed, research shipped its 6 action prompts at
``missions/research/templates/`` instead of ``command-templates/``, mirroring
the same F-1 mistake the documentation mission shipped. ``resolve_command``
raised ``FileNotFoundError`` for every research step, so the live runtime
returned ``prompt_file=None`` for any research mission that reached the
prompt-builder fast path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.runtime.resolver import resolve_command

_RESEARCH_STEPS = ("scoping", "methodology", "gathering", "synthesis", "output", "accept")


@pytest.mark.parametrize("step_id", _RESEARCH_STEPS)
def test_resolve_command_returns_nonempty_template(step_id: str) -> None:
    """resolve_command finds the template the runtime sidecar references."""
    result = resolve_command(f"{step_id}.md", Path("."), mission="research")
    assert result.path.is_file(), f"resolve_command returned non-existent path: {result.path}"
    content = result.path.read_text(encoding="utf-8").strip()
    assert content, f"empty template at {result.path}"


@pytest.mark.parametrize("step_id", _RESEARCH_STEPS)
def test_resolve_command_lands_in_command_templates_tier(step_id: str) -> None:
    """The shipped templates live under command-templates/, not templates/."""
    result = resolve_command(f"{step_id}.md", Path("."), mission="research")
    assert "command-templates" in result.path.parts, f"expected command-templates/ tier, got {result.path}"

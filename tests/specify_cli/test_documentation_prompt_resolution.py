"""Regression test for documentation prompt template resolution (#502 fix-up F-1).

Pins that every documentation step declared in
``src/specify_cli/missions/documentation/mission-runtime.yaml`` has a
shipped, non-empty markdown prompt template. This is the file-existence
gate; the runtime-level assertion that ``Decision.prompt_file`` resolves
non-null is exercised by the integration walk in WP02.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_DOC_STEPS = ("discover", "audit", "design", "generate", "validate", "publish", "accept")
_TEMPLATES_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "specify_cli"
    / "missions"
    / "documentation"
    / "templates"
)


@pytest.mark.parametrize("step_id", _DOC_STEPS)
def test_prompt_template_exists_and_is_nonempty(step_id: str) -> None:
    path = _TEMPLATES_DIR / f"{step_id}.md"
    assert path.is_file(), f"missing template: {path}"
    content = path.read_text(encoding="utf-8").strip()
    assert content, f"empty template: {path}"
    assert (
        len(content.splitlines()) >= 10
    ), f"template too short ({len(content.splitlines())} lines): {path}"

"""FR-027 tests: mission_type_activations filtering semantics."""
from __future__ import annotations

from pathlib import Path

import pytest

from charter.pack_context import PackContext

pytestmark = [pytest.mark.fast]


def test_only_specified_mission_type_is_activated(tmp_path: Path) -> None:
    """FR-027: mission_type_activations: [software-dev] excludes the other
    three built-in mission types from activated_mission_types."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "mission_type_activations:\n  - software-dev\n",
        encoding="utf-8",
    )

    ctx = PackContext.from_config(tmp_path)

    assert ctx.activated_mission_types == frozenset({"software-dev"}), (
        f"Expected only 'software-dev', got: {ctx.activated_mission_types}"
    )
    assert "documentation" not in ctx.activated_mission_types, (
        "documentation must be excluded when not listed in mission_type_activations"
    )
    assert "research" not in ctx.activated_mission_types, (
        "research must be excluded when not listed in mission_type_activations"
    )
    assert "plan" not in ctx.activated_mission_types, (
        "plan must be excluded when not listed in mission_type_activations"
    )

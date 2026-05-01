"""Parametrized structure tests for documentation mission step contracts (#502).

Owned by WP02. The profile-default assertion (FR-016) lives in WP05's
``tests/specify_cli/next/test_runtime_bridge_documentation_composition.py``
because ``executor._ACTION_PROFILE_DEFAULTS`` is WP05's authoritative surface;
this file therefore deliberately does not import from
``specify_cli.mission_step_contracts.executor``.

These tests assert the schema invariants from spec C-009:

- only the agreed top-level keys are present (no ``expected_artifacts``);
- ``id``/``action``/``mission`` are wired correctly per file;
- each contract has at least four steps (bootstrap + >=1 delegate + write + commit);
- no step carries the forbidden ``expected_artifacts`` field.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

_DOC_ACTIONS: tuple[str, ...] = (
    "discover",
    "audit",
    "design",
    "generate",
    "validate",
    "publish",
)

_SHIPPED: Path = Path(__file__).resolve().parents[3] / "src" / "doctrine" / "mission_step_contracts" / "shipped"

_ALLOWED_TOP_LEVEL_KEYS: frozenset[str] = frozenset({"schema_version", "id", "action", "mission", "steps"})


@pytest.mark.parametrize("action", _DOC_ACTIONS)
def test_contract_loads_with_correct_keys(action: str) -> None:
    """Each documentation contract loads and obeys C-009's structural invariants."""
    path = _SHIPPED / f"documentation-{action}.step-contract.yaml"
    assert path.is_file(), f"contract missing: {path}"

    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), f"expected mapping at top of {path}, got {type(raw).__name__}"
    data: dict[str, Any] = raw

    # Top-level keys (C-009 -- no expected_artifacts, no new top-level fields).
    extra_keys = set(data.keys()) - _ALLOWED_TOP_LEVEL_KEYS
    assert not extra_keys, f"unexpected top-level keys in {path.name}: {sorted(extra_keys)}"

    assert data["id"] == f"documentation-{action}"
    assert data["action"] == action
    assert data["mission"] == "documentation"

    steps = data["steps"]
    assert isinstance(steps, list), f"steps in {path.name} must be a list, got {type(steps).__name__}"
    assert len(steps) >= 4, f"{path.name} must declare at least 4 steps (bootstrap + >=1 delegate + write + commit); got {len(steps)}"

    # No expected_artifacts on any step (C-009).
    for step in steps:
        assert isinstance(step, dict), f"step in {path.name} must be a mapping, got {type(step).__name__}"
        assert "expected_artifacts" not in step, f"step {step.get('id')!r} in {path.name} has forbidden 'expected_artifacts' key"

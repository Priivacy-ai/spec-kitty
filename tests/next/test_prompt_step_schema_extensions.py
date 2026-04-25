"""Unit tests for `PromptStep` schema extensions (WP01).

These lock the contract for FR-008: optional `agent_profile` and
`contract_ref` fields on `PromptStep`, with `agent_profile` accepting
either the snake-case canonical name or the kebab-case alias when parsed
from YAML / dict input.
"""

from __future__ import annotations

import pytest

from specify_cli.next._internal_runtime.schema import PromptStep


def test_default_fields_are_none() -> None:
    step = PromptStep(id="x", title="X")
    assert step.agent_profile is None
    assert step.contract_ref is None


@pytest.mark.parametrize(
    "key",
    ["agent_profile", "agent-profile"],
    ids=["snake-alias", "kebab-alias"],
)
def test_agent_profile_alias_parses(key: str) -> None:
    step = PromptStep.model_validate(
        {"id": "x", "title": "X", key: "implementer-ivan"}
    )
    assert step.agent_profile == "implementer-ivan"


def test_contract_ref_parses() -> None:
    set_step = PromptStep.model_validate(
        {"id": "x", "title": "X", "contract_ref": "abc"}
    )
    assert set_step.contract_ref == "abc"

    default_step = PromptStep.model_validate({"id": "x", "title": "X"})
    assert default_step.contract_ref is None


def test_both_set_round_trip() -> None:
    original = PromptStep.model_validate(
        {
            "id": "x",
            "title": "X",
            "agent_profile": "implementer-ivan",
            "contract_ref": "contract-123",
        }
    )
    assert original.agent_profile == "implementer-ivan"
    assert original.contract_ref == "contract-123"

    dumped = original.model_dump(by_alias=True)
    assert dumped["agent-profile"] == "implementer-ivan"
    assert dumped["contract_ref"] == "contract-123"

    revived = PromptStep.model_validate(dumped)
    assert revived.agent_profile == "implementer-ivan"
    assert revived.contract_ref == "contract-123"
    assert revived == original

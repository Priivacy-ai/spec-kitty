"""Regression tests for generated agent-profile JSON schema parity."""

from pathlib import Path

import jsonschema
import pytest
from ruamel.yaml import YAML

from scripts.generate_schemas import generate_schema

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

BUILT_IN_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "src"
    / "doctrine"
    / "agent_profiles"
    / "built-in"
)


def test_generated_agent_profile_schema_preserves_extension_fields() -> None:
    """Schema model must not drop shipped scoping and augmentation fields."""
    schema = generate_schema("agent-profile")
    properties = schema["properties"]

    assert "overrides" in properties
    assert "enhances" in properties
    assert "applies_to_languages" in properties
    assert schema["anyOf"] == [{"required": ["role"]}, {"required": ["roles"]}]


def test_generated_agent_profile_schema_validates_shipped_scoped_profile() -> None:
    """Freshly generated schema must accept built-in profiles, not only committed YAML."""
    yaml = YAML(typ="safe")
    with (BUILT_IN_DIR / "python-pedro.agent.yaml").open() as f:
        profile = yaml.load(f)

    validator = jsonschema.Draft202012Validator(generate_schema("agent-profile"))
    errors = sorted(validator.iter_errors(profile), key=lambda error: list(error.path))

    assert errors == []


@pytest.mark.parametrize("field_name", ["overrides", "enhances"])
def test_generated_agent_profile_schema_validates_augmentation_fields(field_name: str) -> None:
    """Generated schema must accept declared profile override/enhance intent."""
    profile = {
        "profile-id": "org-python-pedro",
        "name": "Org Python Pedro",
        "roles": ["implementer"],
        "purpose": "Validate augmentation intent fields.",
        "specialization": {"primary-focus": "Python implementation"},
        field_name: "python-pedro",
    }

    validator = jsonschema.Draft202012Validator(generate_schema("agent-profile"))
    errors = sorted(validator.iter_errors(profile), key=lambda error: list(error.path))

    assert errors == []

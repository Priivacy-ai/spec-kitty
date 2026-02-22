"""Schema validation tests for doctrine governance artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "src" / "doctrine" / "schemas"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

SCHEMA_FILES = {
    "mission": SCHEMA_DIR / "mission.schema.yaml",
    "directive": SCHEMA_DIR / "directive.schema.yaml",
    "tactic": SCHEMA_DIR / "tactic.schema.yaml",
    "import-candidate": SCHEMA_DIR / "import-candidate.schema.yaml",
    "agent-profile": SCHEMA_DIR / "agent-profile.schema.yaml",
    "styleguide": SCHEMA_DIR / "styleguide.schema.yaml",
    "toolguide": SCHEMA_DIR / "toolguide.schema.yaml",
}


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict), f"{path}: expected mapping root"
    return data


def _schema_validator(schema_name: str) -> Draft202012Validator:
    schema_path = SCHEMA_FILES[schema_name]
    schema = _load_yaml(schema_path)
    return Draft202012Validator(schema)


def _error_message(schema_name: str, fixture_path: Path, error) -> str:
    pointer = "/" + "/".join(str(part) for part in error.path) if error.path else "/"
    return f"schema={schema_name} fixture={fixture_path.name} path={pointer} message={error.message}"


@pytest.mark.parametrize("schema_name", sorted(SCHEMA_FILES.keys()))
def test_valid_fixtures_pass(schema_name: str) -> None:
    validator = _schema_validator(schema_name)
    valid_dir = FIXTURE_DIR / schema_name / "valid"
    fixture_paths = sorted(valid_dir.glob("*.yaml"))

    assert fixture_paths, f"No valid fixtures found for {schema_name}"

    for fixture_path in fixture_paths:
        instance = _load_yaml(fixture_path)
        errors = sorted(validator.iter_errors(instance), key=str)
        assert not errors, "\n".join(_error_message(schema_name, fixture_path, error) for error in errors)


@pytest.mark.parametrize("schema_name", sorted(SCHEMA_FILES.keys()))
def test_invalid_fixtures_fail(schema_name: str) -> None:
    validator = _schema_validator(schema_name)
    invalid_dir = FIXTURE_DIR / schema_name / "invalid"
    fixture_paths = sorted(invalid_dir.glob("*.yaml"))

    assert fixture_paths, f"No invalid fixtures found for {schema_name}"

    for fixture_path in fixture_paths:
        instance = _load_yaml(fixture_path)
        errors = sorted(validator.iter_errors(instance), key=str)
        assert errors, f"schema={schema_name} fixture={fixture_path.name} expected validation errors but got none"

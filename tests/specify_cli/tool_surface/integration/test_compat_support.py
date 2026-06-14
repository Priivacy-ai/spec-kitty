"""Focused unit tests for the compatibility-gate helpers.

Every branch/helper in ``_compat_support`` is exercised directly here so the
shared utilities carry their own coverage (per the Sonar new-code discipline),
independent of the subprocess-driven integration tests.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import _compat_support as cs

import pytest

pytestmark = [pytest.mark.integration]


def test_schema_shape_scalars() -> None:
    assert cs.schema_shape("hi") == "str"
    assert cs.schema_shape(3) == "int"
    assert cs.schema_shape(True) == "bool"
    assert cs.schema_shape(1.5) == "float"
    assert cs.schema_shape(None) == "null"


def test_schema_shape_dict_keys_sorted() -> None:
    shape = cs.schema_shape({"b": 1, "a": "x"})
    assert list(shape.keys()) == ["a", "b"]
    assert shape == {"a": "str", "b": "int"}


def test_schema_shape_empty_list() -> None:
    assert cs.schema_shape([]) == []


def test_schema_shape_list_of_scalars() -> None:
    assert cs.schema_shape(["a", "b"]) == ["str"]


def test_schema_shape_list_of_dicts_merges() -> None:
    shape = cs.schema_shape([{"a": 1}, {"b": "x"}])
    assert shape == [{"a": "int", "b": "str"}]


def test_schema_shape_nested() -> None:
    value = {"outer": {"inner": [1]}, "flag": None}
    assert cs.schema_shape(value) == {"flag": "null", "outer": {"inner": ["int"]}}


def test_render_config_yaml_with_agents() -> None:
    text = cs._render_config_yaml(["codex", "claude"])
    assert "agents:" in text
    assert "    - codex" in text
    assert "    - claude" in text


def test_render_config_yaml_empty_uses_inline_list() -> None:
    text = cs._render_config_yaml([])
    assert "  available: []" in text
    assert "    - " not in text


def test_write_controlled_project_creates_marker_files(tmp_path: Path) -> None:
    root = cs.write_controlled_project(tmp_path)
    assert root == tmp_path
    config = (tmp_path / ".kittify" / "config.yaml").read_text(encoding="utf-8")
    assert "- codex" in config
    manifest = json.loads(
        (tmp_path / ".kittify" / "command-skills-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest == cs.EMPTY_MANIFEST


def test_write_controlled_project_custom_agents(tmp_path: Path) -> None:
    cs.write_controlled_project(tmp_path, agents=["claude", "pi"])
    config = (tmp_path / ".kittify" / "config.yaml").read_text(encoding="utf-8")
    assert "- claude" in config
    assert "- pi" in config
    assert "codex" not in config


def test_write_controlled_project_empty_agents(tmp_path: Path) -> None:
    cs.write_controlled_project(tmp_path, agents=[])
    config = (tmp_path / ".kittify" / "config.yaml").read_text(encoding="utf-8")
    assert "available: []" in config


def test_project_root_resolves_to_checkout() -> None:
    root = cs.project_root()
    assert (root / "pyproject.toml").exists()


def test_cli_result_json_parses_stdout() -> None:
    result = cs.CliResult(returncode=0, stdout='{"a": 1}', stderr="")
    assert result.json() == {"a": 1}


def test_constants_are_machine_independent() -> None:
    assert cs.CONTROLLED_AGENT == "codex"
    assert cs.EMPTY_MANIFEST == {"schema_version": 1, "entries": []}


def test_compat_tests_never_shell_out_to_path_binary() -> None:
    """Guard: the subprocess-driven compat tests must use the checkout-local
    helper, never ``subprocess.run([<spec-kitty>, ...])`` against PATH.

    The forbidden literal is assembled at runtime so this scanner file does not
    itself contain it (which would make the scan self-referential).
    """
    here = Path(__file__).parent
    binary = "spec-" + "kitty"  # avoid embedding the literal in this file
    forbidden = [f'subprocess.run(["{binary}"', f"subprocess.run(['{binary}'"]
    for name in ("test_migration_compat.py", "test_agent_config_compat.py"):
        source = (here / name).read_text(encoding="utf-8")
        assert "run_spec_kitty" in source, f"{name} must use the shared helper"
        for pattern in forbidden:
            assert pattern not in source, f"{name} shells out to PATH: {pattern}"

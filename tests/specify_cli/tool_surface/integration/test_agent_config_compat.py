"""Migration compatibility gate for ``spec-kitty agent config list/status/sync``.

Unlike ``doctor skills``, the ``agent config`` subcommands have NO ``--json``
flag -- their external interface is the command surface, exit codes, and stable
human-readable markers. These tests freeze that interface so a subsequent WP
that removes a subcommand, drops a marker, or changes exit semantics is caught.

The committed interface descriptor lives in
``fixtures/agent_config_list_schema.json``; these tests assert the live CLI
still conforms to it. They run the checkout-local ``specify_cli`` package
against a controlled ``.kittify`` fixture so results are deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._compat_support import run_spec_kitty, write_controlled_project

import pytest

pytestmark = [pytest.mark.integration]

_FIXTURES = Path(__file__).parent / "fixtures"
_SCHEMA = _FIXTURES / "agent_config_list_schema.json"


def _load_schema() -> dict[str, object]:
    data: dict[str, object] = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    return data


def _subcommand_descriptor(name: str) -> dict[str, object]:
    schema = _load_schema()
    subcommands = schema["subcommands"]
    assert isinstance(subcommands, dict)
    descriptor = subcommands[name]
    assert isinstance(descriptor, dict)
    return descriptor


def test_agent_config_list_interface_stable(tmp_path: Path) -> None:
    project = write_controlled_project(tmp_path)
    descriptor = _subcommand_descriptor("list")
    result = run_spec_kitty("agent", "config", "list", cwd=project)
    assert result.returncode == descriptor["success_exit_code"], result.stderr
    markers = descriptor["required_markers"]
    assert isinstance(markers, list)
    for marker in markers:
        assert marker in result.stdout, f"agent config list dropped marker: {marker!r}"


def test_agent_config_status_interface_stable(tmp_path: Path) -> None:
    project = write_controlled_project(tmp_path)
    descriptor = _subcommand_descriptor("status")
    result = run_spec_kitty("agent", "config", "status", cwd=project)
    assert result.returncode == descriptor["success_exit_code"], result.stderr
    markers = descriptor["required_markers"]
    assert isinstance(markers, list)
    for marker in markers:
        assert marker in result.stdout, f"agent config status dropped marker: {marker!r}"


def test_agent_config_sync_keep_orphaned_is_no_op(tmp_path: Path) -> None:
    """sync --keep-orphaned on a fixture with no orphans makes NO state changes."""
    project = write_controlled_project(tmp_path)
    descriptor = _subcommand_descriptor("sync")
    # Snapshot the project tree before and after the dry-run-style sync.
    before = sorted(p.name for p in (project / ".kittify").iterdir())
    result = run_spec_kitty("agent", "config", "sync", "--keep-orphaned", cwd=project)
    assert result.returncode == descriptor["success_exit_code"], result.stderr
    marker = descriptor["idempotent_keep_orphaned_marker"]
    assert isinstance(marker, str)
    assert marker in result.stdout
    after = sorted(p.name for p in (project / ".kittify").iterdir())
    assert before == after, "sync --keep-orphaned must not mutate the project tree"


def test_agent_config_list_has_no_json_flag(tmp_path: Path) -> None:
    """Frozen fact: ``agent config list`` does not expose ``--json``.

    If a future WP adds ``--json`` that is an *additive* change and this test
    must be updated alongside the contract doc -- it is here to make the
    interface boundary explicit, not to forbid evolution.
    """
    project = write_controlled_project(tmp_path)
    descriptor = _subcommand_descriptor("list")
    assert descriptor["json_flag"] is False
    result = run_spec_kitty("agent", "config", "list", "--json", cwd=project)
    # Unknown option => non-zero exit from the CLI parser.
    assert result.returncode != 0


def test_agent_config_schema_descriptor_is_machine_independent() -> None:
    """The interface descriptor must not leak machine-specific paths."""
    raw = _SCHEMA.read_text(encoding="utf-8")
    assert str(Path.home()) not in raw
    schema = _load_schema()
    subcommands = schema["subcommands"]
    assert isinstance(subcommands, dict)
    assert set(subcommands) == {"list", "status", "sync"}

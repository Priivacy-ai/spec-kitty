"""Golden CLI characterization harness for the ``agent tasks`` command surface.

This module is the safety net described by WP01 of the
``decompose-agent-tasks-god-module-01KVWVAR`` mission (FR-001). It captures the
*current* externally-observable behaviour of the ``agent tasks`` Typer ``app``
so that the later decomposition work packages (WP02-07) can be proven
byte-identical against this frozen baseline.

It pins the five invariants from
``kitty-specs/decompose-agent-tasks-god-module-01KVWVAR/contracts/cli-surface-contract.md``:

* **CONTRACT-1** -- ``agent tasks --help`` exposes exactly the 9 documented
  commands (no additions/removals/renames).
* **CONTRACT-2** -- each command exposes (at least) the documented flags with
  unchanged names.
* **CONTRACT-3** -- exit codes are unchanged: ``0`` success, ``1``
  validation/refusal, ``2`` usage / mission-not-found.
* **CONTRACT-4** -- ``--json`` envelopes keep their existing top-level keys for
  the success, error, and ``--validate-only`` paths.
* (CONTRACT-5 -- protected-primary refusal byte-identity -- is exercised by the
  commit-routing WP; this harness only freezes the command surface those WPs
  build on.)

Capture mechanism: ``typer.testing.CliRunner`` invoking the ``app`` object
directly (never the installed CLI). Expected output is stored as committed
fixtures under ``fixtures/tasks_cli/`` and compared in-test -- no snapshot
dependency is added.

This file holds only the PURE in-process contract tests (help fixtures,
command/flag structure, and ``--json`` envelope shapes). The subprocess /
real-git coord-topology fixtures, the mutating-command characterization
(T003-T007), and the from-harness branch-coverage ratchet live in the sibling
``test_tasks_cli_contract_coord.py`` — split out so these pure tests can stay in
the ``fast`` lane (marker-correctness Rules 1 & 2).
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import click
import pytest
from typer.main import get_command
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests.mocked_env import setup_mocked_env

# Every test in this file drives the ``app`` object in-process via
# ``CliRunner`` — no subprocess, no git — so it is a sub-second ``fast`` test
# (marker-correctness Rules 1 & 2).
pytestmark = pytest.mark.fast

runner = CliRunner()

FIXTURES = Path(__file__).parent / "fixtures" / "tasks_cli"
HELP_FIXTURES = FIXTURES / "help"
JSON_FIXTURES = FIXTURES / "json"

# Fixed terminal width keeps Rich's help rendering deterministic across
# machines, terminal sizes, and CI; it must match the width used to generate
# the committed help fixtures.
HELP_ENV = {"COLUMNS": "100", "TERM": "dumb", "NO_COLOR": "1"}

# The 9 frozen commands (CONTRACT-1).
COMMANDS = (
    "move-task",
    "mark-status",
    "list-tasks",
    "add-history",
    "finalize-tasks",
    "map-requirements",
    "validate-workflow",
    "status",
    "list-dependents",
)

# The documented flags per command (CONTRACT-2). The live command may expose
# *additional* flags (e.g. move-task carries reviewer-fallback options); the
# contract pins these as a required subset so a *removal/rename* fails loudly
# while an additive change does not.
CONTRACT_FLAGS: dict[str, tuple[str, ...]] = {
    "move-task": (
        "--to",
        "--mission",
        "--agent",
        "--assignee",
        "--shell-pid",
        "--note",
        "--review-feedback-file",
        "--approval-ref",
        "--reviewer",
        "--self-review-fallback",
        "--force",
        "--auto-commit",
        "--json",
    ),
    "mark-status": ("--status", "--mission", "--auto-commit", "--json"),
    "list-tasks": ("--lane", "--mission", "--json"),
    "add-history": ("--note", "--mission", "--agent", "--shell-pid", "--json"),
    "finalize-tasks": ("--mission", "--json", "--validate-only"),
    "map-requirements": (
        "--wp",
        "--refs",
        "--batch",
        "--replace",
        "--tracker-ref",
        "--mission",
        "--json",
        "--auto-commit",
    ),
    "validate-workflow": ("--mission", "--json"),
    "status": ("--mission", "--json", "--stale-threshold"),
    "list-dependents": ("--mission", "--json"),
}


# ---------------------------------------------------------------------------
# T001 -- capture harness
# ---------------------------------------------------------------------------


def _click_group() -> click.Group:
    command = get_command(app)
    assert isinstance(command, click.Group)
    return command


def _command_flags(name: str) -> set[str]:
    """Return the long-form option flags of a single command via introspection.

    Click introspection is used (rather than parsing Rich-rendered ``--help``)
    because Rich truncates long flag names with an ellipsis at narrow widths;
    the parsed param model is exact and version-stable.
    """
    cmd = _click_group().commands[name]
    flags: set[str] = set()
    for param in cmd.params:
        if isinstance(param, click.Option):
            flags.update(param.opts)
    return flags


# ---------------------------------------------------------------------------
# T002 -- golden --help fixtures + structural command/flag contract
# ---------------------------------------------------------------------------


def test_top_level_help_lists_exactly_the_nine_commands() -> None:
    """CONTRACT-1: the command group exposes exactly the 9 frozen commands."""
    assert set(_click_group().commands.keys()) == set(COMMANDS)


def test_group_help_matches_golden_fixture() -> None:
    result = runner.invoke(app, ["--help"], env=HELP_ENV)
    assert result.exit_code == 0
    fixture = (HELP_FIXTURES / "_group.txt").read_text(encoding="utf-8")
    assert result.stdout == fixture


@pytest.mark.parametrize("command", COMMANDS)
def test_command_help_matches_golden_fixture(command: str) -> None:
    """CONTRACT-2 (text): each command's rendered help is byte-frozen."""
    result = runner.invoke(app, [command, "--help"], env=HELP_ENV)
    assert result.exit_code == 0, result.stdout
    fixture = (HELP_FIXTURES / f"{command}.txt").read_text(encoding="utf-8")
    assert result.stdout == fixture


@pytest.mark.parametrize("command", COMMANDS)
def test_command_exposes_contract_flags(command: str) -> None:
    """CONTRACT-2 (structure): documented flags are present and unrenamed."""
    live = _command_flags(command)
    missing = [flag for flag in CONTRACT_FLAGS[command] if flag not in live]
    assert not missing, f"{command} is missing contract flags: {missing}"


# ---------------------------------------------------------------------------
# T003 -- exit-code + --json envelope fixtures
# ---------------------------------------------------------------------------


def _envelopes() -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = json.loads(
        (JSON_FIXTURES / "envelopes.json").read_text(encoding="utf-8")
    )
    return data


# Free-form maps whose keys are data-dependent (mission / WP / lane names). The
# fixture pins these as the opaque marker below; the harness asserts only that
# the live value is a dict, so a value change does not break the contract but a
# structural change (e.g. dict -> list) still does.
_OPAQUE_MAP = "<map>"


def _shape(obj: Any, key: str | None = None, freeform: set[str] | None = None) -> Any:
    freeform = freeform or set()
    if isinstance(obj, dict):
        if key in freeform:
            return _OPAQUE_MAP
        return {k: _shape(v, k, freeform) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_shape(obj[0], None, freeform)] if obj else []
    return type(obj).__name__


def _freeform_keys(shape: Any) -> set[str]:
    """Collect the keys the fixture marked as opaque free-form maps."""
    found: set[str] = set()
    if isinstance(shape, dict):
        for k, v in shape.items():
            if v == _OPAQUE_MAP:
                found.add(k)
            else:
                found |= _freeform_keys(v)
    elif isinstance(shape, list):
        for item in shape:
            found |= _freeform_keys(item)
    return found


def _result_streams(result: Any) -> tuple[str, str]:
    out = result.stdout or ""
    try:
        err = result.stderr or ""
    except (ValueError, AttributeError):
        err = ""
    return out, err


def _build_demo_mission(tmp_path: Path) -> str:
    """Stage a minimal-but-real mission so success ``--json`` paths can run."""
    slug = "099-demo"
    (tmp_path / ".kittify").mkdir()
    feature_dir = tmp_path / "kitty-specs" / slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": slug,
                "mission_number": "099",
                "mission_type": "software-dev",
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n## WP01 First\n- [ ] T001 do thing\n", encoding="utf-8"
    )
    (tasks_dir / "WP01-test.md").write_text(
        textwrap.dedent(
            """\
            ---
            work_package_id: WP01
            title: Test WP01
            dependencies: []
            execution_mode: code_change
            ---
            # WP01
            """
        ),
        encoding="utf-8",
    )
    append_event(
        feature_dir,
        StatusEvent(
            event_id="contract-seed",
            mission_slug=slug,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.APPROVED,
            at="2026-01-01T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
        ),
    )
    return slug


@pytest.mark.parametrize(
    "case",
    [
        "mission_not_found_status",
        "mission_not_found_list_tasks",
    ],
)
def test_error_envelope_shape(case: str) -> None:
    """CONTRACT-3 + CONTRACT-4: mission-not-found envelope keys and exit code."""
    spec = _envelopes()[case]
    result = runner.invoke(app, spec["argv"])
    assert result.exit_code == spec["exit_code"]
    out, err = _result_streams(result)
    blob = err if err.strip() else out
    payload = json.loads(blob)
    assert _shape(payload) == spec["json_shape"]


def test_validation_error_exit_one() -> None:
    """CONTRACT-3: an invalid input value refuses with exit 1 and a plain message."""
    spec = _envelopes()["validation_error_mark_status"]
    result = runner.invoke(app, spec["argv"])
    assert result.exit_code == spec["exit_code"] == 1
    assert spec["stdout_contains"] in (result.stdout or "")


def test_usage_error_exit_two() -> None:
    """CONTRACT-3: a missing required argument is a usage error with exit 2."""
    spec = _envelopes()["usage_error_missing_arg"]
    result = runner.invoke(app, spec["argv"])
    assert result.exit_code == spec["exit_code"] == 2
    _, err = _result_streams(result)
    assert spec["stderr_contains"] in err


@pytest.mark.parametrize(
    "case",
    [
        "success_status",
        "success_list_tasks",
        "success_finalize_validate_only",
    ],
)
def test_success_envelope_shape(case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CONTRACT-4: success ``--json`` envelopes keep their top-level keys/types."""
    spec = _envelopes()[case]
    freeform = _freeform_keys(spec["json_shape"])
    slug = _build_demo_mission(tmp_path)
    monkeypatch.chdir(tmp_path)
    workspace = SimpleNamespace(execution_mode="code_change", resolution_kind="lane_workspace")
    # Replace the placeholder mission slug in the captured argv with the slug we
    # just staged, so the captured command runs against the demo mission.
    argv = [slug if arg == "099-demo" else arg for arg in spec["argv"]]
    with setup_mocked_env(tmp_path, workspace_resolution=workspace):
        result = runner.invoke(app, argv)
    assert result.exit_code == spec["exit_code"] == 0, result.output
    payload = json.loads(result.stdout)
    assert _shape(payload, freeform=freeform) == spec["json_shape"]

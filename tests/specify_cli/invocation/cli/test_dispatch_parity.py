"""Parity tests for the canonical `spec-kitty dispatch` command and its
first-class aliases `do` / `ask` / `advise` (WP03, NFR-001 / FR-005 / C-002).

The binding contract is `contracts/dispatch-parity.md`: for equivalent inputs
the Op-record JSONL at ``invocation_path(<invocation_id>)`` MUST be
byte/contract-identical across the canonical command and its alias, field-for-
field except the unique ``invocation_id`` and timestamps. The mode mapping
(do/ask/dispatch -> task_execution; advise -> advisory) and the ``--json``
envelope + exit codes must also match.

These tests source the Op-record path from ``invocation/writer.py`` (via
``InvocationWriter.invocation_path``) — never hard-coded — per the contract.
"""

from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import Result
from typer import Typer
from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.invocation.modes import ModeOfWork, derive_mode
from specify_cli.invocation.writer import EVENTS_DIR, InvocationWriter

# Marked for mutmut sandbox skip — subprocess-style CLI invocation.
pytestmark = pytest.mark.non_sandbox

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "profiles"

# Volatile fields that legitimately differ between two distinct invocations and
# are therefore excluded from the field-for-field parity comparison.
_VOLATILE_FIELDS = frozenset({"invocation_id", "started_at", "completed_at", "at", "timestamp"})


class ArgvCliRunner(CliRunner):
    def invoke(  # type: ignore[override]
        self,
        app: Typer,
        args: str | Sequence[str] | None = None,
        **kwargs: Any,
    ) -> Result:
        argv = ["spec-kitty", *(list(args) if args is not None and not isinstance(args, str) else [])]
        with patch.object(sys, "argv", argv):
            return super().invoke(app, args, **kwargs)


runner = ArgvCliRunner()

_COMPACT_CTX = MagicMock()
_COMPACT_CTX.mode = "compact"
_COMPACT_CTX.text = "compact governance context"


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal project with the fixture profiles installed."""
    profiles_dir = tmp_path / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)
    return tmp_path


def _strip_volatile(record: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the record without volatile (id/timestamp) fields."""
    return {k: v for k, v in record.items() if k not in _VOLATILE_FIELDS}


def _strip_glossary_timing(observations: Any) -> Any:
    """Drop the volatile `duration_ms` measurement from a glossary-observations
    dict so two runs can be compared by contract shape, not wall-clock timing."""
    if isinstance(observations, dict):
        return {k: v for k, v in observations.items() if k != "duration_ms"}
    return observations


def _read_op_record(project: Path, invocation_id: str) -> list[dict[str, Any]]:
    """Read the Op-record JSONL using the canonical writer path.

    The path is sourced from ``InvocationWriter.invocation_path`` — the contract
    forbids hard-coding ``kitty-ops/<id>.jsonl`` here.
    """
    path = InvocationWriter(project).invocation_path(invocation_id)
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _run(project: Path, args: list[str]) -> Result:
    """Invoke the CLI against a fixture project with charter context mocked.

    The `dispatch`, `do_cmd`, and `advise` modules each resolve the repo root
    through their own module-level `find_repo_root`, so all three seams are
    patched to the fixture project.
    """
    with (
        patch("specify_cli.cli.commands.dispatch.find_repo_root", return_value=project),
        patch("specify_cli.cli.commands.advise.find_repo_root", return_value=project),
        patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
        patch(
            "specify_cli.invocation.executor.build_charter_context",
            return_value=_COMPACT_CTX,
        ),
    ):
        return runner.invoke(cli_app, args)


def _invoke_json(project: Path, args: list[str]) -> dict[str, Any]:
    """Run a `--json` invocation, assert exit 0, return the parsed envelope."""
    result = _run(project, args)
    assert result.exit_code == 0, result.output
    envelope: dict[str, Any] = json.loads(result.output)
    return envelope


# ---------------------------------------------------------------------------
# Op-record JSONL parity (NFR-001)
# ---------------------------------------------------------------------------


class TestOpRecordParity:
    def test_dispatch_vs_do_op_record_identical(self, tmp_path: Path) -> None:
        """dispatch and do produce byte/contract-identical Op records (minus volatile fields)."""
        project = _setup_project(tmp_path)
        dispatch_env = _invoke_json(
            project, ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"]
        )
        do_env = _invoke_json(
            project, ["do", "implement the feature", "--profile", "implementer-fixture", "--json"]
        )

        dispatch_rec = _read_op_record(project, str(dispatch_env["invocation_id"]))
        do_rec = _read_op_record(project, str(do_env["invocation_id"]))

        assert len(dispatch_rec) == len(do_rec) == 1, "started-only Op (open)"
        assert _strip_volatile(dispatch_rec[0]) == _strip_volatile(do_rec[0])

    def test_dispatch_vs_ask_op_record_identical(self, tmp_path: Path) -> None:
        """dispatch and ask (both task_execution) produce identical Op records."""
        project = _setup_project(tmp_path)
        dispatch_env = _invoke_json(
            project, ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"]
        )
        ask_env = _invoke_json(project, ["ask", "implementer-fixture", "implement the feature", "--json"])

        dispatch_rec = _read_op_record(project, str(dispatch_env["invocation_id"]))
        ask_rec = _read_op_record(project, str(ask_env["invocation_id"]))

        assert _strip_volatile(dispatch_rec[0]) == _strip_volatile(ask_rec[0])

    def test_advise_op_record_differs_only_by_mode(self, tmp_path: Path) -> None:
        """advise (advisory) matches dispatch (task_execution) on every Op-record
        field except mode_of_work — the one deliberate verb difference."""
        project = _setup_project(tmp_path)
        dispatch_env = _invoke_json(
            project, ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"]
        )
        advise_env = _invoke_json(
            project, ["advise", "implement the feature", "--profile", "implementer-fixture", "--json"]
        )

        dispatch_rec = _strip_volatile(_read_op_record(project, str(dispatch_env["invocation_id"]))[0])
        advise_rec = _strip_volatile(_read_op_record(project, str(advise_env["invocation_id"]))[0])

        # mode_of_work is the only field allowed to differ.
        assert dispatch_rec.get("mode_of_work") == "task_execution"
        assert advise_rec.get("mode_of_work") == "advisory"
        dispatch_rec.pop("mode_of_work", None)
        advise_rec.pop("mode_of_work", None)
        assert dispatch_rec == advise_rec

    def test_op_record_carries_required_v2_fields(self, tmp_path: Path) -> None:
        """The started event carries the contract-required v2 fields."""
        project = _setup_project(tmp_path)
        env = _invoke_json(
            project, ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"]
        )
        record = _read_op_record(project, str(env["invocation_id"]))[0]
        for field in ("invocation_id", "profile_id", "action", "request_text", "actor", "mode_of_work"):
            assert field in record, f"missing required Op-record field: {field}"


# ---------------------------------------------------------------------------
# Mode mapping (NFR-001)
# ---------------------------------------------------------------------------


class TestModeMapping:
    def test_entry_command_mode_mapping(self) -> None:
        """do/ask/dispatch -> task_execution; advise -> advisory."""
        assert derive_mode("dispatch") is ModeOfWork.TASK_EXECUTION
        assert derive_mode("do") is ModeOfWork.TASK_EXECUTION
        assert derive_mode("ask") is ModeOfWork.TASK_EXECUTION
        assert derive_mode("advise") is ModeOfWork.ADVISORY

    def test_op_record_mode_matches_verb(self, tmp_path: Path) -> None:
        """Each verb records the mode_of_work its entry command derives."""
        project = _setup_project(tmp_path)
        cases = {
            "dispatch": ("task_execution", ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"]),
            "do": ("task_execution", ["do", "implement the feature", "--profile", "implementer-fixture", "--json"]),
            "ask": ("task_execution", ["ask", "implementer-fixture", "implement the feature", "--json"]),
            "advise": ("advisory", ["advise", "implement the feature", "--profile", "implementer-fixture", "--json"]),
        }
        for _verb, (expected_mode, args) in cases.items():
            env = _invoke_json(project, args)
            record = _read_op_record(project, str(env["invocation_id"]))[0]
            assert record.get("mode_of_work") == expected_mode


# ---------------------------------------------------------------------------
# JSON envelope + exit-code parity (NFR-001)
# ---------------------------------------------------------------------------


class TestJsonEnvelopeParity:
    def test_dispatch_do_envelope_identical(self, tmp_path: Path) -> None:
        """The --json envelope (minus invocation-specific fields) matches across
        dispatch and do: status + close_contract shape + glossary observations."""
        project = _setup_project(tmp_path)
        dispatch_env = _invoke_json(
            project, ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"]
        )
        do_env = _invoke_json(
            project, ["do", "implement the feature", "--profile", "implementer-fixture", "--json"]
        )

        assert dispatch_env["status"] == do_env["status"] == "open"
        assert dispatch_env["profile_id"] == do_env["profile_id"]
        assert dispatch_env["action"] == do_env["action"]
        # glossary_observations carries a volatile `duration_ms` timing field;
        # compare the contract shape excluding that measurement.
        assert _strip_glossary_timing(dispatch_env["glossary_observations"]) == _strip_glossary_timing(
            do_env["glossary_observations"]
        )
        # close_contract differs only in the embedded invocation_id (inside command).
        d_contract = dict(dispatch_env["close_contract"])
        o_contract = dict(do_env["close_contract"])
        d_contract.pop("command", None)
        o_contract.pop("command", None)
        assert d_contract == o_contract

    def test_dispatch_advise_close_contract_mode_difference(self, tmp_path: Path) -> None:
        """task_execution close contract advertises --evidence; advisory omits it."""
        project = _setup_project(tmp_path)
        dispatch_env = _invoke_json(
            project, ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"]
        )
        advise_env = _invoke_json(
            project, ["advise", "implement the feature", "--profile", "implementer-fixture", "--json"]
        )
        assert dispatch_env["close_contract"]["evidence_flag"] == "--evidence"
        assert "evidence_flag" not in advise_env["close_contract"]

    def test_missing_profile_exit_code_parity(self, tmp_path: Path) -> None:
        """A non-existent profile exits 1 for both dispatch and do."""
        project = _setup_project(tmp_path)
        dispatch_result = _run(
            project, ["dispatch", "implement", "--profile", "nonexistent-profile", "--json"]
        )
        do_result = _run(project, ["do", "implement", "--profile", "nonexistent-profile", "--json"])
        assert dispatch_result.exit_code == 1
        assert do_result.exit_code == 1


# ---------------------------------------------------------------------------
# Registration / discoverability
# ---------------------------------------------------------------------------


class TestDispatchRegistration:
    def test_dispatch_help_exits_zero(self) -> None:
        result = runner.invoke(cli_app, ["dispatch", "--help"])
        assert result.exit_code == 0
        assert "dispatch" in result.output.lower()

    def test_dispatch_writes_single_jsonl(self, tmp_path: Path) -> None:
        project = _setup_project(tmp_path)
        env = _invoke_json(
            project, ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"]
        )
        jsonl = [p for p in (project / EVENTS_DIR).glob("*.jsonl") if p.name != "ops-index.jsonl"]
        assert len(jsonl) == 1
        assert jsonl[0].stem == str(env["invocation_id"])

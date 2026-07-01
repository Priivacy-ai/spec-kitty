"""Integration tests for the public ``spec-kitty dispatch`` surface."""

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

from glossary.chokepoint import GlossaryObservationBundle
from glossary.models import ConflictType, SemanticConflict, SenseRef, Severity, TermSurface
from specify_cli import app as cli_app
from specify_cli.invocation.modes import ModeOfWork, derive_mode
from specify_cli.invocation.writer import EVENTS_DIR, InvocationWriter

pytestmark = [pytest.mark.non_sandbox, pytest.mark.fast]

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "profiles"


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

_MISSING_CTX = MagicMock()
_MISSING_CTX.mode = "missing"
_MISSING_CTX.text = ""


def _setup_project(tmp_path: Path) -> Path:
    profiles_dir = tmp_path / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)
    return tmp_path


def _make_mock_registry(profile_specs: list[dict[str, object]]) -> MagicMock:
    from doctrine.agent_profiles.profile import Role

    mock_profiles = []
    for spec in profile_specs:
        profile = MagicMock()
        profile.profile_id = spec["profile_id"]
        profile.role = Role(str(spec["role_value"]))
        profile.routing_priority = spec.get("routing_priority", 50)
        profile.name = spec.get("name", spec["profile_id"])

        specialization = MagicMock()
        specialization.domain_keywords = spec.get("domain_keywords", [])
        profile.specialization_context = specialization

        collaboration = MagicMock()
        collaboration.canonical_verbs = spec.get("collab_verbs", [])
        profile.collaboration = collaboration

        mock_profiles.append(profile)

    registry = MagicMock()
    registry.list_all.return_value = mock_profiles

    def _get(profile_id: str) -> object | None:
        return next((profile for profile in mock_profiles if profile.profile_id == profile_id), None)

    def _resolve(profile_id: str) -> object:
        from specify_cli.invocation.errors import ProfileNotFoundError

        profile = _get(profile_id)
        if profile is None:
            raise ProfileNotFoundError(profile_id, [p.profile_id for p in mock_profiles])
        return profile

    registry.get.side_effect = _get
    registry.resolve.side_effect = _resolve
    return registry


def _implementer_registry() -> MagicMock:
    return _make_mock_registry(
        [
            {
                "profile_id": "implementer-fixture",
                "role_value": "implementer",
                "routing_priority": 50,
                "name": "Implementer (fixture)",
                "domain_keywords": ["implement", "build", "code"],
            }
        ]
    )


def _high_severity_bundle() -> GlossaryObservationBundle:
    conflict = SemanticConflict(
        term=TermSurface("lane"),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.HIGH,
        confidence=1.0,
        candidate_senses=[
            SenseRef(surface="lane", scope="spec_kitty_core", definition="Execution lane", confidence=1.0),
            SenseRef(surface="lane", scope="team_domain", definition="Worktree lane", confidence=1.0),
        ],
        context="request_text",
    )
    return GlossaryObservationBundle(
        matched_urns=("glossary:d93244e7",),
        high_severity=(conflict,),
        all_conflicts=(conflict,),
        tokens_checked=3,
        duration_ms=1.5,
        error_msg=None,
    )


def _run(project: Path, args: list[str], *, ctx: MagicMock = _COMPACT_CTX) -> Result:
    with (
        patch("specify_cli.cli.commands.dispatch.find_repo_root", return_value=project),
        patch("specify_cli.invocation.executor.build_charter_context", return_value=ctx),
    ):
        return runner.invoke(cli_app, args)


def _run_with_registry(project: Path, args: list[str], registry: MagicMock) -> Result:
    with (
        patch("specify_cli.cli.commands.dispatch.find_repo_root", return_value=project),
        patch("specify_cli.cli.commands.dispatch.ProfileRegistry", return_value=registry),
        patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX),
    ):
        return runner.invoke(cli_app, args)


def _invoke_json(project: Path, args: list[str], *, ctx: MagicMock = _COMPACT_CTX) -> dict[str, Any]:
    result = _run(project, args, ctx=ctx)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _read_op_record(project: Path, invocation_id: str) -> list[dict[str, Any]]:
    path = InvocationWriter(project).invocation_path(invocation_id)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_dispatch_with_profile_opens_task_execution_op(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)

    envelope = _invoke_json(
        project,
        ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"],
    )

    record = _read_op_record(project, str(envelope["invocation_id"]))[0]
    assert envelope["status"] == "open"
    assert envelope["governance_context_text"] == "compact governance context"
    assert envelope["close_contract"]["evidence_flag"] == "--evidence"
    assert record["mode_of_work"] == "task_execution"
    assert record["profile_id"] == "implementer-fixture"
    assert record["request_text"] == "implement the feature"


def test_dispatch_auto_routes_and_writes_single_started_record(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    result = _run_with_registry(
        project,
        ["dispatch", "implement the payment module", "--json"],
        _implementer_registry(),
    )

    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output)
    events = _read_op_record(project, str(envelope["invocation_id"]))
    assert envelope["profile_id"] == "implementer-fixture"
    assert envelope["router_confidence"] == "canonical_verb"
    assert [event["event"] for event in events] == ["started"]


def test_dispatch_no_charter_still_opens_record(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)

    envelope = _invoke_json(
        project,
        ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"],
        ctx=_MISSING_CTX,
    )

    record = _read_op_record(project, str(envelope["invocation_id"]))[0]
    assert envelope["governance_context_available"] is False
    assert record["governance_context_available"] is False


def test_dispatch_rich_output_includes_governance_and_close_contract(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    with (
        patch("specify_cli.cli.commands.dispatch.find_repo_root", return_value=project),
        patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX),
        patch("glossary.chokepoint.GlossaryChokepoint.run", return_value=_high_severity_bundle()),
    ):
        result = runner.invoke(
            cli_app,
            ["dispatch", "implement the feature", "--profile", "implementer-fixture"],
        )

    assert result.exit_code == 0, result.output
    flat = result.output.replace("\n", " ")
    assert "High-severity terminology conflicts detected before this invocation." in result.output
    assert result.output.index("lane (ambiguous)") < result.output.index("compact governance context")
    assert "This Op is OPEN" in flat
    assert "profile-invocation complete" in flat
    assert "git add" not in flat


def test_dispatch_missing_profile_exits_1_with_routing_error(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)

    result = _run(
        project,
        ["dispatch", "implement", "--profile", "nonexistent-profile", "--json"],
    )

    assert result.exit_code == 1
    error_obj = json.loads(result.output)
    assert error_obj["error"] == "routing_failed"
    assert error_obj["error_code"] == "PROFILE_NOT_FOUND"
    assert "spec-kitty profiles list" in error_obj["suggestion"]


def test_only_dispatch_is_registered_as_standalone_opener() -> None:
    assert runner.invoke(cli_app, ["dispatch", "--help"]).exit_code == 0
    for removed_command in ("do", "ask", "advise"):
        assert runner.invoke(cli_app, [removed_command, "--help"]).exit_code != 0


def test_entry_command_mode_mapping_only_has_dispatch_for_standalone_openers() -> None:
    assert derive_mode("dispatch") is ModeOfWork.TASK_EXECUTION
    for removed_command in ("do", "ask", "advise"):
        with pytest.raises(KeyError):
            derive_mode(removed_command)


def test_dispatch_writes_single_jsonl_file(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    envelope = _invoke_json(
        project,
        ["dispatch", "implement the feature", "--profile", "implementer-fixture", "--json"],
    )
    jsonl = [p for p in (project / EVENTS_DIR).glob("*.jsonl") if p.name != "ops-index.jsonl"]
    assert len(jsonl) == 1
    assert jsonl[0].stem == str(envelope["invocation_id"])
